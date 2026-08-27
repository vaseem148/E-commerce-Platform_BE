"""Authoritative pricing, coupon and inventory rules for Nexa.

This module is the **single source of truth** for money. Routers never do
arithmetic on prices themselves - they call :func:`compute_cart_totals` (or the
convenience wrapper :func:`cart_response`) and serialise the result.

The rules, verbatim from the API contract::

    subtotal = sum(line_total)
    discount = coupon applied to subtotal (percent capped by max_discount, or flat)
    shipping = 0 if (subtotal - discount) >= 999 else 49
    tax      = round((subtotal - discount) * 0.05, 2)      # 5% GST
    total    = subtotal - discount + shipping + tax

The low-level ``compute_discount`` / ``compute_totals`` primitives live in
``app.services.serializers`` (so the serialiser layer stays self-contained);
they are re-exported here so callers only ever need to import ``pricing``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.applied_coupon import CartCoupon
from app.models.cart import CartItem
from app.models.coupon import Coupon
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartOut
from app.services.serializers import (
    cart_to_out,
    category_counts_map,
    compute_discount,
    compute_totals,
    money,
)

#: Hard ceiling on how many units of one product a single cart line may hold.
MAX_LINE_QUANTITY = 99


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def format_inr(amount: float) -> str:
    """Format a rupee amount with Indian digit grouping (``1,23,456``).

    Used inside user-facing error messages so the API speaks the same language
    as the UI (which formats with ``Intl.NumberFormat('en-IN')``).
    """
    value = money(amount)
    negative = value < 0
    value = abs(value)

    whole = int(value)
    paise = int(round((value - whole) * 100))
    if paise >= 100:  # rounding carried over into the rupee
        whole += 1
        paise = 0

    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: List[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        grouped = ",".join(groups + [tail])
    else:
        grouped = digits

    if paise:
        grouped = f"{grouped}.{paise:02d}"
    return f"-{grouped}" if negative else grouped


# ---------------------------------------------------------------------------
# Inventory guards (shared by the cart and the checkout)
# ---------------------------------------------------------------------------
def stock_error(product: Product, requested: int) -> Optional[str]:
    """Return an error message when ``requested`` units cannot be fulfilled."""
    available = int(product.stock or 0)
    if not product.is_active:
        return f"{product.name} is no longer available"
    if available <= 0:
        return f"{product.name} is out of stock"
    if requested > available:
        return f"Only {available} left in stock"
    if requested > MAX_LINE_QUANTITY:
        return f"You can order at most {MAX_LINE_QUANTITY} units of this product"
    return None


def ensure_stock(product: Product, requested: int) -> None:
    """Raise ``400`` with a precise message when stock cannot cover the request."""
    message = stock_error(product, requested)
    if message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


# ---------------------------------------------------------------------------
# Cart reads
# ---------------------------------------------------------------------------
def get_cart_items(db: Session, user: User) -> List[CartItem]:
    """Every cart line for ``user``, oldest first (stable display order)."""
    return list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .order_by(CartItem.created_at.asc(), CartItem.id.asc())
        ).unique()
    )


def get_cart_item(db: Session, user: User, item_id: int) -> Optional[CartItem]:
    """One cart line, scoped to its owner so ids cannot be guessed."""
    return db.scalars(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    ).first()


def find_cart_line(db: Session, user: User, product_id: int) -> Optional[CartItem]:
    """The user's existing line for ``product_id``, when there is one."""
    return db.scalars(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    ).first()


def cart_subtotal(items: Sequence[CartItem]) -> float:
    """Sum of every line total, rounded to paise."""
    return money(sum(item.line_total for item in items if item.product is not None))


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
def find_coupon(db: Session, code: str) -> Optional[Coupon]:
    """Case-insensitive coupon lookup."""
    cleaned = (code or "").strip()
    if not cleaned:
        return None
    return db.scalars(
        select(Coupon).where(func.upper(Coupon.code) == cleaned.upper())
    ).first()


def validate_coupon(db: Session, code: str, subtotal: float) -> Tuple[Coupon, float]:
    """Validate ``code`` against ``subtotal``.

    Returns ``(coupon, discount)``, or raises ``HTTPException(400)`` carrying a
    precise, user-facing ``detail``.
    """
    coupon = find_coupon(db, code)
    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid coupon code",
        )
    if coupon.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon has expired",
        )
    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon is no longer active",
        )

    minimum = money(coupon.min_order)
    if minimum > 0 and money(subtotal) < minimum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This coupon requires a minimum order of Rs. {format_inr(minimum)}",
        )

    discount = compute_discount(money(subtotal), coupon)
    if discount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon does not apply to the items in your cart",
        )

    return coupon, discount


def get_cart_coupon_row(db: Session, user: User) -> Optional[CartCoupon]:
    """The ``cart_coupons`` row holding the code the user applied, if any."""
    return db.scalars(select(CartCoupon).where(CartCoupon.user_id == user.id)).first()


def clear_cart_coupon(db: Session, user: User, commit: bool = True) -> None:
    """Detach any coupon from the user's cart. Safe to call when none exists."""
    row = get_cart_coupon_row(db, user)
    if row is None:
        return
    db.delete(row)
    if commit:
        db.commit()
    else:
        db.flush()


def apply_cart_coupon(db: Session, user: User, coupon: Coupon) -> None:
    """Attach ``coupon`` to the user's cart, replacing any previous one."""
    row = get_cart_coupon_row(db, user)
    if row is None:
        db.add(CartCoupon(user_id=user.id, code=coupon.code))
    else:
        row.code = coupon.code
    db.flush()


def resolve_cart_coupon(db: Session, user: User, subtotal: float) -> Optional[Coupon]:
    """Return the coupon currently applied to the cart.

    A coupon that has since expired, been deactivated, been deleted, or that no
    longer clears its minimum-order threshold is detached automatically, so the
    cart totals never advertise a discount the checkout would refuse.
    """
    row = get_cart_coupon_row(db, user)
    if row is None:
        return None

    coupon = find_coupon(db, row.code)
    still_valid = (
        coupon is not None
        and coupon.is_redeemable
        and money(subtotal) >= money(coupon.min_order)
        and compute_discount(money(subtotal), coupon) > 0
    )
    if not still_valid:
        db.delete(row)
        db.commit()
        return None

    return coupon


# ---------------------------------------------------------------------------
# The authoritative cart computation
# ---------------------------------------------------------------------------
def compute_cart_totals(db: Session, user: User) -> Dict[str, Any]:
    """Compute the user's cart exactly as the pricing rules describe.

    Returns a dict with ``items`` (ORM ``CartItem`` rows), ``count``,
    ``subtotal``, ``discount``, ``shipping``, ``tax``, ``total`` and ``coupon``
    (the ORM ``Coupon`` or ``None``). Both the cart endpoints and the checkout
    read their numbers from here - the client's numbers are never trusted.
    """
    items = [item for item in get_cart_items(db, user) if item.product is not None]
    subtotal = cart_subtotal(items)
    coupon = resolve_cart_coupon(db, user, subtotal)
    discount = compute_discount(subtotal, coupon)
    totals = compute_totals(subtotal, discount)

    return {
        "items": items,
        "count": sum(int(item.quantity or 0) for item in items),
        "subtotal": totals["subtotal"],
        "discount": totals["discount"],
        "shipping": totals["shipping"],
        "tax": totals["tax"],
        "total": totals["total"],
        "coupon": coupon if totals["discount"] > 0 else None,
    }


def cart_response(db: Session, user: User) -> CartOut:
    """Serialise the user's cart - the payload every cart endpoint returns."""
    snapshot = compute_cart_totals(db, user)
    return cart_to_out(
        snapshot["items"],
        snapshot["coupon"],
        category_counts_map(db),
    )


__all__ = [
    "MAX_LINE_QUANTITY",
    "format_inr",
    "money",
    "compute_discount",
    "compute_totals",
    "stock_error",
    "ensure_stock",
    "get_cart_items",
    "get_cart_item",
    "find_cart_line",
    "cart_subtotal",
    "find_coupon",
    "validate_coupon",
    "get_cart_coupon_row",
    "clear_cart_coupon",
    "apply_cart_coupon",
    "resolve_cart_coupon",
    "compute_cart_totals",
    "cart_response",
]

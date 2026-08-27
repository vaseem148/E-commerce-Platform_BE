"""Shopping cart endpoints.

Mounted at ``/api/cart``. Every endpoint - including the mutations - returns
the **full, freshly recomputed** cart so the client never has to guess what the
totals became after a change.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import (
    CartAddRequest,
    CartOut,
    CartUpdateRequest,
    CouponApplyRequest,
)
from app.services import pricing

router = APIRouter()


def _get_product(db: Session, product_id: int) -> Product:
    """Fetch a purchasable product or raise 404."""
    product = db.scalars(select(Product).where(Product.id == product_id)).first()
    if product is None or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


def _get_line(db: Session, user: User, item_id: int) -> CartItem:
    """Fetch one of the user's own cart lines or raise 404."""
    item = pricing.get_cart_item(db, user, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )
    return item


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=CartOut,
    summary="Get the current user's cart",
)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Return the cart with authoritative, server-computed totals."""
    return pricing.cart_response(db, current_user)


# ---------------------------------------------------------------------------
# Line items
# ---------------------------------------------------------------------------
@router.post(
    "/items",
    response_model=CartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product to the cart",
)
def add_item(
    payload: CartAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Add a product, or increment the quantity when it is already in the cart."""
    product = _get_product(db, payload.product_id)
    quantity = max(1, int(payload.quantity or 1))

    line = pricing.find_cart_line(db, current_user, product.id)
    desired = quantity + (int(line.quantity or 0) if line else 0)

    # Validate the *resulting* quantity, not just the increment.
    pricing.ensure_stock(product, desired)

    if line is None:
        line = CartItem(
            user_id=current_user.id,
            product_id=product.id,
            quantity=desired,
        )
        db.add(line)
    else:
        line.quantity = desired

    db.commit()
    return pricing.cart_response(db, current_user)


@router.patch(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Set the quantity of a cart line (0 removes it)",
)
def update_item(
    payload: CartUpdateRequest,
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Replace the quantity of a line. A quantity of ``0`` removes it."""
    line = _get_line(db, current_user, item_id)
    quantity = int(payload.quantity or 0)

    if quantity <= 0:
        db.delete(line)
        db.commit()
        return pricing.cart_response(db, current_user)

    product = line.product
    if product is None or not product.is_active:
        # The catalog entry vanished underneath the cart - drop the dead line.
        db.delete(line)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    pricing.ensure_stock(product, quantity)

    line.quantity = quantity
    db.commit()
    return pricing.cart_response(db, current_user)


@router.delete(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Remove a line from the cart",
)
def remove_item(
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Remove a single line item."""
    line = _get_line(db, current_user, item_id)
    db.delete(line)
    db.commit()
    return pricing.cart_response(db, current_user)


@router.delete(
    "",
    response_model=CartOut,
    summary="Empty the cart",
)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Remove every line and detach any applied coupon."""
    db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    pricing.clear_cart_coupon(db, current_user, commit=False)
    db.commit()
    return pricing.cart_response(db, current_user)


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
@router.post(
    "/coupon",
    response_model=CartOut,
    summary="Apply a coupon to the cart",
)
def apply_coupon(
    payload: CouponApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Validate and attach a coupon, replacing any previously applied one."""
    items = pricing.get_cart_items(db, current_user)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add items to your cart before applying a coupon",
        )

    subtotal = pricing.cart_subtotal(items)
    coupon, _discount = pricing.validate_coupon(db, payload.code, subtotal)

    pricing.apply_cart_coupon(db, current_user, coupon)
    db.commit()
    return pricing.cart_response(db, current_user)


@router.delete(
    "/coupon",
    response_model=CartOut,
    summary="Remove the applied coupon",
)
def remove_coupon(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartOut:
    """Detach the coupon. Idempotent - succeeds even when none was applied."""
    pricing.clear_cart_coupon(db, current_user)
    return pricing.cart_response(db, current_user)

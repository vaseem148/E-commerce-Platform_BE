"""Shared ORM -> Pydantic serializers.

Every router serialises through these helpers so a Product looks identical
whether it came from the catalog, the cart, the wishlist or the admin panel.

They also own the authoritative pricing math:

    subtotal = sum(line_total)
    discount = coupon applied to subtotal (percent capped by max_discount, or flat)
    shipping = 0 if (subtotal - discount) >= 999 else 49
    tax      = round((subtotal - discount) * 0.05, 2)
    total    = subtotal - discount + shipping + tax
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.models.address import Address
from app.models.cart import CartItem
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import Review
from app.models.user import User
from app.schemas.address import AddressOut
from app.schemas.cart import AppliedCouponOut, CartItemOut, CartOut
from app.schemas.category import CategoryOut
from app.schemas.coupon import CouponOut
from app.schemas.order import OrderItemOut, OrderOut, OrderTimelineEntry
from app.schemas.product import ProductDetailOut, ProductOut
from app.schemas.review import ReviewOut
from app.schemas.user import UserOut, UserPublic

_COUNTS_CACHE_KEY = "_nexa_category_counts"


# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------
def money(value: Optional[float]) -> float:
    """Round a monetary amount to 2 decimal places, treating None as 0."""
    return round(float(value or 0.0), 2)


def compute_discount(subtotal: float, coupon: Optional[Coupon]) -> float:
    """Discount produced by ``coupon`` against ``subtotal`` (never negative)."""
    if coupon is None or subtotal <= 0:
        return 0.0
    if subtotal < float(coupon.min_order or 0.0):
        return 0.0

    if coupon.type == "percent":
        amount = subtotal * (float(coupon.value or 0.0) / 100.0)
        if coupon.max_discount is not None:
            amount = min(amount, float(coupon.max_discount))
    else:  # "flat"
        amount = float(coupon.value or 0.0)

    return money(max(0.0, min(amount, subtotal)))


def compute_totals(subtotal: float, discount: float = 0.0) -> Dict[str, float]:
    """Return the full price breakdown for a given subtotal and discount."""
    subtotal = money(subtotal)
    discount = money(min(discount, subtotal))
    payable = max(0.0, subtotal - discount)

    shipping = (
        0.0 if payable >= settings.FREE_SHIPPING_THRESHOLD else settings.SHIPPING_FLAT_RATE
    )
    if payable <= 0:
        shipping = 0.0

    tax = money(payable * settings.TAX_RATE)
    total = money(payable + shipping + tax)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "shipping": money(shipping),
        "tax": tax,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
def category_counts_map(db: Session) -> Dict[int, int]:
    """Active-product count per category id, in a single grouped query."""
    rows = db.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.is_active.is_(True))
        .group_by(Product.category_id)
    ).all()
    return {int(cid): int(count) for cid, count in rows}


def _category_product_count(category: Optional[Category]) -> int:
    """Count active products for a category, memoised per database session."""
    if category is None:
        return 0

    db = object_session(category)
    if db is None:
        return 0

    cache = db.info.get(_COUNTS_CACHE_KEY)
    if cache is None:
        cache = category_counts_map(db)
        db.info[_COUNTS_CACHE_KEY] = cache
    return int(cache.get(category.id, 0))


def invalidate_category_counts(db: Session) -> None:
    """Drop the memoised counts after a catalog write."""
    db.info.pop(_COUNTS_CACHE_KEY, None)


def category_to_out(
    category: Category, product_count: Optional[int] = None
) -> CategoryOut:
    """Serialise a Category, computing ``product_count`` when not supplied."""
    count = (
        int(product_count)
        if product_count is not None
        else _category_product_count(category)
    )
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description or "",
        image_url=category.image_url or "",
        product_count=count,
    )


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
def product_to_out(
    product: Product, category_counts: Optional[Dict[int, int]] = None
) -> ProductOut:
    """Serialise a Product exactly as the API contract describes it."""
    if product.category is None:
        # Defensive: the FK is NOT NULL, but never crash a whole listing.
        category = CategoryOut(
            id=product.category_id or 0,
            name="Uncategorised",
            slug="uncategorised",
            description="",
            image_url="",
            product_count=0,
        )
    elif category_counts is not None:
        category = category_to_out(
            product.category, category_counts.get(product.category_id, 0)
        )
    else:
        category = category_to_out(product.category)

    return ProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description or "",
        price=money(product.price),
        compare_at_price=(
            money(product.compare_at_price)
            if product.compare_at_price is not None
            else None
        ),
        discount_percent=product.discount_percent,
        stock=int(product.stock or 0),
        brand=product.brand or "",
        rating=round(float(product.rating or 0.0), 2),
        review_count=int(product.review_count or 0),
        images=list(product.images or []),
        category=category,
        is_featured=bool(product.is_featured),
        is_active=bool(product.is_active),
        tags=list(product.tags or []),
        created_at=product.created_at,
    )


def products_to_out(
    products: Iterable[Product], category_counts: Optional[Dict[int, int]] = None
) -> List[ProductOut]:
    """Serialise many products, sharing one category-count map."""
    return [product_to_out(p, category_counts) for p in products]


def product_to_detail_out(
    product: Product,
    related: Optional[Sequence[Product]] = None,
    rating_breakdown: Optional[Dict[str, int]] = None,
    category_counts: Optional[Dict[int, int]] = None,
) -> ProductDetailOut:
    """Serialise the single-product page payload."""
    base = product_to_out(product, category_counts)
    breakdown = rating_breakdown or {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    return ProductDetailOut(
        **base.model_dump(),
        related=[product_to_out(p, category_counts) for p in (related or [])],
        rating_breakdown={str(k): int(v) for k, v in breakdown.items()},
    )


def empty_rating_breakdown() -> Dict[str, int]:
    return {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}


# ---------------------------------------------------------------------------
# User / review / address / coupon
# ---------------------------------------------------------------------------
def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role if user.role in ("user", "admin") else "user",
        created_at=user.created_at,
    )


def user_to_public(user: Optional[User]) -> UserPublic:
    if user is None:
        return UserPublic(id=0, name="Deleted user", avatar_url=None)
    return UserPublic(id=user.id, name=user.name, avatar_url=user.avatar_url)


def review_to_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        rating=int(review.rating),
        title=review.title or "",
        comment=review.comment or "",
        created_at=review.created_at,
        user=user_to_public(review.user),
    )


def address_to_out(address: Address) -> AddressOut:
    return AddressOut(
        id=address.id,
        full_name=address.full_name,
        phone=address.phone,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        is_default=bool(address.is_default),
    )


def coupon_to_out(coupon: Coupon) -> CouponOut:
    return CouponOut(
        id=coupon.id,
        code=coupon.code,
        type=coupon.type if coupon.type in ("percent", "flat") else "percent",
        value=money(coupon.value),
        min_order=money(coupon.min_order),
        max_discount=(
            money(coupon.max_discount) if coupon.max_discount is not None else None
        ),
        is_active=bool(coupon.is_active),
        expires_at=coupon.expires_at,
        used_count=int(coupon.used_count or 0),
    )


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
def cart_item_to_out(
    item: CartItem, category_counts: Optional[Dict[int, int]] = None
) -> CartItemOut:
    return CartItemOut(
        id=item.id,
        product=product_to_out(item.product, category_counts),
        quantity=int(item.quantity or 0),
        line_total=money(item.line_total),
    )


def cart_to_out(
    items: Sequence[CartItem],
    coupon: Optional[Coupon] = None,
    category_counts: Optional[Dict[int, int]] = None,
) -> CartOut:
    """Serialise a cart and apply the authoritative pricing rules."""
    line_items = [
        cart_item_to_out(item, category_counts)
        for item in items
        if item.product is not None
    ]

    subtotal = money(sum(li.line_total for li in line_items))
    discount = compute_discount(subtotal, coupon)
    totals = compute_totals(subtotal, discount)

    applied: Optional[AppliedCouponOut] = None
    if coupon is not None and totals["discount"] > 0:
        applied = AppliedCouponOut(
            code=coupon.code,
            type=coupon.type if coupon.type in ("percent", "flat") else "percent",
            value=money(coupon.value),
        )

    return CartOut(
        items=line_items,
        count=sum(li.quantity for li in line_items),
        subtotal=totals["subtotal"],
        discount=totals["discount"],
        shipping=totals["shipping"],
        tax=totals["tax"],
        total=totals["total"],
        coupon=applied,
    )


def empty_cart() -> CartOut:
    """A zeroed cart - used when a user has no items."""
    return CartOut(
        items=[],
        count=0,
        subtotal=0.0,
        discount=0.0,
        shipping=0.0,
        tax=0.0,
        total=0.0,
        coupon=None,
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def order_item_to_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        id=item.id,
        product_id=int(item.product_id),
        name=item.name,
        slug=item.slug or "",
        image=item.image or "",
        price=money(item.price),
        quantity=int(item.quantity or 0),
        line_total=money(item.line_total),
    )


def _order_address(order: Order) -> AddressOut:
    """Build an AddressOut from the order's shipping snapshot.

    The snapshot is not a row in ``addresses`` (the original address may have
    been edited or deleted since), so the id is reported as 0.
    """
    return AddressOut(
        id=0,
        full_name=order.ship_name or "",
        phone=order.ship_phone or "",
        line1=order.ship_line1 or "",
        line2=order.ship_line2,
        city=order.ship_city or "",
        state=order.ship_state or "",
        pincode=order.ship_pincode or "",
        is_default=False,
    )


def _order_timeline(order: Order) -> List[OrderTimelineEntry]:
    """Normalise the stored timeline, synthesising one entry when empty."""
    entries: List[OrderTimelineEntry] = []
    for raw in order.timeline or []:
        if not isinstance(raw, dict):
            continue
        at = raw.get("at")
        if isinstance(at, str):
            try:
                at = datetime.fromisoformat(at.replace("Z", "+00:00"))
            except ValueError:
                at = order.created_at
        elif not isinstance(at, datetime):
            at = order.created_at
        entries.append(
            OrderTimelineEntry(
                status=str(raw.get("status") or order.status),
                at=at,
                note=str(raw.get("note") or ""),
            )
        )

    if not entries:
        entries.append(
            OrderTimelineEntry(
                status=order.status,
                at=order.created_at,
                note="Order placed",
            )
        )
    return entries


def timeline_entry(status: str, at: Optional[datetime] = None, note: str = "") -> dict:
    """Build a JSON-serialisable timeline entry for storing on an Order."""
    moment = at or datetime.utcnow()
    return {"status": status, "at": moment.isoformat(), "note": note}


def order_to_out(order: Order) -> OrderOut:
    """Serialise an Order exactly as the API contract describes it."""
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        items=[order_item_to_out(item) for item in (order.items or [])],
        subtotal=money(order.subtotal),
        discount=money(order.discount),
        shipping=money(order.shipping),
        tax=money(order.tax),
        total=money(order.total),
        address=_order_address(order),
        coupon_code=order.coupon_code,
        created_at=order.created_at,
        timeline=_order_timeline(order),
    )


def orders_to_out(orders: Iterable[Order]) -> List[OrderOut]:
    return [order_to_out(o) for o in orders]


__all__ = [
    "money",
    "compute_discount",
    "compute_totals",
    "category_counts_map",
    "invalidate_category_counts",
    "category_to_out",
    "product_to_out",
    "products_to_out",
    "product_to_detail_out",
    "empty_rating_breakdown",
    "user_to_out",
    "user_to_public",
    "review_to_out",
    "address_to_out",
    "coupon_to_out",
    "cart_item_to_out",
    "cart_to_out",
    "empty_cart",
    "order_item_to_out",
    "order_to_out",
    "orders_to_out",
    "timeline_entry",
]

"""SQLAlchemy models.

Importing this package registers every mapper on ``Base.metadata`` which is
what ``init_db()`` relies on to create the schema.
"""

from app.models.address import Address
from app.models.applied_coupon import CartCoupon
from app.models.cart import CartItem
from app.models.category import Category
from app.models.coupon import COUPON_TYPES, Coupon
from app.models.order import (
    CANCELLABLE_STATUSES,
    ORDER_STATUSES,
    PAYMENT_METHODS,
    PAYMENT_STATUSES,
    STATUS_FLOW,
    Order,
    OrderItem,
    build_order_number,
)
from app.models.product import Product
from app.models.review import Review
from app.models.user import User
from app.models.wishlist import WishlistItem

__all__ = [
    "Address",
    "CartCoupon",
    "CartItem",
    "Category",
    "Coupon",
    "COUPON_TYPES",
    "Order",
    "OrderItem",
    "ORDER_STATUSES",
    "PAYMENT_METHODS",
    "PAYMENT_STATUSES",
    "STATUS_FLOW",
    "CANCELLABLE_STATUSES",
    "build_order_number",
    "Product",
    "Review",
    "User",
    "WishlistItem",
]

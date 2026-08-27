"""Pydantic v2 schemas mirroring the public API contract."""

from app.schemas.address import (
    AddressBase,
    AddressCreate,
    AddressOut,
    AddressUpdate,
)
from app.schemas.admin import (
    AdminStatsOut,
    CustomerOut,
    RevenuePoint,
    StatusBucket,
    TopCategory,
    TopProduct,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenOut,
)
from app.schemas.cart import (
    AppliedCouponOut,
    CartAddRequest,
    CartItemOut,
    CartOut,
    CartUpdateRequest,
    CouponApplyRequest,
)
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    paginate_params,
)
from app.schemas.coupon import CouponCreate, CouponOut, CouponUpdate
from app.schemas.order import (
    OrderCreate,
    OrderItemOut,
    OrderOut,
    OrderStatusUpdate,
    OrderTimelineEntry,
)
from app.schemas.product import (
    BrandFacet,
    CategoryFacet,
    ProductCreate,
    ProductDetailOut,
    ProductFacets,
    ProductListResponse,
    ProductOut,
    ProductUpdate,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewOut,
    ReviewSummary,
)
from app.schemas.user import UserOut, UserPublic, UserUpdate
from app.schemas.wishlist import WishlistOut

__all__ = [
    # common
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    "paginate_params",
    # user / auth
    "UserOut",
    "UserPublic",
    "UserUpdate",
    "RegisterRequest",
    "LoginRequest",
    "TokenOut",
    "ChangePasswordRequest",
    # catalog
    "CategoryOut",
    "CategoryCreate",
    "CategoryUpdate",
    "ProductOut",
    "ProductDetailOut",
    "ProductCreate",
    "ProductUpdate",
    "ProductFacets",
    "ProductListResponse",
    "BrandFacet",
    "CategoryFacet",
    # reviews
    "ReviewOut",
    "ReviewCreate",
    "ReviewSummary",
    "ReviewListResponse",
    # cart
    "CartOut",
    "CartItemOut",
    "CartAddRequest",
    "CartUpdateRequest",
    "CouponApplyRequest",
    "AppliedCouponOut",
    # wishlist
    "WishlistOut",
    # addresses
    "AddressOut",
    "AddressBase",
    "AddressCreate",
    "AddressUpdate",
    # orders
    "OrderOut",
    "OrderItemOut",
    "OrderCreate",
    "OrderStatusUpdate",
    "OrderTimelineEntry",
    # coupons
    "CouponOut",
    "CouponCreate",
    "CouponUpdate",
    # admin
    "AdminStatsOut",
    "CustomerOut",
    "RevenuePoint",
    "StatusBucket",
    "TopProduct",
    "TopCategory",
]

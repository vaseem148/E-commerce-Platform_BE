"""Cart schemas."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.product import ProductOut


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductOut
    quantity: int
    line_total: float


class AppliedCouponOut(BaseModel):
    """The coupon block embedded in a cart response."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    type: Literal["percent", "flat"]
    value: float


class CartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CartItemOut] = Field(default_factory=list)
    count: int = 0
    subtotal: float = 0.0
    discount: float = 0.0
    shipping: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    coupon: Optional[AppliedCouponOut] = None


class CartAddRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartUpdateRequest(BaseModel):
    """Quantity 0 removes the line item."""

    quantity: int = Field(ge=0, le=99)


class CouponApplyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)

    @field_validator("code")
    @classmethod
    def _normalise(cls, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if not cleaned:
            raise ValueError("Coupon code is required")
        return cleaned

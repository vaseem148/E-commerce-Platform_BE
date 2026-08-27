"""Order schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.address import AddressOut

OrderStatus = Literal[
    "pending", "confirmed", "packed", "shipped", "delivered", "cancelled"
]
PaymentMethod = Literal["cod", "card", "upi", "netbanking"]
PaymentStatus = Literal["pending", "paid", "failed", "refunded"]


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    name: str
    slug: str = ""
    image: str = ""
    price: float
    quantity: int
    line_total: float


class OrderTimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    at: datetime
    note: str = ""


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    items: List[OrderItemOut] = Field(default_factory=list)
    subtotal: float = 0.0
    discount: float = 0.0
    shipping: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    address: AddressOut
    coupon_code: Optional[str] = None
    created_at: datetime
    timeline: List[OrderTimelineEntry] = Field(default_factory=list)


class OrderCreate(BaseModel):
    address_id: int
    payment_method: PaymentMethod = "cod"
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class OrderStatusUpdate(BaseModel):
    """Admin PATCH payload - at least one field must be supplied."""

    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    note: Optional[str] = Field(default=None, max_length=500)

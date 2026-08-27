"""Admin dashboard and management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.order import OrderOut
from app.schemas.product import ProductOut
from app.schemas.user import Role


# --- analytics building blocks ----------------------------------------------
class RevenuePoint(BaseModel):
    """One day on the revenue chart."""

    date: str  # "YYYY-MM-DD"
    revenue: float = 0.0
    orders: int = 0


class StatusBucket(BaseModel):
    status: str
    count: int = 0


class TopProduct(BaseModel):
    id: int
    name: str
    slug: str = ""
    image: str = ""
    units_sold: int = 0
    revenue: float = 0.0


class TopCategory(BaseModel):
    name: str
    revenue: float = 0.0


class AdminStatsOut(BaseModel):
    """Payload for GET /api/admin/stats."""

    model_config = ConfigDict(from_attributes=True)

    revenue: float = 0.0
    revenue_delta_pct: float = 0.0
    orders: int = 0
    orders_delta_pct: float = 0.0
    customers: int = 0
    customers_delta_pct: float = 0.0
    products: int = 0
    avg_order_value: float = 0.0
    pending_orders: int = 0

    revenue_series: List[RevenuePoint] = Field(default_factory=list)
    status_breakdown: List[StatusBucket] = Field(default_factory=list)
    top_products: List[TopProduct] = Field(default_factory=list)
    top_categories: List[TopCategory] = Field(default_factory=list)
    recent_orders: List[OrderOut] = Field(default_factory=list)
    low_stock: List[ProductOut] = Field(default_factory=list)


# --- customer directory ------------------------------------------------------
class CustomerOut(BaseModel):
    """A user row enriched with lifetime order metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Role = "user"
    created_at: datetime

    orders_count: int = 0
    total_spent: float = 0.0
    last_order_at: Optional[datetime] = None

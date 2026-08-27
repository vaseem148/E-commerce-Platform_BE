"""Order and order-item models."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User

# --- enumerations (kept as plain strings for SQLite friendliness) ------------
ORDER_STATUSES = (
    "pending",
    "confirmed",
    "packed",
    "shipped",
    "delivered",
    "cancelled",
)
PAYMENT_METHODS = ("cod", "card", "upi", "netbanking")
PAYMENT_STATUSES = ("pending", "paid", "failed", "refunded")

#: Statuses a customer is still allowed to cancel from.
CANCELLABLE_STATUSES = ("pending", "confirmed")

#: Forward-only progression used to validate admin status transitions.
STATUS_FLOW = ("pending", "confirmed", "packed", "shipped", "delivered")


def build_order_number(order_id: int, created: Optional[datetime] = None) -> str:
    """Build a human-friendly order number such as ``NEX-2026-0001A7``.

    Deterministic: a zero-padded counter from the primary key plus a short
    uppercase hex suffix derived from the same id, so the value never collides
    and can be regenerated from the row alone.
    """
    moment = created or utcnow()
    counter = f"{order_id:04d}"
    suffix = f"{(order_id * 2654435761) % 0x100:02X}"
    return f"NEX-{moment.year}-{counter}{suffix}"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), default="cod", server_default="cod", nullable=False
    )
    payment_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )

    # --- money (always rounded to 2 dp before persisting) --------------------
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shipping: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, index=True
    )

    coupon_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- shipping address snapshot -------------------------------------------
    ship_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ship_phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    ship_line1: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ship_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ship_city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ship_state: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ship_pincode: Mapped[str] = mapped_column(String(16), default="", nullable=False)

    #: List of ``{"status": str, "at": iso8601, "note": str}`` entries.
    timeline: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="joined")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderItem.id",
    )

    @property
    def item_count(self) -> int:
        return sum((item.quantity or 0) for item in (self.items or []))

    @property
    def can_cancel(self) -> bool:
        return self.status in CANCELLABLE_STATUSES


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Snapshot of the product at purchase time - the catalog may change later.
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), default="", nullable=False)
    image: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship("Order", back_populates="items")

"""Discount coupon model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow

COUPON_TYPES = ("percent", "flat")


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(10), default="percent", server_default="percent", nullable=False
    )
    value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_order: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )
    max_discount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    used_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return self.expires_at < utcnow()

    @property
    def is_redeemable(self) -> bool:
        return bool(self.is_active) and not self.is_expired

"""Product catalog model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from app.models.category import Category
    from app.models.review import Review


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(220), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    price: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, index=True
    )
    compare_at_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    stock: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    brand: Mapped[str] = mapped_column(
        String(120), default="", nullable=False, index=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    is_featured: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False, index=True
    )

    # Denormalised aggregates kept in sync by the reviews and orders routers.
    rating: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False, index=True
    )
    review_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    sold_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, index=True
    )

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

    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="products",
        lazy="joined",
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def discount_percent(self) -> int:
        """Percentage saved versus compare_at_price (0 when not on sale)."""
        compare = self.compare_at_price
        if not compare or compare <= self.price:
            return 0
        return int(round((compare - self.price) / compare * 100))

    @property
    def in_stock(self) -> bool:
        return (self.stock or 0) > 0

    @property
    def primary_image(self) -> str:
        images = self.images or []
        return images[0] if images else ""

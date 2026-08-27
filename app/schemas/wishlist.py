"""Wishlist schemas.

The wishlist endpoints return a bare ``Product[]`` array, so this module simply
re-exports ``ProductOut`` under a wishlist-flavoured alias plus a small
``WishlistToggleResult`` helper used internally by the router.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductOut

#: Wishlist entries are serialised exactly like catalog products.
WishlistItemOut = ProductOut

#: Convenience alias for ``response_model=List[ProductOut]``.
WishlistOut = List[ProductOut]


class WishlistToggleResult(BaseModel):
    """Optional richer payload: the full list plus what just changed."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ProductOut] = Field(default_factory=list)
    added: bool = False
    product_id: int = 0


__all__ = ["WishlistItemOut", "WishlistOut", "WishlistToggleResult", "ProductOut"]

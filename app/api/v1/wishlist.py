"""Wishlist endpoints.

Mounted at ``/api/wishlist``. All three endpoints return the complete, ordered
``Product[]`` so the client can replace its local state wholesale after any
toggle - no optimistic-merge bugs.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.product import Product
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.schemas.product import ProductOut
from app.services.serializers import category_counts_map, products_to_out

router = APIRouter()


def _wishlist_products(db: Session, user: User) -> List[ProductOut]:
    """The user's wishlist as serialised products, most recently added first."""
    entries = list(
        db.scalars(
            select(WishlistItem)
            .where(WishlistItem.user_id == user.id)
            .order_by(WishlistItem.created_at.desc(), WishlistItem.id.desc())
        ).unique()
    )
    products = [entry.product for entry in entries if entry.product is not None]
    return products_to_out(products, category_counts_map(db))


@router.get(
    "",
    response_model=List[ProductOut],
    summary="List the current user's wishlist",
)
def list_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ProductOut]:
    """Return every saved product, newest first."""
    return _wishlist_products(db, current_user)


@router.post(
    "/{product_id}",
    response_model=List[ProductOut],
    summary="Add a product to the wishlist",
)
def add_to_wishlist(
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ProductOut]:
    """Save a product. Idempotent - adding it twice is not an error."""
    product = db.scalars(select(Product).where(Product.id == product_id)).first()
    if product is None or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing = db.scalars(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product.id,
        )
    ).first()

    if existing is None:
        db.add(WishlistItem(user_id=current_user.id, product_id=product.id))
        db.commit()

    return _wishlist_products(db, current_user)


@router.delete(
    "/{product_id}",
    response_model=List[ProductOut],
    summary="Remove a product from the wishlist",
)
def remove_from_wishlist(
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ProductOut]:
    """Remove a saved product. Idempotent - removing an absent one is fine."""
    entry = db.scalars(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    ).first()

    if entry is not None:
        db.delete(entry)
        db.commit()

    return _wishlist_products(db, current_user)

"""Category endpoints.

Mounted at ``/api/categories``:

    GET /api/categories         every category, each with its live product count
    GET /api/categories/{slug}  one category

``product_count`` always counts *active* products only, and the listing resolves
all counts with a single grouped query - never one query per category.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryOut
from app.services.serializers import category_counts_map, category_to_out

router = APIRouter()

CATEGORY_NOT_FOUND = "Category not found"


@router.get(
    "",
    response_model=List[CategoryOut],
    summary="All categories with their active product counts",
)
def list_categories(db: Session = Depends(get_db)) -> List[CategoryOut]:
    """Alphabetical category list; counts come from one grouped query."""
    counts = category_counts_map(db)
    categories = db.scalars(select(Category).order_by(Category.name.asc())).all()
    return [
        category_to_out(category, counts.get(category.id, 0))
        for category in categories
    ]


@router.get(
    "/{slug}",
    response_model=CategoryOut,
    summary="A single category by slug",
    responses={404: {"description": CATEGORY_NOT_FOUND}},
)
def get_category(slug: str, db: Session = Depends(get_db)) -> CategoryOut:
    """Look a category up by slug, 404 when it does not exist."""
    category = db.scalars(
        select(Category).where(func.lower(Category.slug) == (slug or "").strip().lower())
    ).first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=CATEGORY_NOT_FOUND
        )

    product_count = int(
        db.scalar(
            select(func.count(Product.id)).where(
                Product.category_id == category.id,
                Product.is_active.is_(True),
            )
        )
        or 0
    )
    return category_to_out(category, product_count)

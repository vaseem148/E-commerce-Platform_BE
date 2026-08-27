"""Product review endpoints.

This router is mounted at ``/api`` (not ``/api/reviews``) because its routes
straddle two resources:

    GET    /api/products/{slug}/reviews   paginated reviews + rating summary
    POST   /api/products/{slug}/reviews   write a review            [auth]
    DELETE /api/reviews/{review_id}       remove one   [auth: owner or admin]

It also owns the denormalised rating aggregates on ``products`` - every write
here recomputes ``product.rating`` and ``product.review_count`` so the catalog
can sort and filter by rating without touching the reviews table.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.models.product import Product
from app.models.review import Review
from app.models.user import User
from app.schemas.common import paginate_params
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewOut,
    ReviewSummary,
)
from app.services.serializers import empty_rating_breakdown, review_to_out

router = APIRouter()

PRODUCT_NOT_FOUND = "Product not found"
REVIEW_NOT_FOUND = "Review not found"
DUPLICATE_REVIEW = "You have already reviewed this product"
NOT_ALLOWED = "Not allowed"

DEFAULT_REVIEW_PAGE_SIZE = 10


# ---------------------------------------------------------------------------
# Rating aggregation (shared with the products router)
# ---------------------------------------------------------------------------
def rating_breakdown_map(db: Session, product_id: int) -> Dict[str, int]:
    """How many reviews gave each star rating; keys "1".."5" are always present."""
    breakdown = empty_rating_breakdown()
    rows = db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.product_id == product_id)
        .group_by(Review.rating)
    ).all()
    for rating, count in rows:
        key = str(int(rating))
        if key in breakdown:
            breakdown[key] = int(count)
    return breakdown


def refresh_product_rating(db: Session, product: Product) -> None:
    """Recompute and persist ``rating`` / ``review_count`` for one product.

    Call this after any review insert or delete, before committing.
    """
    count, average = db.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.product_id == product.id
        )
    ).one()

    total = int(count or 0)
    product.review_count = total
    product.rating = round(float(average or 0.0), 1) if total else 0.0


def _summary_from_breakdown(breakdown: Dict[str, int]) -> ReviewSummary:
    """Average / count / breakdown, derived from a single grouped query."""
    count = sum(breakdown.values())
    if count:
        weighted = sum(int(star) * hits for star, hits in breakdown.items())
        average = round(weighted / count, 1)
    else:
        average = 0.0
    return ReviewSummary(average=average, count=count, breakdown=breakdown)


def _get_product_or_404(db: Session, slug: str) -> Product:
    product = db.scalars(
        select(Product).where(func.lower(Product.slug) == (slug or "").strip().lower())
    ).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND
        )
    return product


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get(
    "/products/{slug}/reviews",
    response_model=ReviewListResponse,
    summary="Paginated reviews for a product, with the rating summary",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def list_reviews(
    slug: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(
        DEFAULT_REVIEW_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE
    ),
) -> ReviewListResponse:
    """Newest reviews first; the summary always covers *all* reviews."""
    product = _get_product_or_404(db, slug)

    total = int(
        db.scalar(
            select(func.count(Review.id)).where(Review.product_id == product.id)
        )
        or 0
    )
    page, page_size, offset = paginate_params(page, page_size, settings.MAX_PAGE_SIZE)

    reviews = db.scalars(
        select(Review)
        .where(Review.product_id == product.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    response = ReviewListResponse.create(
        items=[review_to_out(review) for review in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )
    response.summary = _summary_from_breakdown(rating_breakdown_map(db, product.id))
    return response


@router.post(
    "/products/{slug}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Write a review (one per customer per product)",
    responses={
        400: {"description": DUPLICATE_REVIEW},
        404: {"description": PRODUCT_NOT_FOUND},
    },
)
def create_review(
    slug: str,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReviewOut:
    """Create the caller's review, then refresh the product's rating aggregates."""
    product = _get_product_or_404(db, slug)

    existing = db.scalars(
        select(Review).where(
            Review.product_id == product.id, Review.user_id == current_user.id
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=DUPLICATE_REVIEW
        )

    review = Review(
        product_id=product.id,
        user_id=current_user.id,
        rating=int(payload.rating),
        title=payload.title,
        comment=payload.comment,
    )
    db.add(review)

    try:
        db.flush()
    except IntegrityError:
        # Two tabs, one product: the unique (product_id, user_id) index wins.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=DUPLICATE_REVIEW
        )

    refresh_product_rating(db, product)
    db.commit()
    db.refresh(review)

    return review_to_out(review)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review (owner or admin)",
    responses={
        403: {"description": NOT_ALLOWED},
        404: {"description": REVIEW_NOT_FOUND},
    },
)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Remove a review, then refresh the product's rating aggregates."""
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=REVIEW_NOT_FOUND
        )

    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)

    product: Optional[Product] = db.get(Product, review.product_id)

    db.delete(review)
    db.flush()

    if product is not None:
        refresh_product_rating(db, product)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__: List[str] = [
    "router",
    "rating_breakdown_map",
    "refresh_product_rating",
]

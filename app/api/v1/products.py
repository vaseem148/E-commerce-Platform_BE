"""Public catalog endpoints.

Mounted at ``/api/products``:

    GET /api/products           faceted, filtered, sorted, paginated listing
    GET /api/products/featured  hand-picked products for the home page
    GET /api/products/{slug}    single product + related items + rating breakdown

Every filter is pushed down to SQL - nothing is filtered in Python - and the
facet block is computed from the *same* filtered query minus the facet's own
dimension, so brand counts stay meaningful while a brand is already selected.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, and_, cast, func, not_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.reviews import rating_breakdown_map
from app.core.config import settings
from app.core.deps import get_db, get_optional_user
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.common import paginate_params
from app.schemas.product import (
    BrandFacet,
    CategoryFacet,
    ProductDetailOut,
    ProductFacets,
    ProductListResponse,
    ProductOut,
    SortOption,
)
from app.services.serializers import (
    category_counts_map,
    product_to_detail_out,
    products_to_out,
)

router = APIRouter()

#: A search box is not a query language - cap the work one request can ask for.
MAX_SEARCH_TOKENS = 6
#: Size of the "you may also like" strip on the product page.
RELATED_LIMIT = 8

PRODUCT_NOT_FOUND = "Product not found"


# ---------------------------------------------------------------------------
# Filter building blocks
# ---------------------------------------------------------------------------
def _escape_like(term: str) -> str:
    """Escape LIKE wildcards so a shopper typing ``50%`` searches a literal."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _tags_text() -> ColumnElement:
    """The JSON ``tags`` column as lowercase text, e.g. ``["audio", "anc"]``."""
    return func.lower(cast(Product.tags, String))


def _search_conditions(search: str) -> List[ColumnElement]:
    """One AND-ed condition per token; each token may match any searchable field.

    Multi-word queries therefore narrow the result set ("wireless headphones"
    requires both words somewhere in name / brand / description / tags) instead
    of exploding it, which is what shoppers actually expect.
    """
    tokens = [tok for tok in (search or "").lower().split() if tok][:MAX_SEARCH_TOKENS]
    conditions: List[ColumnElement] = []
    for token in tokens:
        pattern = "%" + _escape_like(token) + "%"
        conditions.append(
            or_(
                func.lower(Product.name).like(pattern, escape="\\"),
                func.lower(Product.brand).like(pattern, escape="\\"),
                func.lower(Product.description).like(pattern, escape="\\"),
                _tags_text().like(pattern, escape="\\"),
            )
        )
    return conditions


def _clean_list(values: Optional[Sequence[str]]) -> List[str]:
    """Lowercased, de-duplicated, blank-free copy of a repeatable query param.

    Comma separated values are accepted too, so ``?brand=Aurora,Volt`` behaves
    like ``?brand=Aurora&brand=Volt``.
    """
    cleaned: List[str] = []
    for raw in values or []:
        for part in str(raw).split(","):
            item = part.strip().lower()
            if item and item not in cleaned:
                cleaned.append(item)
    return cleaned


def _on_sale_condition() -> ColumnElement:
    return and_(
        Product.compare_at_price.is_not(None),
        Product.compare_at_price > Product.price,
    )


def _filter_groups(
    *,
    search: Optional[str],
    category: Optional[List[str]],
    brand: Optional[List[str]],
    min_price: Optional[float],
    max_price: Optional[float],
    min_rating: Optional[float],
    in_stock: Optional[bool],
    featured: Optional[bool],
    on_sale: Optional[bool],
    tag: Optional[str],
) -> Dict[str, List[ColumnElement]]:
    """Group the WHERE clauses by the *dimension* each one constrains.

    Keeping them grouped is what makes self-excluding facets possible: the brand
    facet re-runs the query with every group except ``"brand"``.
    """
    groups: Dict[str, List[ColumnElement]] = {"base": [Product.is_active.is_(True)]}

    if search and search.strip():
        conditions = _search_conditions(search)
        if conditions:
            groups["search"] = conditions

    slugs = _clean_list(category)
    if slugs:
        groups["category"] = [
            Product.category_id.in_(
                select(Category.id).where(func.lower(Category.slug).in_(slugs))
            )
        ]

    brands = _clean_list(brand)
    if brands:
        groups["brand"] = [func.lower(Product.brand).in_(brands)]

    price: List[ColumnElement] = []
    if min_price is not None:
        price.append(Product.price >= float(min_price))
    if max_price is not None:
        price.append(Product.price <= float(max_price))
    if price:
        groups["price"] = price

    if min_rating is not None and min_rating > 0:
        groups["rating"] = [Product.rating >= float(min_rating)]

    if in_stock is not None:
        groups["stock"] = [Product.stock > 0] if in_stock else [Product.stock <= 0]

    if featured is not None:
        groups["featured"] = [Product.is_featured.is_(bool(featured))]

    if on_sale is not None:
        sale = _on_sale_condition()
        groups["sale"] = [sale] if on_sale else [not_(sale)]

    if tag and tag.strip():
        # tags is a JSON array, so match the quoted token - otherwise "pro"
        # would also match "projector".
        needle = _escape_like(tag.strip().lower())
        groups["tag"] = [_tags_text().like('%"' + needle + '"%', escape="\\")]

    return groups


def _conditions(
    groups: Dict[str, List[ColumnElement]],
    exclude: Optional[Set[str]] = None,
) -> List[ColumnElement]:
    """Flatten the grouped conditions, optionally dropping some dimensions."""
    skip = exclude or set()
    flat: List[ColumnElement] = []
    for key, conditions in groups.items():
        if key in skip:
            continue
        flat.extend(conditions)
    return flat


def _order_by(sort: str) -> List[ColumnElement]:
    """Deterministic ORDER BY for each supported sort option."""
    if sort == "price_asc":
        return [Product.price.asc(), Product.id.asc()]
    if sort == "price_desc":
        return [Product.price.desc(), Product.id.desc()]
    if sort == "rating":
        return [Product.rating.desc(), Product.review_count.desc(), Product.id.desc()]
    if sort == "popular":
        return [
            Product.sold_count.desc(),
            Product.review_count.desc(),
            Product.rating.desc(),
            Product.id.desc(),
        ]
    if sort == "name_asc":
        return [func.lower(Product.name).asc(), Product.id.asc()]
    return [Product.created_at.desc(), Product.id.desc()]  # "newest"


# ---------------------------------------------------------------------------
# Facets
# ---------------------------------------------------------------------------
def _build_facets(db: Session, groups: Dict[str, List[ColumnElement]]) -> ProductFacets:
    """Sidebar facets, each computed *without* its own filter applied."""
    brand_rows = db.execute(
        select(Product.brand, func.count(Product.id))
        .where(*_conditions(groups, exclude={"brand"}))
        .where(Product.brand.is_not(None), func.trim(Product.brand) != "")
        .group_by(Product.brand)
        .order_by(func.count(Product.id).desc(), Product.brand.asc())
    ).all()
    brands = [
        BrandFacet(name=name, count=int(count)) for name, count in brand_rows if name
    ]

    category_rows = db.execute(
        select(Category.slug, Category.name, func.count(Product.id))
        .join(Product, Product.category_id == Category.id)
        .where(*_conditions(groups, exclude={"category"}))
        .group_by(Category.id, Category.slug, Category.name)
        .order_by(func.count(Product.id).desc(), Category.name.asc())
    ).all()
    categories = [
        CategoryFacet(slug=slug, name=name, count=int(count))
        for slug, name, count in category_rows
    ]

    low, high = db.execute(
        select(func.min(Product.price), func.max(Product.price)).where(
            *_conditions(groups, exclude={"price"})
        )
    ).one()

    if low is None or high is None:
        # Nothing matched: fall back to the catalog-wide range so the price
        # slider keeps usable bounds instead of collapsing to 0 - 0.
        low, high = db.execute(
            select(func.min(Product.price), func.max(Product.price)).where(
                Product.is_active.is_(True)
            )
        ).one()

    return ProductFacets(
        brands=brands,
        categories=categories,
        price_min=round(float(low or 0.0), 2),
        price_max=round(float(high or 0.0), 2),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=ProductListResponse,
    summary="Browse products with filters, sorting, pagination and facets",
)
def list_products(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(
        None, max_length=200, description="Matches name, brand, description and tags"
    ),
    category: Optional[List[str]] = Query(
        None, description="Category slug - repeat the param to select several"
    ),
    brand: Optional[List[str]] = Query(
        None, description="Brand name - repeat the param to select several"
    ),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    in_stock: Optional[bool] = Query(None, description="Only items still in stock"),
    featured: Optional[bool] = Query(None),
    on_sale: Optional[bool] = Query(None, description="Only discounted items"),
    tag: Optional[str] = Query(None, max_length=80),
    sort: SortOption = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> ProductListResponse:
    """Return one page of products plus the facet block for the filter sidebar."""
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    groups = _filter_groups(
        search=search,
        category=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        in_stock=in_stock,
        featured=featured,
        on_sale=on_sale,
        tag=tag,
    )
    where = _conditions(groups)

    total = int(db.scalar(select(func.count(Product.id)).where(*where)) or 0)
    page, page_size, offset = paginate_params(page, page_size, settings.MAX_PAGE_SIZE)

    products = db.scalars(
        select(Product)
        .where(*where)
        .order_by(*_order_by(sort))
        .offset(offset)
        .limit(page_size)
    ).all()

    counts = category_counts_map(db)
    response = ProductListResponse.create(
        items=products_to_out(products, counts),
        total=total,
        page=page,
        page_size=page_size,
    )
    response.facets = _build_facets(db, groups)
    return response


@router.get(
    "/featured",
    response_model=List[ProductOut],
    summary="Featured products for the home page",
)
def featured_products(
    db: Session = Depends(get_db),
    limit: int = Query(8, ge=1, le=24),
) -> List[ProductOut]:
    """Best-rated featured products, topped up with best sellers when short."""
    products = list(
        db.scalars(
            select(Product)
            .where(Product.is_active.is_(True), Product.is_featured.is_(True))
            .order_by(
                Product.rating.desc(),
                Product.sold_count.desc(),
                Product.created_at.desc(),
                Product.id.desc(),
            )
            .limit(limit)
        ).all()
    )

    if len(products) < limit:
        chosen = {p.id for p in products}
        filler = select(Product).where(Product.is_active.is_(True))
        if chosen:
            filler = filler.where(Product.id.not_in(chosen))
        products.extend(
            db.scalars(
                filler.order_by(
                    Product.rating.desc(),
                    Product.sold_count.desc(),
                    Product.id.desc(),
                ).limit(limit - len(products))
            ).all()
        )

    return products_to_out(products, category_counts_map(db))


@router.get(
    "/{slug}",
    response_model=ProductDetailOut,
    summary="Product detail with related items and rating breakdown",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def get_product(
    slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> ProductDetailOut:
    """Look a product up by slug; admins may also preview unpublished items."""
    product = db.scalars(
        select(Product).where(func.lower(Product.slug) == slug.strip().lower())
    ).first()

    is_admin = current_user is not None and current_user.role == "admin"
    if product is None or (not product.is_active and not is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND
        )

    related = db.scalars(
        select(Product)
        .where(
            Product.is_active.is_(True),
            Product.category_id == product.category_id,
            Product.id != product.id,
        )
        .order_by(
            Product.rating.desc(),
            Product.review_count.desc(),
            Product.sold_count.desc(),
            Product.id.desc(),
        )
        .limit(RELATED_LIMIT)
    ).all()

    return product_to_detail_out(
        product,
        related=related,
        rating_breakdown=rating_breakdown_map(db, product.id),
        category_counts=category_counts_map(db),
    )

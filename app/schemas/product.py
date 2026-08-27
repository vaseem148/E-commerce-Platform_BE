"""Product schemas, including the faceted list response."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryOut
from app.schemas.common import PaginatedResponse

SortOption = Literal[
    "newest", "price_asc", "price_desc", "rating", "popular", "name_asc"
]


class ProductOut(BaseModel):
    """Catalog card / grid representation of a product."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str = ""
    price: float
    compare_at_price: Optional[float] = None
    discount_percent: int = 0
    stock: int = 0
    brand: str = ""
    rating: float = 0.0
    review_count: int = 0
    images: List[str] = Field(default_factory=list)
    category: CategoryOut
    is_featured: bool = False
    is_active: bool = True
    tags: List[str] = Field(default_factory=list)
    created_at: datetime


class ProductDetailOut(ProductOut):
    """Single-product page payload: adds related items and rating breakdown."""

    related: List[ProductOut] = Field(default_factory=list)
    rating_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    )


# --- facets -----------------------------------------------------------------
class BrandFacet(BaseModel):
    name: str
    count: int


class CategoryFacet(BaseModel):
    slug: str
    name: str
    count: int


class ProductFacets(BaseModel):
    brands: List[BrandFacet] = Field(default_factory=list)
    categories: List[CategoryFacet] = Field(default_factory=list)
    price_min: float = 0.0
    price_max: float = 0.0


class ProductListResponse(PaginatedResponse[ProductOut]):
    """Paginated envelope plus the facet block used by the filter sidebar."""

    facets: ProductFacets = Field(default_factory=ProductFacets)


# --- admin write models -----------------------------------------------------
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    price: float = Field(ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="", max_length=120)
    category_id: int
    images: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    is_featured: bool = False
    is_active: bool = True
    slug: Optional[str] = Field(default=None, max_length=220)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    brand: Optional[str] = Field(default=None, max_length=120)
    category_id: Optional[int] = None
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    slug: Optional[str] = Field(default=None, max_length=220)

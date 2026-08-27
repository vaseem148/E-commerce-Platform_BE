"""Category schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str = ""
    image_url: str = ""
    product_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    image_url: str = ""
    slug: Optional[str] = Field(default=None, max_length=140)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    slug: Optional[str] = Field(default=None, max_length=140)

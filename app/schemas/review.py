"""Review schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginatedResponse
from app.schemas.user import UserPublic


def _empty_breakdown() -> Dict[str, int]:
    return {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: int
    title: str = ""
    comment: str = ""
    created_at: datetime
    user: UserPublic


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=200)
    comment: str = Field(default="", max_length=4000)

    @field_validator("title", "comment")
    @classmethod
    def _strip(cls, value: str) -> str:
        return (value or "").strip()


class ReviewSummary(BaseModel):
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=_empty_breakdown)


class ReviewListResponse(PaginatedResponse[ReviewOut]):
    """Paginated reviews plus the aggregate rating summary."""

    summary: ReviewSummary = Field(default_factory=ReviewSummary)

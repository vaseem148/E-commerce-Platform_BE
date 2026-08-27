"""Shared schema primitives: pagination envelope and simple responses."""

from __future__ import annotations

from math import ceil
from typing import Generic, List, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Generic ``{"detail": "..."}`` payload used for simple acknowledgements."""

    detail: str


class ErrorResponse(BaseModel):
    """Shape of every error body returned by the API."""

    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope returned by every list endpoint.

    Usage::

        @router.get("", response_model=PaginatedResponse[ProductOut])
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 12
    pages: int = 0

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Build an envelope, deriving ``pages`` from ``total``/``page_size``."""
        safe_size = max(1, int(page_size or 1))
        return cls(
            items=list(items),
            total=int(total),
            page=max(1, int(page or 1)),
            page_size=safe_size,
            pages=int(ceil(total / safe_size)) if total else 0,
        )


def paginate_params(page: int, page_size: int, max_page_size: int = 100) -> tuple[int, int, int]:
    """Normalise page/page_size and return ``(page, page_size, offset)``."""
    safe_page = max(1, int(page or 1))
    safe_size = min(max(1, int(page_size or 12)), max_page_size)
    return safe_page, safe_size, (safe_page - 1) * safe_size

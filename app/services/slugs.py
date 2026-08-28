"""URL slug generation with collision handling.

Shared by the admin catalog endpoints and the seeder so a product created
through the API gets exactly the same slug shape as a seeded one.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Type

from sqlalchemy import func, select
from sqlalchemy.orm import Session

_NON_WORD = re.compile(r"[^a-z0-9]+")
_TRIM = re.compile(r"^-+|-+$")


def slugify(value: str, fallback: str = "item") -> str:
    """Turn arbitrary text into a lowercase, hyphenated ASCII slug."""
    normalised = unicodedata.normalize("NFKD", str(value or ""))
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii").lower()
    slug = _TRIM.sub("", _NON_WORD.sub("-", ascii_only))
    return slug[:180] or fallback


def unique_slug(
    db: Session,
    model: Type,
    value: str,
    *,
    fallback: str = "item",
    exclude_id: Optional[int] = None,
) -> str:
    """Return a slug for ``value`` that no other row of ``model`` is using.

    On collision a numeric suffix is appended (``-2``, ``-3``, ...).  Passing
    ``exclude_id`` lets a row keep its own slug while being renamed.
    """
    base = slugify(value, fallback=fallback)
    candidate = base
    suffix = 2

    while True:
        stmt = select(func.count(model.id)).where(model.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if not db.scalar(stmt):
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


__all__ = ["slugify", "unique_slug"]

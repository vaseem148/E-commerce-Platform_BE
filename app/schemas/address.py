"""Shipping address schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=32)
    line1: str = Field(min_length=1, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)
    pincode: str = Field(min_length=4, max_length=16)
    is_default: bool = False

    @field_validator("full_name", "line1", "city", "state", "pincode", "phone")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @field_validator("line2")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AddressCreate(AddressBase):
    """Payload for POST /api/addresses."""


class AddressUpdate(BaseModel):
    """Every field optional - PATCH semantics."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, min_length=6, max_length=32)
    line1: Optional[str] = Field(default=None, min_length=1, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=1, max_length=120)
    state: Optional[str] = Field(default=None, min_length=1, max_length=120)
    pincode: Optional[str] = Field(default=None, min_length=4, max_length=16)
    is_default: Optional[bool] = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    is_default: bool = False

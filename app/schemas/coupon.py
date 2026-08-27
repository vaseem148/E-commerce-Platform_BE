"""Coupon schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CouponType = Literal["percent", "flat"]


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    type: CouponType
    value: float
    min_order: float = 0.0
    max_discount: Optional[float] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None
    used_count: int = 0


class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    type: CouponType = "percent"
    value: float = Field(gt=0)
    min_order: float = Field(default=0.0, ge=0)
    max_discount: Optional[float] = Field(default=None, ge=0)
    is_active: bool = True
    expires_at: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def _normalise_code(cls, value: str) -> str:
        cleaned = (value or "").strip().upper().replace(" ", "")
        if len(cleaned) < 2:
            raise ValueError("Coupon code must be at least 2 characters")
        return cleaned


class CouponUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=40)
    type: Optional[CouponType] = None
    value: Optional[float] = Field(default=None, gt=0)
    min_order: Optional[float] = Field(default=None, ge=0)
    max_discount: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def _normalise_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().upper().replace(" ", "")
        if len(cleaned) < 2:
            raise ValueError("Coupon code must be at least 2 characters")
        return cleaned

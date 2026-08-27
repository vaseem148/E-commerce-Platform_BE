"""Shipping address book endpoints.

Mounted under ``/api/addresses`` by :mod:`app.main`. Every route is scoped to
the authenticated user - an address belonging to somebody else is reported as
``404 Address not found`` rather than ``403`` so ids cannot be probed.

Default-address invariants maintained here:

* the first address a user saves becomes their default automatically;
* promoting an address to default demotes every other one in the same
  transaction, so a user never has two defaults;
* deleting (or demoting) the default promotes the most recently created
  remaining address, so a user with addresses always has exactly one default.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.address import Address
from app.models.user import User
from app.schemas.address import AddressCreate, AddressOut, AddressUpdate
from app.schemas.common import ErrorResponse
from app.services.serializers import address_to_out

router = APIRouter()

ADDRESS_NOT_FOUND = "Address not found"
MAX_ADDRESSES = 20

NOT_FOUND_RESPONSE = {404: {"model": ErrorResponse, "description": ADDRESS_NOT_FOUND}}
AUTH_RESPONSE = {401: {"model": ErrorResponse, "description": "Not authenticated"}}

REQUIRED_TEXT_FIELDS = ("full_name", "phone", "line1", "city", "state", "pincode")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _user_addresses(db: Session, user_id: int) -> List[Address]:
    """All of a user's addresses: default first, then newest first."""
    return list(
        db.scalars(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(
                Address.is_default.desc(),
                Address.created_at.desc(),
                Address.id.desc(),
            )
        ).all()
    )


def _get_owned(db: Session, user_id: int, address_id: int) -> Address:
    """Fetch one address belonging to ``user_id`` or raise 404."""
    address = db.scalars(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )
    ).first()
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ADDRESS_NOT_FOUND
        )
    return address


def _count_addresses(db: Session, user_id: int) -> int:
    """How many addresses the user currently has saved."""
    return len(db.scalars(select(Address.id).where(Address.user_id == user_id)).all())


def _clear_other_defaults(db: Session, user_id: int, keep_id: Optional[int]) -> None:
    """Demote every other address of the user (single UPDATE, same transaction)."""
    stmt = update(Address).where(
        Address.user_id == user_id,
        Address.is_default.is_(True),
    )
    if keep_id is not None:
        stmt = stmt.where(Address.id != keep_id)
    db.execute(stmt.values(is_default=False))


def _promote_latest(db: Session, user_id: int, exclude_id: Optional[int] = None) -> None:
    """Make the most recently created remaining address the default."""
    stmt = select(Address).where(Address.user_id == user_id)
    if exclude_id is not None:
        stmt = stmt.where(Address.id != exclude_id)

    candidate = db.scalars(
        stmt.order_by(Address.created_at.desc(), Address.id.desc())
    ).first()
    if candidate is not None and not candidate.is_default:
        candidate.is_default = True
        db.add(candidate)


def _label(field: str) -> str:
    """Human readable field name for validation messages."""
    return field.replace("_", " ").capitalize()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=List[AddressOut],
    summary="List your saved addresses",
    responses={**AUTH_RESPONSE},
)
def list_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[AddressOut]:
    """Return the signed-in user's address book, default address first."""
    return [address_to_out(address) for address in _user_addresses(db, current_user.id)]


@router.post(
    "",
    response_model=AddressOut,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new address",
    responses={**AUTH_RESPONSE, 400: {"model": ErrorResponse}},
)
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AddressOut:
    """Create an address. The first one saved is automatically the default."""
    existing = _count_addresses(db, current_user.id)
    if existing >= MAX_ADDRESSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can save up to {MAX_ADDRESSES} addresses",
        )

    make_default = bool(payload.is_default) or existing == 0

    address = Address(
        user_id=current_user.id,
        full_name=payload.full_name,
        phone=payload.phone,
        line1=payload.line1,
        line2=payload.line2,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        is_default=make_default,
    )
    db.add(address)
    db.flush()  # assign the id before demoting siblings

    if make_default:
        _clear_other_defaults(db, current_user.id, keep_id=address.id)

    db.commit()
    db.refresh(address)
    return address_to_out(address)


@router.patch(
    "/{address_id}",
    response_model=AddressOut,
    summary="Update a saved address",
    responses={**AUTH_RESPONSE, **NOT_FOUND_RESPONSE},
)
def update_address(
    payload: AddressUpdate,
    address_id: int = Path(..., ge=1, description="Address id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AddressOut:
    """Patch any subset of an address's fields, keeping the default rules intact."""
    address = _get_owned(db, current_user.id, address_id)
    data = payload.model_dump(exclude_unset=True)

    for field in REQUIRED_TEXT_FIELDS:
        if field not in data or data[field] is None:
            continue
        cleaned = str(data[field]).strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{_label(field)} cannot be empty",
            )
        setattr(address, field, cleaned)

    if "line2" in data:
        line2 = data["line2"]
        address.line2 = (str(line2).strip() or None) if line2 is not None else None

    if data.get("is_default") is not None:
        if bool(data["is_default"]):
            address.is_default = True
            db.add(address)
            _clear_other_defaults(db, current_user.id, keep_id=address.id)
        elif address.is_default:
            # Never leave the user without a default: demote only when another
            # address can take over, otherwise this one stays the default.
            if _count_addresses(db, current_user.id) > 1:
                address.is_default = False
                db.add(address)
                _promote_latest(db, current_user.id, exclude_id=address.id)

    db.add(address)
    db.commit()
    db.refresh(address)
    return address_to_out(address)


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved address",
    responses={**AUTH_RESPONSE, **NOT_FOUND_RESPONSE},
)
def delete_address(
    address_id: int = Path(..., ge=1, description="Address id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Delete an address; the newest remaining one inherits the default flag."""
    address = _get_owned(db, current_user.id, address_id)
    was_default = bool(address.is_default)

    db.delete(address)
    db.flush()

    if was_default:
        _promote_latest(db, current_user.id, exclude_id=address_id)

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

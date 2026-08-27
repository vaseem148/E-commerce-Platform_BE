"""Authentication endpoints: register, login, profile and password management.

All routes are mounted under ``/api/auth`` by :mod:`app.main`.

Error bodies always follow the ``{"detail": "..."}`` contract - login failures
deliberately return the *same* message for an unknown email and a wrong
password so the endpoint cannot be used to enumerate accounts.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenOut,
)
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.user import UserOut, UserUpdate
from app.services.serializers import user_to_out

router = APIRouter()

INVALID_CREDENTIALS = "Incorrect email or password"
EMAIL_TAKEN = "An account with this email already exists"
ACCOUNT_DISABLED = "This account has been deactivated"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize_email(email: str) -> str:
    """Lowercase + strip so ``  Foo@Bar.COM `` and ``foo@bar.com`` are one account."""
    return (email or "").strip().lower()


def _find_by_email(db: Session, email: str) -> Optional[User]:
    """Case-insensitive lookup - tolerant of rows seeded with mixed casing."""
    return db.scalars(
        select(User).where(func.lower(User.email) == _normalize_email(email))
    ).first()


def _issue_token(user: User) -> TokenOut:
    """Build the ``{access_token, token_type, user}`` payload for a user."""
    token = create_access_token(
        user.id,
        extra_claims={"email": user.email, "role": user.role},
    )
    return TokenOut(access_token=token, token_type="bearer", user=user_to_out(user))


# ---------------------------------------------------------------------------
# Registration & login
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    responses={400: {"model": ErrorResponse, "description": "Email already registered"}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenOut:
    """Create a new customer account and return an access token.

    New accounts are always created with the ``user`` role - the very first
    account in an empty database is *not* promoted to admin.
    """
    email = _normalize_email(str(payload.email))

    if _find_by_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_TAKEN)

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race against a concurrent signup with the same address.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_TAKEN
        ) from None

    db.refresh(user)
    return _issue_token(user)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Sign in with email and password",
    responses={401: {"model": ErrorResponse, "description": "Bad credentials"}},
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    """Exchange credentials for a bearer token."""
    user = _find_by_email(db, str(payload.email))

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_DISABLED
        )

    # Transparently upgrade legacy/low-iteration hashes on successful login.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)

    return _issue_token(user)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserOut,
    summary="Current signed-in user",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_me(current_user: User = Depends(get_current_active_user)) -> UserOut:
    """Return the profile of the authenticated user."""
    return user_to_out(current_user)


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update your profile",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserOut:
    """Patch the editable profile fields (name, phone, avatar).

    Email and role are intentionally immutable through this endpoint.
    """
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"]:
        current_user.name = data["name"]
    if "phone" in data:
        current_user.phone = data["phone"]
    if "avatar_url" in data:
        current_user.avatar_url = data["avatar_url"]

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_to_out(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change your password",
    responses={
        400: {"model": ErrorResponse, "description": "Current password is incorrect"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Replace the caller's password after verifying the current one."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()

    return MessageResponse(detail="Password updated successfully")

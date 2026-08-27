"""Reusable FastAPI dependencies: database sessions and auth guards."""

from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Bearer")

CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> Optional[User]:
    """Resolve a bearer token into a User, or ``None`` when not resolvable."""
    if credentials is None or not credentials.credentials:
        return None
    if (credentials.scheme or "").lower() != "bearer":
        return None

    payload = decode_token(credentials.credentials)
    if not payload:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    return db.scalars(select(User).where(User.id == user_id)).first()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user or raise 401."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=CREDENTIALS_HEADERS,
        )

    user = _user_from_credentials(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers=CREDENTIALS_HEADERS,
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user, rejecting deactivated accounts."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return the authenticated user only when they are an administrator."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user when a valid token is present, else None."""
    user = _user_from_credentials(credentials, db)
    if user is not None and not user.is_active:
        return None
    return user

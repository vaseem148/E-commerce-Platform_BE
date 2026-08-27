"""Password hashing and JWT helpers.

Password hashing intentionally uses only the Python standard library
(``hashlib.pbkdf2_hmac``) so the project has no native-compiled dependencies
and installs cleanly on Windows.

Stored hash format::

    pbkdf2_sha256$<iterations>$<hex-salt>$<hex-hash>
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import jwt

from app.core.config import settings

ALGORITHM_LABEL = "pbkdf2_sha256"
SALT_BYTES = 16


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str, *, iterations: Optional[int] = None) -> str:
    """Hash a plain-text password into a self-describing storable string."""
    if not isinstance(password, str) or password == "":
        raise ValueError("Password must be a non-empty string")

    rounds = int(iterations or settings.PBKDF2_ITERATIONS)
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"{ALGORITHM_LABEL}${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """Verify a plain-text password against a stored hash. Never raises."""
    if not password or not stored:
        return False

    try:
        label, rounds_raw, salt_hex, hash_hex = stored.split("$")
        if label != ALGORITHM_LABEL:
            return False
        rounds = int(rounds_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored: Optional[str]) -> bool:
    """True when a stored hash uses fewer iterations than currently configured."""
    if not stored:
        return True
    try:
        label, rounds_raw, _salt, _hash = stored.split("$")
    except ValueError:
        return True
    return label != ALGORITHM_LABEL or int(rounds_raw) < settings.PBKDF2_ITERATIONS


# ---------------------------------------------------------------------------
# JSON Web Tokens
# ---------------------------------------------------------------------------
def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed HS256 access token for ``subject`` (usually a user id)."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    # PyJWT >= 2 returns str; older versions returned bytes.
    if isinstance(token, bytes):  # pragma: no cover - defensive
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a token. Returns the claims dict or ``None``."""
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.PyJWTError:
        return None


def get_subject_from_token(token: str) -> Optional[str]:
    """Convenience helper returning just the ``sub`` claim."""
    payload = decode_token(token)
    if not payload:
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None

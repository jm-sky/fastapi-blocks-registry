"""Authentication utilities for JWT token management and password hashing."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from ...core.config import settings
from .types.jwt import JWTPayload


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.security.access_token_expires_minutes)

    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(UTC)
    })
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> JWTPayload:
    """Verify and decode a JWT token."""
    from .exceptions import ExpiredTokenError, InvalidTokenError

    try:
        payload = jwt.decode(token, settings.security.secret_key, algorithms=[settings.security.jwt_algorithm])
        return payload  # type: ignore[no-any-return]
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError()
    except jwt.InvalidTokenError:
        raise InvalidTokenError()


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token with longer expiration."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.security.refresh_token_expires_days)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(UTC)
    })
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt


def create_password_reset_token(data: dict[str, Any]) -> str:
    """Create a JWT password reset token with 1-hour expiration."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(hours=settings.security.password_reset_token_expires_hours)
    to_encode.update({
        "exp": expire,
        "type": "password_reset",
        "iat": datetime.now(UTC)
    })
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt

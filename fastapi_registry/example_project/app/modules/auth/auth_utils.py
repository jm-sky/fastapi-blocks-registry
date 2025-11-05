"""Authentication utilities for JWT token management and password hashing."""

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from ...core.config import settings
from .types.jwt import CreateAccessTokenOptions, CreateRefreshTokenOptions, JWTPayload


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def create_access_token(
    data: CreateAccessTokenOptions,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with optional tenant and 2FA context.

    Args:
        data: Token options including sub (required), email, tid, trol, tfaVerified, tfaMethod
        expires_delta: Optional custom expiration time. If not provided, uses default from settings.

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.security.access_token_expires_minutes)

    payload: JWTPayload = {
        "sub": data["sub"],
        "email": data.get("email"),
        "tid": data.get("tid"),
        "trol": data.get("trol"),
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "tfaPending": False,
        "tfaVerified": data.get("tfaVerified", False),
        "tfaMethod": data.get("tfaMethod"),
    }
    encoded_jwt = jwt.encode(dict(payload), settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
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


def create_refresh_token(data: CreateRefreshTokenOptions) -> str:
    """Create a JWT refresh token with longer expiration and 2FA context.

    Args:
        data: Token options including sub (required), email, tfaVerified, tfaMethod
            Note: tid/trol are NOT preserved in refresh tokens (security).

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.security.refresh_token_expires_days)

    payload: JWTPayload = {
        "sub": data["sub"],
        "email": data.get("email"),
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "tfaVerified": data.get("tfaVerified", False),
        "tfaMethod": data.get("tfaMethod"),
        # NOTE: tid/trol are NOT preserved in refresh token (security)
    }
    encoded_jwt = jwt.encode(dict(payload), settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt


def create_password_reset_token(data: dict[str, str]) -> str:
    """Create a JWT password reset token with 1-hour expiration."""
    now = datetime.now(UTC)
    expire = now + timedelta(hours=settings.security.password_reset_token_expires_hours)
    to_encode = {
        **data,
        "exp": int(expire.timestamp()),
        "type": "password_reset",
        "iat": int(now.timestamp()),
    }
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt

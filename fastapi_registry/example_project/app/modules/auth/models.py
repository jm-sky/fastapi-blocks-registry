"""User model and data store for authentication.

IMPORTANT: Module Integration Notice
=====================================

This auth module provides a complete User model with authentication features
(password hashing, JWT tokens, etc.). If you're also using the users module,
you should integrate them to share the same User model:

Integration Steps:
1. In users/dependencies.py, import from this auth module:
   from app.modules.auth.models import User
   from app.modules.auth.repositories import get_user_repository
   from app.modules.auth.dependencies import get_current_user

2. Remove users/models.py (or keep it as a reference)

3. Update users module to use the auth module's repository

This ensures both modules work with the same user data and there's no
duplication or inconsistency.

Database Configuration:
-----------------------
This module uses SQLAlchemy with async support. Configure via DATABASE_URL:

Development (SQLite with file):
  DATABASE_URL=sqlite+aiosqlite:///./dev.db

Development (in-memory, data lost on restart):
  DATABASE_URL=sqlite+aiosqlite:///:memory:

Production (PostgreSQL):
  DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

Additional features to consider:
- Email verification
- Two-factor authentication (2FA)
- OAuth integration
"""

import logging
import secrets
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr

from .auth_utils import (  # noqa: E402
    get_password_hash,
    verify_password,
    verify_token,
)
from .exceptions import (  # noqa: E402
    ExpiredTokenError,
    InvalidTokenError,
)


logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model with camelCase fields for API responses."""

    id: str  # ULID or UUID as string
    email: EmailStr
    name: str
    hashedPassword: str
    isActive: bool = True
    isAdmin: bool = False
    createdAt: datetime
    resetToken: str | None = None
    resetTokenExpiry: datetime | None = None

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return verify_password(password, self.hashedPassword)

    def set_password(self, password: str) -> None:
        """Set new password hash."""
        self.hashedPassword = get_password_hash(password)

    def set_reset_token(self, token: str, expiry: datetime) -> None:
        """Set password reset token and expiry."""
        self.resetToken = token
        self.resetTokenExpiry = expiry

    def clear_reset_token(self) -> None:
        """Clear password reset token."""
        self.resetToken = None
        self.resetTokenExpiry = None

    def is_reset_token_valid(self, token: str) -> bool:
        """Check if reset token is valid and not expired using secure comparison."""
        if not self.resetToken:
            return False

        try:
            # Verify JWT token
            payload = verify_token(token)

            # Check token type
            if payload.get("type") != "password_reset":
                logger.debug("Invalid token type for password reset")
                return False

            # Check if it matches stored token using secure comparison
            if not secrets.compare_digest(self.resetToken, token):
                logger.warning("Reset token mismatch for user %s", self.id)
                return False

            # Check user ID matches
            if payload.get("sub") != self.id:
                logger.warning("User ID mismatch in reset token")
                return False

            return True
        except ExpiredTokenError:
            logger.debug("Reset token expired for user %s", self.id)
            return False
        except InvalidTokenError:
            logger.debug("Invalid reset token for user %s", self.id)
            return False
        except Exception as e:
            logger.error("Unexpected error validating reset token: %s", e, exc_info=True)
            return False

    def to_response(self) -> dict[str, Any]:
        """Convert to camelCase response format."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "isActive": self.isActive,
            "isAdmin": self.isAdmin,
            "createdAt": self.createdAt
        }

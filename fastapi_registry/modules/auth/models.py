"""User model and data store for authentication.

IMPORTANT: Module Integration Notice
=====================================

This auth module provides a complete User model with authentication features
(password hashing, JWT tokens, etc.). If you're also using the users module,
you should integrate them to share the same User model:

Integration Steps:
1. In users/dependencies.py, import from this auth module:
   from app.modules.auth.models import user_store, User
   from app.modules.auth.dependencies import get_current_user

2. Remove users/models.py (or keep it as a reference)

3. Update users/service.py to use the auth module's user_store

This ensures both modules work with the same user data and there's no
duplication or inconsistency.

For production use:
- Replace in-memory UserStore with database (SQLAlchemy with PostgreSQL/MySQL)
- Implement proper session management
- Add email verification and 2FA if needed
"""

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

try:
    from ulid import ULID  # noqa: E402
    USE_ULID = True
except ImportError:
    import uuid  # noqa: E402
    USE_ULID = False

from .auth_utils import (  # noqa: E402
    create_password_reset_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from .exceptions import (  # noqa: E402
    ExpiredTokenError,
    InvalidTokenError,
    UserAlreadyExistsError,
)


class User(BaseModel):
    """User model with camelCase fields for API responses."""

    id: str  # ULID or UUID as string
    email: EmailStr
    name: str
    hashedPassword: str
    isActive: bool = True
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
            "createdAt": self.createdAt
        }


# Temporary in-memory user store (replace with database in production)
class UserStore:
    """In-memory user store for development and testing."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # ID -> User
        self._email_index: dict[str, str] = {}  # email -> ID

    def create_user(self, email: str, password: str, full_name: str) -> User:
        """Create a new user."""
        # Normalize email to lowercase for case-insensitive storage
        normalized_email = email.lower().strip()

        if normalized_email in self._email_index:
            raise UserAlreadyExistsError()

        # Generate new ID (ULID if available, otherwise UUID)
        if USE_ULID:
            user_id = str(ULID())
        else:
            user_id = str(uuid.uuid4())

        user = User(
            id=user_id,
            email=normalized_email,
            name=full_name,
            hashedPassword=get_password_hash(password),
            createdAt=datetime.now(UTC)
        )

        self._users[user_id] = user
        self._email_index[normalized_email] = user_id

        return user

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        normalized_email = email.lower().strip()
        user_id = self._email_index.get(normalized_email)
        if user_id:
            return self._users.get(user_id)
        return None

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self._users.get(user_id)

    def get_all_users(self) -> list[User]:
        """Get all users."""
        return list(self._users.values())

    def update_user(self, user: User) -> User:
        """Update user in store."""
        self._users[user.id] = user
        return user

    def generate_reset_token(self, email: str) -> str | None:
        """Generate and store JWT password reset token for user."""
        user = self.get_user_by_email(email)
        if not user or not user.isActive:
            return None

        # Generate JWT reset token
        token = create_password_reset_token(data={"sub": user.id})

        # Store token
        user.set_reset_token(token, datetime.now(UTC) + timedelta(hours=1))
        self.update_user(user)

        return token

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        for user in self._users.values():
            if user.is_reset_token_valid(token):
                user.set_password(new_password)
                user.clear_reset_token()
                self.update_user(user)
                return True
        return False

    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password."""
        user = self.get_user_by_id(user_id)
        if not user or not user.isActive:
            return False

        # Verify current password
        if not verify_password(current_password, user.hashedPassword):
            return False

        # Update password
        user.hashedPassword = get_password_hash(new_password)
        self.update_user(user)
        return True


# Global user store instance
user_store = UserStore()


def seed_development_user() -> None:
    """
    Create a default test user for development environment only.

    This function should ONLY be called when explicitly enabled via
    SEED_DEVELOPMENT_USER environment variable set to 'true'.

    Note:
        Test credentials:
        - Email: test@example.com
        - Password: Test123!@#
    """
    try:
        user_store.create_user(
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User"
        )
        logger.warning(
            "DEV MODE: Created test user account:\n"
            "  Email: test@example.com\n"
            "  Password: Test123!@#\n"
            "  IMPORTANT: Remove this user in production!"
        )
    except UserAlreadyExistsError:
        logger.debug("Development test user already exists")


# Only seed user if explicitly enabled AND not in production
environment = os.getenv("ENVIRONMENT", "production").lower()
seed_enabled = os.getenv("SEED_DEVELOPMENT_USER", "false").lower() == "true"

if seed_enabled:
    if environment != "production":
        seed_development_user()
    else:
        logger.error(
            "SECURITY WARNING: Attempted to seed development user in production environment. "
            "This is blocked for security reasons. Unset SEED_DEVELOPMENT_USER in production."
        )

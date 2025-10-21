"""User model and data store for authentication."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, EmailStr

try:
    from ulid import ULID
    USE_ULID = True
except ImportError:
    import uuid
    USE_ULID = False

from .auth_utils import (
    get_password_hash,
    verify_password,
    create_password_reset_token,
    verify_token
)
from .exceptions import UserAlreadyExistsError


class User(BaseModel):
    """User model with camelCase fields for API responses."""

    id: str  # ULID or UUID as string
    email: EmailStr
    name: str
    hashedPassword: str
    isActive: bool = True
    createdAt: datetime
    resetToken: Optional[str] = None
    resetTokenExpiry: Optional[datetime] = None

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
                return False

            # Check if it matches stored token using secure comparison
            if not secrets.compare_digest(self.resetToken, token):
                return False

            # Check user ID matches
            if payload.get("sub") != self.id:
                return False

            return True
        except Exception:
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
            createdAt=datetime.now(timezone.utc)
        )

        self._users[user_id] = user
        self._email_index[normalized_email] = user_id

        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        normalized_email = email.lower().strip()
        user_id = self._email_index.get(normalized_email)
        if user_id:
            return self._users.get(user_id)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    def get_all_users(self) -> list[User]:
        """Get all users."""
        return list(self._users.values())

    def update_user(self, user: User) -> User:
        """Update user in store."""
        self._users[user.id] = user
        return user

    def generate_reset_token(self, email: str) -> Optional[str]:
        """Generate and store JWT password reset token for user."""
        user = self.get_user_by_email(email)
        if not user or not user.isActive:
            return None

        # Generate JWT reset token
        token = create_password_reset_token(data={"sub": user.id})

        # Store token
        user.set_reset_token(token, datetime.now(timezone.utc) + timedelta(hours=1))
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
    """Create a default test user for development environment only."""
    try:
        user_store.create_user(
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User"
        )
    except UserAlreadyExistsError:
        pass  # User already exists


# Only seed user in development environment
if os.getenv("ENVIRONMENT", "development").lower() == "development":
    seed_development_user()

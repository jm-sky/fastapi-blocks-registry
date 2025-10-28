"""User model for user management module.

IMPORTANT: Module Integration Notice
=====================================

This users module has its own User model and UserStore that is separate from
the auth module's User model. This is intentional for demonstration purposes,
but in a real application you should:

1. If using BOTH auth and users modules together:
   - Modify users/dependencies.py to import from auth module:
     from app.modules.auth.models import user_store
     from app.modules.auth.dependencies import get_current_user
   - Remove this models.py file from users module
   - Use the auth module's User model as the single source of truth

2. If using ONLY users module (without auth):
   - Keep this model as-is
   - Implement your own authentication in users/dependencies.py
   - Replace the mock get_current_user() with real authentication

For production use, it's recommended to:
- Use a single User model shared between modules
- Store users in a database (PostgreSQL, MySQL, etc.) not in-memory
- Implement proper authentication and authorization
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, EmailStr

try:
    from ulid import ULID
    USE_ULID = True
except ImportError:
    import uuid
    USE_ULID = False


class User(BaseModel):
    """User model with camelCase fields for API responses."""

    id: str  # ULID or UUID as string
    email: EmailStr
    name: str
    role: str = "user"  # user, admin, etc.
    isActive: bool = True
    createdAt: datetime
    updatedAt: datetime

    def to_response(self) -> dict[str, Any]:
        """Convert to camelCase response format."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "isActive": self.isActive,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }


class UserStore:
    """In-memory user store for development and testing."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # ID -> User
        self._email_index: dict[str, str] = {}  # email -> ID

    def create_user(self, email: str, name: str, role: str = "user") -> User:
        """Create a new user."""
        # Normalize email to lowercase for case-insensitive storage
        normalized_email = email.lower().strip()

        if normalized_email in self._email_index:
            raise ValueError(f"User with email {email} already exists")

        # Generate new ID (ULID if available, otherwise UUID)
        if USE_ULID:
            user_id = str(ULID())
        else:
            user_id = str(uuid.uuid4())

        now = datetime.now(UTC)
        user = User(
            id=user_id,
            email=normalized_email,
            name=name,
            role=role,
            isActive=True,
            createdAt=now,
            updatedAt=now,
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

    def get_all_users(
        self, skip: int = 0, limit: int = 100, include_inactive: bool = False
    ) -> list[User]:
        """Get all users with pagination."""
        users = list(self._users.values())

        if not include_inactive:
            users = [u for u in users if u.isActive]

        return users[skip : skip + limit]

    def update_user(
        self,
        user_id: str,
        email: str | None = None,
        name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        """Update user fields."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Handle email update
        if email is not None:
            normalized_email = email.lower().strip()
            if normalized_email != user.email:
                # Check if new email is already taken
                if normalized_email in self._email_index:
                    raise ValueError(f"Email {email} is already in use")

                # Remove old email from index
                del self._email_index[user.email]
                # Add new email to index
                self._email_index[normalized_email] = user_id
                user.email = normalized_email

        # Update other fields
        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.isActive = is_active

        user.updatedAt = datetime.now(UTC)
        self._users[user_id] = user

        return user

    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by default - set isActive to False)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.isActive = False
        user.updatedAt = datetime.now(UTC)
        self._users[user_id] = user
        return True

    def hard_delete_user(self, user_id: str) -> bool:
        """Permanently delete user from store."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        del self._email_index[user.email]
        del self._users[user_id]
        return True

    def count_users(self, include_inactive: bool = False) -> int:
        """Count total users."""
        if include_inactive:
            return len(self._users)
        return sum(1 for u in self._users.values() if u.isActive)


# Global user store instance
user_store = UserStore()

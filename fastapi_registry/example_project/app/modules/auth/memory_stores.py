"""In-memory user repository for development and testing.

This module provides an in-memory implementation of the user repository interface.
It's useful for:
- Quick prototyping and development
- Testing without database setup
- Demos and examples

Note: Data is lost when the application restarts. For production, use repositories.py.
"""

import logging
from datetime import UTC, datetime, timedelta

try:
    from ulid import ULID  # noqa: E402
    USE_ULID = True
except ImportError:
    import uuid  # noqa: E402
    USE_ULID = False

from .models import User
from .types import UserRepositoryInterface
from .auth_utils import (  # noqa: E402
    create_password_reset_token,
    get_password_hash,
    verify_password,
)
from .exceptions import (  # noqa: E402
    UserAlreadyExistsError,
)


logger = logging.getLogger(__name__)


class MemoryUserStore(UserRepositoryInterface):
    """In-memory user store for development and testing.

    This implementation stores users in memory (dictionaries) and provides
    async methods that match the interface but don't actually perform I/O.
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # ID -> User
        self._email_index: dict[str, str] = {}  # email -> ID


    async def create_user(self, email: str, password: str, full_name: str) -> User:
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


    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        normalized_email = email.lower().strip()
        user_id = self._email_index.get(normalized_email)
        if user_id:
            return self._users.get(user_id)
        return None


    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self._users.get(user_id)


    async def get_all_users(self) -> list[User]:
        """Get all users."""
        return list(self._users.values())


    async def update_user(self, user: User) -> User:
        """Update user in store."""
        self._users[user.id] = user
        return user


    async def generate_reset_token(self, email: str) -> str | None:
        """Generate and store JWT password reset token for user."""
        user = await self.get_user_by_email(email)
        if not user or not user.isActive:
            return None

        # Generate JWT reset token
        token = create_password_reset_token(data={"sub": user.id})

        # Store token
        user.set_reset_token(token, datetime.now(UTC) + timedelta(hours=1))
        await self.update_user(user)

        return token


    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        for user in self._users.values():
            if user.is_reset_token_valid(token):
                user.set_password(new_password)
                user.clear_reset_token()
                await self.update_user(user)
                return True
        return False


    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password."""
        user = await self.get_user_by_id(user_id)
        if not user or not user.isActive:
            return False

        # Verify current password
        if not verify_password(current_password, user.hashedPassword):
            return False

        # Update password
        user.hashedPassword = get_password_hash(new_password)
        await self.update_user(user)
        return True


# Global user store instance
user_repository = MemoryUserStore()

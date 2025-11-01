"""Repository interface for user storage implementations.

This module defines the abstract interface that both in-memory and database
repositories must implement. This allows easy switching between implementations.
"""

from abc import ABC, abstractmethod

from ..models import User


class UserRepositoryInterface(ABC):
    """Abstract interface for user repository implementations.

    Implementations:
    - UserStore (memory_stores.py): In-memory storage for dev/testing
    - UserRepository (repositories.py): Database storage for production
    """

    @abstractmethod
    async def create_user(self, email: str, password: str, full_name: str) -> User:
        """Create a new user.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            full_name: User's full name

        Returns:
            Created user object

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        ...

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User email to search for

        Returns:
            User object if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by unique ID.

        Args:
            user_id: User ID (ULID format)

        Returns:
            User object if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_all_users(self) -> list[User]:
        """Get all users.

        Returns:
            List of all user objects
        """
        ...

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update user in storage.

        Args:
            user: User object with updated fields

        Returns:
            Updated user object
        """
        ...

    @abstractmethod
    async def generate_reset_token(self, email: str) -> str | None:
        """Generate and store JWT password reset token for user.

        Args:
            email: User email address

        Returns:
            Reset token (JWT) if user found and active, None otherwise
        """
        ...

    @abstractmethod
    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using token.

        Args:
            token: Password reset token (JWT)
            new_password: New plain text password

        Returns:
            True if password reset successful, False otherwise
        """
        ...

    @abstractmethod
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password.

        Args:
            user_id: User ID
            current_password: Current plain text password
            new_password: New plain text password

        Returns:
            True if password changed successfully, False otherwise
        """
        ...

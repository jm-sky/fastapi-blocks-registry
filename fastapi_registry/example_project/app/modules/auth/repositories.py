"""Database repository implementation for user management.

This module provides async PostgreSQL/SQLite repository using SQLAlchemy 2.0+.
For quick development, use SQLite with DATABASE_URL="sqlite+aiosqlite:///./dev.db"
or in-memory with DATABASE_URL="sqlite+aiosqlite:///:memory:"
"""

import logging
from datetime import UTC, datetime, timedelta

try:
    from ulid import ULID
    USE_ULID = True
except ImportError:
    import uuid
    USE_ULID = False

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .types.repository import UserRepositoryInterface
from .models import User
from .db_models import UserDB
from .auth_utils import (
    create_password_reset_token,
    get_password_hash,
    verify_password,
)
from .exceptions import (
    UserAlreadyExistsError,
)


logger = logging.getLogger(__name__)


class UserRepository(UserRepositoryInterface):
    """User repository for async database operations.

    This implementation uses SQLAlchemy 2.0+ with async sessions
    for PostgreSQL or SQLite database access.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db


    async def create_user(self, email: str, password: str, full_name: str, is_admin: bool = False) -> User:
        """Create a new user in database."""
        # Normalize email to lowercase for case-insensitive storage
        normalized_email = email.lower().strip()

        # Check if user already exists
        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()

        # Generate new ID (ULID if available, otherwise UUID)
        if USE_ULID:
            user_id = str(ULID())
        else:
            user_id = str(uuid.uuid4())

        # Create UserDB instance
        user_db = UserDB(
            id=user_id,
            email=normalized_email,
            name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
            created_at=datetime.now(UTC)
        )

        self.db.add(user_db)
        await self.db.commit()
        await self.db.refresh(user_db)

        # Convert to Pydantic User model for response
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password,
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            createdAt=user_db.created_at
        )


    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email from database."""
        normalized_email = email.lower().strip()

        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        # Convert to Pydantic User model
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password,
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            createdAt=user_db.created_at,
            resetToken=user_db.reset_token,
            resetTokenExpiry=user_db.reset_token_expiry
        )


    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID from database."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        # Convert to Pydantic User model
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password,
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            createdAt=user_db.created_at,
            resetToken=user_db.reset_token,
            resetTokenExpiry=user_db.reset_token_expiry
        )


    async def get_all_users(self) -> list[User]:
        """Get all users from database."""
        stmt = select(UserDB)
        result = await self.db.execute(stmt)
        users_db = result.scalars().all()

        # Convert to Pydantic User models
        return [
            User(
                id=user_db.id,
                email=user_db.email,
                name=user_db.name,
                hashedPassword=user_db.hashed_password,
                isActive=user_db.is_active,
                isAdmin=user_db.is_admin,
                createdAt=user_db.created_at,
                resetToken=user_db.reset_token,
                resetTokenExpiry=user_db.reset_token_expiry
            )
            for user_db in users_db
        ]


    async def update_user(self, user: User) -> User:
        """Update user in database."""
        # Get existing user from database
        stmt = select(UserDB).where(UserDB.id == user.id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            raise ValueError(f"User with id {user.id} not found")

        # Update fields
        user_db.email = user.email
        user_db.name = user.name
        user_db.hashed_password = user.hashedPassword
        user_db.is_active = user.isActive
        user_db.is_admin = user.isAdmin
        user_db.reset_token = user.resetToken
        user_db.reset_token_expiry = user.resetTokenExpiry

        await self.db.commit()
        await self.db.refresh(user_db)

        # Return updated user as Pydantic model
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password,
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            createdAt=user_db.created_at,
            resetToken=user_db.reset_token,
            resetTokenExpiry=user_db.reset_token_expiry
        )


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
        # Find user with this token
        stmt = select(UserDB).where(UserDB.reset_token == token)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return False

        # Convert to Pydantic model to use validation methods
        user = User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password,
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            createdAt=user_db.created_at,
            resetToken=user_db.reset_token,
            resetTokenExpiry=user_db.reset_token_expiry
        )

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


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepositoryInterface:
    """
    FastAPI dependency to get user repository instance.

    Args:
        db: Async database session from dependency

    Returns:
        UserRepository instance configured with the session

    Example:
        @router.get("/users")
        async def list_users(
            repo: UserRepository = Depends(get_user_repository)
        ):
            return await repo.get_all_users()

    Configuration:
        For development, use SQLite in your .env:
            DATABASE_URL=sqlite+aiosqlite:///./dev.db

        For in-memory database (data lost on restart):
            DATABASE_URL=sqlite+aiosqlite:///:memory:

        For production, use PostgreSQL:
            DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    """
    return UserRepository(db)

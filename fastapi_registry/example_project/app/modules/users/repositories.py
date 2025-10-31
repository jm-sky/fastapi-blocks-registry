"""Database repository implementation for user management.

This module provides async PostgreSQL/SQLite repository using SQLAlchemy 2.0+.
For quick development, use SQLite with DATABASE_URL="sqlite+aiosqlite:///./dev.db"
or in-memory with DATABASE_URL="sqlite+aiosqlite:///:memory:"
"""

import logging
from datetime import UTC, datetime

try:
    from ulid import ULID
    USE_ULID = True
except ImportError:
    import uuid
    USE_ULID = False

from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.search import SearchMixin

from .models import User
from .db_models import UserDB
from .exceptions import UserAlreadyExistsError


logger = logging.getLogger(__name__)


class UserRepository(SearchMixin):
    """User repository for async database operations.

    This implementation uses SQLAlchemy 2.0+ with async sessions
    for PostgreSQL or SQLite database access.

    Supports search across: name, email, role
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        # Define searchable columns for SearchMixin
        self._search_columns = [UserDB.name, UserDB.email, UserDB.role]
        self._case_sensitive = False


    async def create_user(self, email: str, name: str, role: str = "user") -> User:
        """Create a new user in database."""
        # Normalize email to lowercase for case-insensitive storage
        normalized_email = email.lower().strip()

        # Check if user already exists
        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError(f"User with email {email} already exists")

        # Generate new ID (ULID if available, otherwise UUID)
        if USE_ULID:
            user_id = str(ULID())
        else:
            user_id = str(uuid.uuid4())

        now = datetime.now(UTC)

        # Create UserDB instance
        user_db = UserDB(
            id=user_id,
            email=normalized_email,
            name=name,
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        self.db.add(user_db)
        await self.db.commit()
        await self.db.refresh(user_db)

        # Convert to Pydantic User model for response
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            role=user_db.role,
            isActive=user_db.is_active,
            createdAt=user_db.created_at,
            updatedAt=user_db.updated_at
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
            role=user_db.role,
            isActive=user_db.is_active,
            createdAt=user_db.created_at,
            updatedAt=user_db.updated_at
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
            role=user_db.role,
            isActive=user_db.is_active,
            createdAt=user_db.created_at,
            updatedAt=user_db.updated_at
        )


    async def get_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        search: str | None = None
    ) -> list[User]:
        """Get all users from database with pagination and search.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Include inactive users
            search: Search term (searches in name, email, role)

        Returns:
            List of users matching criteria
        """
        stmt = select(UserDB)

        if not include_inactive:
            stmt = stmt.where(UserDB.is_active == True)  # noqa: E712

        # Apply search filter
        if search:
            stmt = self.apply_search(stmt, search)

        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        users_db = result.scalars().all()

        # Convert to Pydantic User models
        return [
            User(
                id=user_db.id,
                email=user_db.email,
                name=user_db.name,
                role=user_db.role,
                isActive=user_db.is_active,
                createdAt=user_db.created_at,
                updatedAt=user_db.updated_at
            )
            for user_db in users_db
        ]


    async def update_user(
        self,
        user_id: str,
        email: str | None = None,
        name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        """Update user fields in database."""
        # Get existing user from database
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        # Handle email update
        if email is not None:
            normalized_email = email.lower().strip()
            if normalized_email != user_db.email:
                # Check if new email is already taken
                email_stmt = select(UserDB).where(UserDB.email == normalized_email)
                email_result = await self.db.execute(email_stmt)
                if email_result.scalar_one_or_none():
                    raise UserAlreadyExistsError(f"Email {email} is already in use")

                user_db.email = normalized_email

        # Update other fields
        if name is not None:
            user_db.name = name
        if role is not None:
            user_db.role = role
        if is_active is not None:
            user_db.is_active = is_active

        user_db.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(user_db)

        # Return updated user as Pydantic model
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            role=user_db.role,
            isActive=user_db.is_active,
            createdAt=user_db.created_at,
            updatedAt=user_db.updated_at
        )


    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete - set is_active to False)."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return False

        user_db.is_active = False
        user_db.updated_at = datetime.now(UTC)

        await self.db.commit()
        return True


    async def hard_delete_user(self, user_id: str) -> bool:
        """Permanently delete user from database."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return False

        await self.db.delete(user_db)
        await self.db.commit()
        return True


    async def count_users(
        self,
        include_inactive: bool = False,
        search: str | None = None
    ) -> int:
        """Count total users in database with optional search.

        Args:
            include_inactive: Include inactive users in count
            search: Search term (searches in name, email, role)

        Returns:
            Total count of users matching criteria
        """
        stmt = select(func.count(UserDB.id))

        if not include_inactive:
            stmt = stmt.where(UserDB.is_active == True)  # noqa: E712

        # Apply search filter
        if search:
            stmt = self.apply_search(stmt, search)

        result = await self.db.execute(stmt)
        return result.scalar_one()


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
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

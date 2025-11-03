"""SQLAlchemy database models for user management.

This module provides SQLAlchemy ORM models for database persistence.
The UserDB model is designed to work with async SQLAlchemy sessions.

Note: If you're using both auth and users modules, consider using the
UserDB model from the auth module instead to avoid duplication. You can
extend it with additional fields like 'role' if needed.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserDB(Base):
    """SQLAlchemy User model for database persistence.

    This model represents the user table in the database and provides
    the structure for persistent user data storage with role management.

    Note: If both auth and users modules are loaded, this will extend
    the existing 'users' table from the auth module.

    Attributes:
        id: Unique identifier (ULID format, 36 chars)
        email: User email address (unique, indexed)
        name: User full name
        role: User role (user, admin, etc.)
        is_active: Whether the user account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserDB(id={self.id}, email={self.email}, name={self.name}, role={self.role})>"

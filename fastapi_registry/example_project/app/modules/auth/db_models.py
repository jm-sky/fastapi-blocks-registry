"""SQLAlchemy database models for authentication.

This module provides SQLAlchemy ORM models for database persistence.
The UserDB model is designed to work with async SQLAlchemy sessions.

Note: This module complements models.py which contains:
- Pydantic models for API validation (User)
- In-memory UserStore for development/testing

For production use, replace UserStore with database operations using UserDB.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserDB(Base):
    """SQLAlchemy User model for database persistence.

    This model represents the user table in the database and provides
    the structure for persistent user data storage.

    Note: If both auth and users modules are loaded, the table will be
    extended with additional fields from the users module (like 'role').

    Attributes:
        id: Unique identifier (ULID format, 36 chars)
        email: User email address (unique, indexed)
        name: User full name
        hashed_password: Bcrypt hashed password
        is_active: Whether the user account is active
        is_admin: Whether the user has administrator privileges
        created_at: Account creation timestamp
        reset_token: Password reset token (JWT)
        reset_token_expiry: Password reset token expiration time
    """

    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    reset_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    reset_token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<UserDB(id={self.id}, email={self.email}, name={self.name})>"

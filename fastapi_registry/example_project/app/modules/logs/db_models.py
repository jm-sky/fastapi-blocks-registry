"""SQLAlchemy database models for logging system.

This module provides database models for storing application logs,
including errors, warnings, and informational messages.
"""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogDB(Base):
    """SQLAlchemy Log model for database persistence.

    This model stores application logs with metadata for debugging
    and monitoring purposes.

    Attributes:
        id: Unique identifier (ULID format, 36 chars)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        module: Module/file where log originated
        function: Function name where log originated
        user_id: Optional user ID if action was user-initiated
        request_id: Optional request ID for tracing
        traceback: Full traceback for errors (optional)
        extra_data: Additional JSON/text data (optional)
        created_at: Timestamp when log was created
    """

    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(255), nullable=True)
    function: Mapped[str] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_logs_level_created_at', 'level', 'created_at'),
        Index('ix_logs_user_created_at', 'user_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<LogDB(id={self.id}, level={self.level}, message={self.message[:50]}...)>"

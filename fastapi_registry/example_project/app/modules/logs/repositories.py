"""Database repository implementation for logs.

This module provides async PostgreSQL/SQLite repository using SQLAlchemy 2.0+.
For quick development, use SQLite with DATABASE_URL="sqlite+aiosqlite:///./dev.db"
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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.search import SearchMixin

from .models import Log
from .db_models import LogDB, LogLevel


logger = logging.getLogger(__name__)


class LogRepository(SearchMixin):
    """Log repository for async database operations.

    This implementation uses SQLAlchemy 2.0+ with async sessions
    for PostgreSQL or SQLite database access.

    Supports search across: message, module, function
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        # Define searchable columns for SearchMixin
        self._search_columns = [LogDB.message, LogDB.module, LogDB.function]
        self._case_sensitive = False


    async def create_log(
        self,
        level: LogLevel,
        message: str,
        module: str | None = None,
        function: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        traceback: str | None = None,
        extra_data: str | None = None
    ) -> Log:
        """Create a new log entry in database."""
        # Generate new ID (ULID if available, otherwise UUID)
        if USE_ULID:
            log_id = str(ULID())
        else:
            log_id = str(uuid.uuid4())

        # Create LogDB instance
        log_db = LogDB(
            id=log_id,
            level=level.value,
            message=message,
            module=module,
            function=function,
            user_id=user_id,
            request_id=request_id,
            traceback=traceback,
            extra_data=extra_data,
            created_at=datetime.now(UTC)
        )

        self.db.add(log_db)
        await self.db.commit()
        await self.db.refresh(log_db)

        # Convert to Pydantic Log model for response
        return Log.model_validate(log_db)


    async def get_log_by_id(self, log_id: str) -> Log | None:
        """Get log by ID from database."""
        stmt = select(LogDB).where(LogDB.id == log_id)
        result = await self.db.execute(stmt)
        log_db = result.scalar_one_or_none()

        if not log_db:
            return None

        # Convert to Pydantic Log model
        return Log.model_validate(log_db)


    async def get_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        level: LogLevel | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        module: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None
    ) -> list[Log]:
        """Get logs from database with filters, search, and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            level: Filter by log level
            user_id: Filter by user ID
            request_id: Filter by request ID
            module: Filter by module name
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            search: Search term (searches in message, module, function)

        Returns:
            List of logs matching criteria
        """
        stmt = select(LogDB)

        # Apply filters
        filters = []
        if level:
            filters.append(LogDB.level == level.value)
        if user_id:
            filters.append(LogDB.user_id == user_id)
        if request_id:
            filters.append(LogDB.request_id == request_id)
        if module:
            filters.append(LogDB.module == module)
        if start_date:
            filters.append(LogDB.created_at >= start_date)
        if end_date:
            filters.append(LogDB.created_at <= end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Apply search filter
        if search:
            stmt = self.apply_search(stmt, search)

        # Order by newest first
        stmt = stmt.order_by(LogDB.created_at.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        logs_db = result.scalars().all()

        # Convert to Pydantic Log models
        return [Log.model_validate(log_db) for log_db in logs_db]


    async def get_error_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None
    ) -> list[Log]:
        """Get only ERROR and CRITICAL level logs."""
        stmt = select(LogDB).where(
            or_(
                LogDB.level == LogLevel.ERROR.value,
                LogDB.level == LogLevel.CRITICAL.value
            )
        )

        if user_id:
            stmt = stmt.where(LogDB.user_id == user_id)

        stmt = stmt.order_by(LogDB.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        logs_db = result.scalars().all()

        return [Log.model_validate(log_db) for log_db in logs_db]


    async def count_logs(
        self,
        level: LogLevel | None = None,
        user_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None
    ) -> int:
        """Count logs with optional filters and search.

        Args:
            level: Filter by log level
            user_id: Filter by user ID
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            search: Search term (searches in message, module, function)

        Returns:
            Total count of logs matching criteria
        """
        stmt = select(func.count(LogDB.id))

        filters = []
        if level:
            filters.append(LogDB.level == level.value)
        if user_id:
            filters.append(LogDB.user_id == user_id)
        if start_date:
            filters.append(LogDB.created_at >= start_date)
        if end_date:
            filters.append(LogDB.created_at <= end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Apply search filter
        if search:
            stmt = self.apply_search(stmt, search)

        result = await self.db.execute(stmt)
        return result.scalar_one()


    async def delete_old_logs(self, before_date: datetime) -> int:
        """Delete logs older than specified date.

        Args:
            before_date: Delete logs created before this date

        Returns:
            Number of deleted logs
        """
        stmt = select(LogDB).where(LogDB.created_at < before_date)
        result = await self.db.execute(stmt)
        logs_to_delete = result.scalars().all()

        count = len(logs_to_delete)
        for log_db in logs_to_delete:
            await self.db.delete(log_db)

        await self.db.commit()
        return count


def get_log_repository(db: AsyncSession = Depends(get_db)) -> LogRepository:
    """
    FastAPI dependency to get log repository instance.

    Args:
        db: Async database session from dependency

    Returns:
        LogRepository instance configured with the session

    Example:
        @router.get("/logs")
        async def list_logs(
            repo: LogRepository = Depends(get_log_repository)
        ):
            return await repo.get_logs()
    """
    return LogRepository(db)

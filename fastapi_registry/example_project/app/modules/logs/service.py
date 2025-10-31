"""Service layer for logging operations.

This module provides high-level business logic for log management.
"""

import logging
import traceback as tb
from datetime import datetime

from .db_models import LogLevel
from .models import Log
from .repositories import LogRepository


logger = logging.getLogger(__name__)


class LogService:
    """Service class for log operations."""

    def __init__(self, log_repository: LogRepository):
        """Initialize service with log repository.

        Args:
            log_repository: Log repository instance
        """
        self.log_repository = log_repository


    async def log_error(
        self,
        message: str,
        exception: Exception | None = None,
        module: str | None = None,
        function: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        extra_data: str | None = None
    ) -> Log:
        """Log an error with optional exception traceback.

        Args:
            message: Error message
            exception: Exception object (optional)
            module: Module name where error occurred
            function: Function name where error occurred
            user_id: User ID if error was user-initiated
            request_id: Request ID for tracing
            extra_data: Additional data as string

        Returns:
            Created log entry
        """
        traceback_str = None
        if exception:
            traceback_str = ''.join(tb.format_exception(
                type(exception), exception, exception.__traceback__
            ))

        return await self.log_repository.create_log(
            level=LogLevel.ERROR,
            message=message,
            module=module,
            function=function,
            user_id=user_id,
            request_id=request_id,
            traceback=traceback_str,
            extra_data=extra_data
        )


    async def log_warning(
        self,
        message: str,
        module: str | None = None,
        function: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        extra_data: str | None = None
    ) -> Log:
        """Log a warning message.

        Args:
            message: Warning message
            module: Module name
            function: Function name
            user_id: User ID if relevant
            request_id: Request ID for tracing
            extra_data: Additional data

        Returns:
            Created log entry
        """
        return await self.log_repository.create_log(
            level=LogLevel.WARNING,
            message=message,
            module=module,
            function=function,
            user_id=user_id,
            request_id=request_id,
            extra_data=extra_data
        )


    async def log_info(
        self,
        message: str,
        module: str | None = None,
        function: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        extra_data: str | None = None
    ) -> Log:
        """Log an informational message.

        Args:
            message: Info message
            module: Module name
            function: Function name
            user_id: User ID if relevant
            request_id: Request ID for tracing
            extra_data: Additional data

        Returns:
            Created log entry
        """
        return await self.log_repository.create_log(
            level=LogLevel.INFO,
            message=message,
            module=module,
            function=function,
            user_id=user_id,
            request_id=request_id,
            extra_data=extra_data
        )


    async def get_recent_errors(
        self,
        limit: int = 50,
        user_id: str | None = None
    ) -> list[Log]:
        """Get recent error logs.

        Args:
            limit: Maximum number of logs to return
            user_id: Filter by user ID (optional)

        Returns:
            List of error log entries
        """
        return await self.log_repository.get_error_logs(
            skip=0,
            limit=limit,
            user_id=user_id
        )


    async def get_logs_by_request(self, request_id: str) -> list[Log]:
        """Get all logs for a specific request.

        Args:
            request_id: Request ID to filter by

        Returns:
            List of log entries for the request
        """
        return await self.log_repository.get_logs(
            request_id=request_id,
            limit=1000  # Reasonable limit for single request
        )


    async def cleanup_old_logs(self, days: int = 30) -> int:
        """Delete logs older than specified number of days.

        Args:
            days: Delete logs older than this many days

        Returns:
            Number of deleted logs
        """
        from datetime import timedelta, UTC

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        deleted_count = await self.log_repository.delete_old_logs(cutoff_date)

        logger.info(f"Deleted {deleted_count} logs older than {days} days")
        return deleted_count

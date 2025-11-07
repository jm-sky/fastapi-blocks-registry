"""Logging module for FastAPI applications.

This module provides comprehensive logging functionality with:
- Database storage for logs (PostgreSQL/SQLite)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic error logging decorator
- Request tracing support
- User activity tracking
- REST API for log management
- Automatic cleanup of old logs

Usage:
    # Using the decorator
    from app.modules.log_management.decorators import log_errors

    @log_errors(message="Failed to process data")
    async def process_data(data: dict, log_service: LogService):
        # Your code here
        pass

    # Using the service directly
    from app.modules.log_management.service import LogService

    await log_service.log_error(
        message="Something went wrong",
        exception=e,
        user_id=user.id
    )
"""

from .db_models import LogDB, LogLevel
from .decorators import log_errors
from .models import Log, LogCreate
from .repositories import LogRepository, get_log_repository
from .router import router
from .schemas import (
    LogCreateRequest,
    LogListResponse,
    LogResponse,
    MessageResponse,
)
from .service import LogService

__all__ = [
    "router",
    "Log",
    "LogCreate",
    "LogLevel",
    "LogDB",
    "LogService",
    "LogRepository",
    "get_log_repository",
    "log_errors",
    "LogResponse",
    "LogCreateRequest",
    "LogListResponse",
    "MessageResponse",
]

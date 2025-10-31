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
    from app.modules.logs.decorators import log_errors

    @log_errors(message="Failed to process data")
    async def process_data(data: dict, log_service: LogService):
        # Your code here
        pass

    # Using the service directly
    from app.modules.logs.service import LogService

    await log_service.log_error(
        message="Something went wrong",
        exception=e,
        user_id=user.id
    )
"""

from .router import router
from .models import Log, LogCreate
from .db_models import LogLevel, LogDB
from .service import LogService
from .repositories import LogRepository, get_log_repository
from .decorators import log_errors
from .schemas import (
    LogResponse,
    LogCreateRequest,
    LogListResponse,
    MessageResponse,
)

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

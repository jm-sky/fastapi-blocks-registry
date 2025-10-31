"""FastAPI router for logs management endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .db_models import LogLevel
from .repositories import LogRepository, get_log_repository
from .service import LogService
from .schemas import (
    LogCreateRequest,
    LogListResponse,
    LogResponse,
    MessageResponse,
)


# Create router
router = APIRouter()


def get_log_service(
    repo: Annotated[LogRepository, Depends(get_log_repository)]
) -> LogService:
    """Dependency to get log service instance."""
    return LogService(repo)


@router.post(
    "/",
    response_model=LogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new log entry",
    description="Manually create a new log entry",
)
async def create_log(
    log_data: LogCreateRequest,
    service: Annotated[LogService, Depends(get_log_service)]
) -> LogResponse:
    """Create a new log entry."""
    log = await service.log_repository.create_log(
        level=log_data.level,
        message=log_data.message,
        module=log_data.module,
        function=log_data.function,
        user_id=log_data.userId,
        request_id=log_data.requestId,
        traceback=log_data.traceback,
        extra_data=log_data.extraData
    )
    return LogResponse(**log.to_response())


@router.get(
    "/",
    response_model=LogListResponse,
    summary="List logs",
    description="Get list of logs with filtering, search, and pagination",
)
async def list_logs(
    repo: Annotated[LogRepository, Depends(get_log_repository)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    level: LogLevel | None = Query(default=None, description="Filter by log level"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    request_id: str | None = Query(default=None, description="Filter by request ID"),
    module: str | None = Query(default=None, description="Filter by module name"),
    start_date: datetime | None = Query(default=None, description="Filter logs after this date"),
    end_date: datetime | None = Query(default=None, description="Filter logs before this date"),
    search: str | None = Query(default=None, description="Search in message, module, and function"),
) -> LogListResponse:
    """Get list of logs with filters and search.

    Search is performed across message, module, and function fields.
    Example: ?search=error will find logs with 'error' in message, module, or function.
    """
    logs = await repo.get_logs(
        skip=skip,
        limit=limit,
        level=level,
        user_id=user_id,
        request_id=request_id,
        module=module,
        start_date=start_date,
        end_date=end_date,
        search=search
    )
    total = await repo.count_logs(
        level=level,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        search=search
    )

    return LogListResponse(
        logs=[LogResponse(**log.to_response()) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/errors",
    response_model=LogListResponse,
    summary="Get error logs",
    description="Get list of ERROR and CRITICAL level logs",
)
async def get_error_logs(
    service: Annotated[LogService, Depends(get_log_service)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
) -> LogListResponse:
    """Get error and critical logs."""
    logs = await service.log_repository.get_error_logs(
        skip=skip,
        limit=limit,
        user_id=user_id
    )

    # Count only error logs
    total = await service.log_repository.count_logs(level=LogLevel.ERROR)
    total += await service.log_repository.count_logs(level=LogLevel.CRITICAL)

    return LogListResponse(
        logs=[LogResponse(**log.to_response()) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/request/{request_id}",
    response_model=list[LogResponse],
    summary="Get logs by request ID",
    description="Get all logs associated with a specific request",
)
async def get_logs_by_request(
    request_id: str,
    service: Annotated[LogService, Depends(get_log_service)]
) -> list[LogResponse]:
    """Get all logs for a specific request."""
    logs = await service.get_logs_by_request(request_id)
    return [LogResponse(**log.to_response()) for log in logs]


@router.get(
    "/{log_id}",
    response_model=LogResponse,
    summary="Get log by ID",
    description="Get a specific log entry by its ID",
)
async def get_log(
    log_id: str,
    repo: Annotated[LogRepository, Depends(get_log_repository)]
) -> LogResponse:
    """Get log by ID."""
    log = await repo.get_log_by_id(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found"
        )
    return LogResponse(**log.to_response())


@router.delete(
    "/cleanup",
    response_model=MessageResponse,
    summary="Cleanup old logs",
    description="Delete logs older than specified number of days",
)
async def cleanup_logs(
    service: Annotated[LogService, Depends(get_log_service)],
    days: int = Query(default=30, ge=1, le=365, description="Delete logs older than N days")
) -> MessageResponse:
    """Delete old logs."""
    deleted_count = await service.cleanup_old_logs(days=days)
    return MessageResponse(
        message=f"Successfully deleted {deleted_count} logs older than {days} days"
    )

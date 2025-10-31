"""Example usage of the logs module.

This file demonstrates how to use the logging module in your FastAPI application.
"""

from fastapi import APIRouter, Depends, HTTPException
from app.modules.logs.decorators import log_errors
from app.modules.logs.service import LogService
from app.modules.logs.repositories import get_log_repository, LogRepository
from app.modules.logs.db_models import LogLevel


# Example router
example_router = APIRouter(prefix="/example", tags=["example"])


# Example 1: Using the decorator with automatic error logging
@example_router.post("/process-data")
@log_errors(message="Failed to process data")
async def process_data_endpoint(
    data: dict,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates automatic error logging.
    If an exception occurs, it will be automatically logged to the database.
    """
    log_service = LogService(repo)

    # Simulate some processing that might fail
    if data.get("should_fail"):
        raise ValueError("Processing failed as requested")

    # Log successful processing
    await log_service.log_info(
        message="Successfully processed data",
        module="example",
        function="process_data_endpoint",
        extra_data=str(data)
    )

    return {"status": "success", "data": data}


# Example 2: Manual error logging with full control
@example_router.post("/create-item")
async def create_item_endpoint(
    item: dict,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates manual error logging
    where you have full control over what gets logged.
    """
    log_service = LogService(repo)

    try:
        # Simulate item creation
        if not item.get("name"):
            raise ValueError("Item name is required")

        # Log successful creation
        await log_service.log_info(
            message=f"Item created: {item.get('name')}",
            module="example",
            function="create_item_endpoint"
        )

        return {"status": "created", "item": item}

    except ValueError as e:
        # Log validation error as WARNING
        await log_service.log_warning(
            message=f"Validation error: {str(e)}",
            module="example",
            function="create_item_endpoint",
            extra_data=str(item)
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Log unexpected errors
        await log_service.log_error(
            message="Unexpected error creating item",
            exception=e,
            module="example",
            function="create_item_endpoint",
            extra_data=str(item)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


# Example 3: Using decorator without re-raising exception
@example_router.post("/risky-operation")
@log_errors(message="Risky operation failed", reraise=False)
async def risky_operation_endpoint(
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates error logging without re-raising.
    The error is logged, but the endpoint returns normally.
    """

    # This will fail but won't raise an exception
    raise RuntimeError("Something went wrong")

    # This code won't be reached due to exception above,
    # but if reraise=False, the endpoint returns None instead of raising


# Example 4: Getting recent errors
@example_router.get("/recent-errors")
async def get_recent_errors_endpoint(
    limit: int = 10,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates retrieving recent error logs.
    """
    log_service = LogService(repo)

    errors = await log_service.get_recent_errors(limit=limit)

    return {
        "count": len(errors),
        "errors": [
            {
                "id": error.id,
                "level": error.level,
                "message": error.message,
                "module": error.module,
                "function": error.function,
                "createdAt": error.createdAt
            }
            for error in errors
        ]
    }


# Example 5: Cleanup old logs
@example_router.delete("/cleanup")
async def cleanup_logs_endpoint(
    days: int = 30,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates cleaning up old logs.
    In production, this would typically be a scheduled task.
    """
    log_service = LogService(repo)

    deleted_count = await log_service.cleanup_old_logs(days=days)

    await log_service.log_info(
        message=f"Cleaned up {deleted_count} logs older than {days} days",
        module="example",
        function="cleanup_logs_endpoint"
    )

    return {
        "deleted": deleted_count,
        "message": f"Deleted logs older than {days} days"
    }


# Example 6: Direct repository usage for custom queries
@example_router.get("/logs-by-module/{module_name}")
async def get_logs_by_module(
    module_name: str,
    limit: int = 50,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates direct repository usage
    for custom log queries.
    """
    logs = await repo.get_logs(
        module=module_name,
        limit=limit
    )

    return {
        "module": module_name,
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "level": log.level,
                "message": log.message,
                "createdAt": log.createdAt
            }
            for log in logs
        ]
    }


# Example 7: Complex filtering
@example_router.get("/logs-advanced-search")
async def advanced_log_search(
    level: LogLevel | None = None,
    user_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: LogRepository = Depends(get_log_repository)
):
    """
    This endpoint demonstrates advanced log filtering.
    """
    logs = await repo.get_logs(
        skip=skip,
        limit=limit,
        level=level,
        user_id=user_id
    )

    total = await repo.count_logs(
        level=level,
        user_id=user_id
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "count": len(logs),
        "logs": [log.to_response() for log in logs]
    }


# To use this example in your main.py:
# from app.modules.logs.example_usage import example_router
# app.include_router(example_router, prefix="/api/v1")

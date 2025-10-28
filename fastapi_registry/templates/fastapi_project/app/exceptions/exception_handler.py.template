"""Global exception handlers for the application."""

import logging
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from app.exceptions.custom_exceptions import AppException


logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request, exc: Union[HTTPException, AppException, Exception]
) -> JSONResponse:
    """
    Global exception handler for HTTP and application exceptions.

    Handles:
    - FastAPI HTTPException
    - Custom AppException
    - Unexpected exceptions

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    # Handle custom app exceptions
    if isinstance(exc, AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "type": exc.__class__.__name__,
            },
        )

    # Handle FastAPI HTTP exceptions
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
            },
        )

    # Handle unexpected exceptions
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for request validation errors.

    Provides detailed validation error messages.

    Args:
        request: FastAPI request object
        exc: RequestValidationError exception

    Returns:
        JSON response with validation errors
    """
    errors = []
    for error in exc.errors():
        error_detail = {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        errors.append(error_detail)

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"errors": errors},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )

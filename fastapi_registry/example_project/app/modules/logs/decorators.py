"""Decorators for automatic error logging.

This module provides decorators that automatically log exceptions
to the database when they occur in decorated functions.
"""

import functools
import inspect
import logging
from typing import Any, Awaitable, Callable, TypeVar, ParamSpec, cast

from fastapi import Request

from .db_models import LogLevel


logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


def log_errors(
    message: str | None = None,
    reraise: bool = True,
    level: LogLevel = LogLevel.ERROR
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to automatically log exceptions to database.

    This decorator catches exceptions in the decorated function and logs them
    to the database using the LogService. It can be used on both sync and async
    functions.

    Args:
        message: Custom error message (optional, uses exception message if None)
        reraise: Whether to re-raise the exception after logging (default: True)
        level: Log level to use (default: ERROR)

    Returns:
        Decorated function

    Example:
        @log_errors(message="Failed to process user data")
        async def process_user(user_id: str):
            # Your code here
            pass

        @log_errors(reraise=False)  # Don't re-raise, just log
        def risky_operation():
            # Your code here
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    return await cast(Awaitable[T], func(*args, **kwargs))
                except Exception as e:
                    # Try to get log service from function arguments or kwargs
                    log_service = _extract_log_service(args, kwargs)

                    # Extract user_id and request_id if available
                    user_id = _extract_user_id(args, kwargs)
                    request_id = _extract_request_id(args, kwargs)

                    error_message = message or f"Error in {func.__name__}: {str(e)}"

                    # Log the error
                    if log_service:
                        try:
                            await log_service.log_error(
                                message=error_message,
                                exception=e,
                                module=func.__module__,
                                function=func.__name__,
                                user_id=user_id,
                                request_id=request_id
                            )
                        except Exception as log_error:
                            # Fallback to standard logging if database logging fails
                            logger.error(
                                f"Failed to log error to database: {log_error}",
                                exc_info=True
                            )
                            logger.error(f"Original error: {error_message}", exc_info=e)
                    else:
                        # Fallback to standard logging if no log service available
                        logger.error(error_message, exc_info=e)

                    if reraise:
                        raise
                    return None  # type: ignore[return-value]  # type: ignore

            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_message = message or f"Error in {func.__name__}: {str(e)}"

                    # For sync functions, we can only use standard logging
                    # as we can't await async database operations
                    logger.error(error_message, exc_info=e)

                    if reraise:
                        raise
                    return None  # type: ignore[return-value]

            return sync_wrapper

    return decorator


def _extract_log_service(args: tuple, kwargs: dict) -> Any:
    """Try to extract LogService from function arguments.

    Looks for:
    - kwargs with 'log_service' key
    - First argument that has a 'log_service' attribute
    """
    # Check kwargs
    if 'log_service' in kwargs:
        return kwargs['log_service']

    # Check args for objects with log_service attribute
    for arg in args:
        if hasattr(arg, 'log_service'):
            return arg.log_service

    return None


def _extract_user_id(args: tuple, kwargs: dict) -> str | None:
    """Try to extract user_id from function arguments.

    Looks for:
    - kwargs with 'user_id' key
    - kwargs with 'current_user' that has 'id' attribute
    - Request object with user state
    """
    if 'user_id' in kwargs:
        return str(kwargs['user_id'])

    if 'current_user' in kwargs:
        user = kwargs['current_user']
        if hasattr(user, 'id'):
            return str(user.id)

    # Check for FastAPI Request object
    for arg in args:
        if isinstance(arg, Request):
            if hasattr(arg.state, 'user') and hasattr(arg.state.user, 'id'):
                return str(arg.state.user.id)

    return None


def _extract_request_id(args: tuple, kwargs: dict) -> str | None:
    """Try to extract request_id from function arguments.

    Looks for:
    - kwargs with 'request_id' key
    - Request object with request_id in state or headers
    """
    if 'request_id' in kwargs:
        return str(kwargs['request_id'])

    # Check for FastAPI Request object
    for arg in args:
        if isinstance(arg, Request):
            # Check state first
            if hasattr(arg.state, 'request_id'):
                return str(arg.state.request_id)
            # Check headers
            if 'x-request-id' in arg.headers:
                return str(arg.headers['x-request-id'])

    return None

"""Custom decorators for authentication, rate limiting, and validation."""

from functools import wraps
from typing import Any, Callable

from fastapi import Depends, HTTPException, status

from ...core.limiter import limiter
from .dependencies import get_current_user
from .models import User


def require_auth(func: Callable) -> Callable:
    """
    Decorator for endpoints requiring authentication.

    Automatically injects authenticated user into 'current_user' parameter.

    Usage:
        @router.get("/me")
        @require_auth
        async def get_me(current_user: User) -> UserResponse:
            return UserResponse.model_validate(current_user)
    """

    @wraps(func)
    async def wrapper(*args: Any, current_user: User = Depends(get_current_user), **kwargs: Any) -> Any:
        return await func(*args, current_user=current_user, **kwargs)

    return wrapper


def rate_limit(limit: str):
    """
    Decorator for rate limiting.

    NOTE: This is just a convenience wrapper around limiter.limit.
    The decorated endpoint MUST include a 'request: Request' parameter.

    Args:
        limit: Rate limit string (e.g., "5/minute", "100/hour")

    Usage:
        @router.post("/login")
        @rate_limit("10/minute")
        async def login(request: Request, credentials: UserLogin) -> LoginResponse:
            # request parameter is required for rate limiting
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Apply limiter.limit directly - it will handle the request parameter
        return limiter.limit(limit)(func)  # type: ignore[no-any-return]

    return decorator


def recaptcha_protected(action: str):
    """
    Decorator for endpoints requiring reCAPTCHA verification.

    Expects the request body to have a 'recaptchaToken' field.

    NOTE: This is an optional security feature. Enable by setting:
    RECAPTCHA_ENABLED=true in your .env file and configuring reCAPTCHA keys.

    Args:
        action: reCAPTCHA action name (should match client-side action)

    Usage:
        @router.post("/register")
        @recaptcha_protected("register")
        async def register(user_data: UserRegister) -> LoginResponse:
            # reCAPTCHA already verified
            ...

    Frontend Integration:
        // Add reCAPTCHA token to your request body:
        const response = await fetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                ...userData,
                recaptchaToken: await grecaptcha.execute(siteKey, {action: 'register'})
            })
        });
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.core.recaptcha import RecaptchaError, verify_recaptcha

            # Find the request data object in args or kwargs
            request_data = None
            for arg in args:
                if hasattr(arg, "recaptchaToken"):
                    request_data = arg
                    break

            if not request_data:
                for kwarg_value in kwargs.values():
                    if hasattr(kwarg_value, "recaptchaToken"):
                        request_data = kwarg_value
                        break

            # Verify reCAPTCHA token
            if request_data and hasattr(request_data, "recaptchaToken"):
                try:
                    await verify_recaptcha(
                        request_data.recaptchaToken or "",
                        action=action
                    )
                except RecaptchaError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"reCAPTCHA verification failed: {str(e)}"
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator

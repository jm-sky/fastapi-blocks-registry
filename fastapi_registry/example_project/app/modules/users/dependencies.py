"""FastAPI dependencies for user management module.

SECURITY WARNING: Mock Authentication
======================================

This module uses MOCK authentication for demonstration purposes.
The get_current_user() function returns the first user in the store,
effectively bypassing all authentication checks!

DO NOT USE IN PRODUCTION WITHOUT PROPER AUTHENTICATION!

Integration Options:
--------------------

Option 1: Integrate with auth module (RECOMMENDED if using both modules)
    1. Import auth module's get_current_user:
       from app.modules.auth.dependencies import get_current_user
    2. Comment out or remove the mock implementation below
    3. Both modules will share the same authentication

Option 2: Implement your own authentication
    1. Extract JWT token from Authorization header
    2. Validate the token using PyJWT
    3. Get user from database by token's user_id
    4. Return the authenticated user

Option 3: Use NotImplementedError (forces explicit implementation)
    Replace mock implementation with:
    raise NotImplementedError(
        "Authentication not configured. See users/dependencies.py for integration options."
    )
"""

import os
from typing import Annotated

from fastapi import Depends, HTTPException, status

from .models import User

# Check if we should allow mock authentication
ALLOW_MOCK_AUTH = os.getenv("ALLOW_MOCK_AUTH", "false").lower() == "true"


async def get_current_user() -> User:
    """
    Get the currently authenticated user.

    SECURITY WARNING: This is a MOCK implementation!

    To use this in development, set environment variable:
        ALLOW_MOCK_AUTH=true

    For production, you MUST implement real authentication.
    See module docstring for integration options.
    """
    if not ALLOW_MOCK_AUTH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Authentication not configured. "
                "To integrate with auth module, import get_current_user from "
                "app.modules.auth.dependencies. "
                "For development testing, set ALLOW_MOCK_AUTH=true environment variable. "
                "See app/modules/users/dependencies.py for details."
            ),
        )

    # MOCK IMPLEMENTATION - DO NOT USE IN PRODUCTION
    # Returns a fake user for testing purposes
    from datetime import UTC, datetime

    return User(
        id="mock-user-id",
        email="mock@example.com",
        name="Mock User",
        role="admin",
        isActive=True,
        createdAt=datetime.now(UTC),
        updatedAt=datetime.now(UTC)
    )


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Require the current user to have admin role.

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]

"""FastAPI dependencies for user management module."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from .exceptions import UnauthorizedError
from .models import User

# NOTE: This is a placeholder dependency for the current user.
# In a real application, this would integrate with the auth module
# to extract and validate the JWT token from the request headers.


async def get_current_user() -> User:
    """
    Get the currently authenticated user.

    NOTE: This is a mock implementation for demonstration purposes.
    In production, this should:
    1. Extract JWT token from Authorization header
    2. Validate the token
    3. Get user from database by token's subject (user_id)
    4. Return the authenticated user

    Example integration with auth module:
    ```python
    from ..auth.dependencies import get_current_user as auth_get_current_user
    from ..auth.models import User as AuthUser

    async def get_current_user(auth_user: Annotated[AuthUser, Depends(auth_get_current_user)]) -> User:
        # Convert auth user to users module user or fetch from user_store
        return user_store.get_user_by_id(auth_user.id)
    ```
    """
    # Mock user for demonstration
    from .models import user_store

    # In production, this would come from JWT token
    mock_user = user_store.get_all_users(limit=1)
    if not mock_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return mock_user[0]


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

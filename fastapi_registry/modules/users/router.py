"""FastAPI router for user management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from .dependencies import AdminUser, CurrentUser
from .exceptions import UserAlreadyExistsError, UserNotFoundError
from .models import user_store
from .schemas import (
    MessageResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

# Create router
router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user (admin only)",
)
async def create_user(user_data: UserCreate, _: AdminUser) -> UserResponse:
    """Create a new user."""
    try:
        user = user_store.create_user(
            email=user_data.email, name=user_data.name, role=user_data.role
        )
        return UserResponse(**user.to_response())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from e


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="Get list of all users with pagination",
)
async def list_users(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    include_inactive: bool = Query(
        default=False, description="Include inactive users"
    ),
    _: AdminUser = None,
) -> UserListResponse:
    """Get list of users."""
    users = user_store.get_all_users(
        skip=skip, limit=limit, include_inactive=include_inactive
    )
    total = user_store.count_users(include_inactive=include_inactive)

    return UserListResponse(
        users=[UserResponse(**u.to_response()) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get currently authenticated user information",
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse(**current_user.to_response())


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get a specific user by their ID",
)
async def get_user(user_id: str, _: AdminUser) -> UserResponse:
    """Get user by ID."""
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return UserResponse(**user.to_response())


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information (admin only)",
)
async def update_user(
    user_id: str, user_data: UserUpdate, _: AdminUser
) -> UserResponse:
    """Update user information."""
    try:
        user = user_store.update_user(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            is_active=user_data.isActive,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return UserResponse(**user.to_response())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from e


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete user (set isActive to false)",
)
async def delete_user(user_id: str, _: AdminUser) -> MessageResponse:
    """Soft delete user."""
    success = user_store.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return MessageResponse(message=f"User {user_id} deactivated successfully")


@router.delete(
    "/{user_id}/hard",
    response_model=MessageResponse,
    summary="Permanently delete user",
    description="Permanently delete user from the system (admin only)",
)
async def hard_delete_user(user_id: str, _: AdminUser) -> MessageResponse:
    """Permanently delete user."""
    success = user_store.hard_delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return MessageResponse(message=f"User {user_id} permanently deleted")

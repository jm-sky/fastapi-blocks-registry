"""FastAPI router for user management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .dependencies import AdminUser, CurrentUser
from .exceptions import UserAlreadyExistsError
from .repositories import UserRepository, get_user_repository
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
async def create_user(
    user_data: UserCreate,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> UserResponse:
    """Create a new user."""
    try:
        user = await repo.create_user(
            email=user_data.email, name=user_data.name, role=user_data.role
        )
        return UserResponse(**user.to_response())
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from e


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="Get list of all users with pagination and search",
)
async def list_users(
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    include_inactive: bool = Query(
        default=False, description="Include inactive users"
    ),
    search: str | None = Query(
        default=None, description="Search in name, email, and role"
    )
) -> UserListResponse:
    """Get list of users with optional search.

    Search is performed across name, email, and role fields.
    Example: ?search=john will find users with 'john' in name, email, or role.
    """
    users = await repo.get_all_users(
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
        search=search
    )
    total = await repo.count_users(
        include_inactive=include_inactive,
        search=search
    )

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
async def get_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> UserResponse:
    """Get user by ID."""
    user = await repo.get_user_by_id(user_id)
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
    user_id: str,
    user_data: UserUpdate,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> UserResponse:
    """Update user information."""
    try:
        user = await repo.update_user(
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
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from e


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete user (set isActive to false)",
)
async def delete_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> MessageResponse:
    """Soft delete user."""
    success = await repo.delete_user(user_id)
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
async def hard_delete_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> MessageResponse:
    """Permanently delete user."""
    success = await repo.hard_delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return MessageResponse(message=f"User {user_id} permanently deleted")

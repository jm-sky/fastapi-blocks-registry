"""Pagination utilities for API endpoints.

This module provides reusable pagination functionality including
request parameters, response models, and helper functions.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters for API endpoints.

    Usage:
        @router.get("/items")
        async def list_items(
            skip: int = Query(default=0, ge=0),
            limit: int = Query(default=100, ge=1, le=1000)
        ):
            # Use skip and limit for database queries
            pass
    """

    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Max records to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model.

    This provides a consistent pagination structure across all endpoints.

    Usage:
        class UserListResponse(PaginatedResponse[UserResponse]):
            pass

        return UserListResponse(
            items=users,
            total=total_count,
            skip=0,
            limit=100
        )
    """

    items: list[T]
    total: int = Field(description="Total number of items available")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items per page")
    hasMore: bool | None = Field(default=None, description="Whether more items are available")

    def __init__(self, **data):
        """Initialize and calculate hasMore if not provided."""
        super().__init__(**data)
        if self.hasMore is None:
            self.hasMore = (self.skip + len(self.items)) < self.total


def paginate_query(query, skip: int = 0, limit: int = 100):
    """Apply pagination to SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        Query with pagination applied

    Usage:
        stmt = select(UserDB).where(UserDB.is_active == True)
        stmt = paginate_query(stmt, skip=0, limit=50)
        result = await session.execute(stmt)
    """
    return query.offset(skip).limit(limit)

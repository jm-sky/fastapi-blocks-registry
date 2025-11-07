"""Pydantic schemas for user management endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """User creation request schema with camelCase."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", pattern="^(user|admin|moderator)$")


class UserUpdate(BaseModel):
    """User update request schema with camelCase."""

    email: EmailStr | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = Field(None, pattern="^(user|admin|moderator)$")
    isActive: bool | None = None


class UserResponse(BaseModel):
    """User response schema with camelCase."""

    id: str
    email: EmailStr
    name: str
    role: str
    isActive: bool
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserListResponse(BaseModel):
    """User list response with pagination metadata."""

    users: list[UserResponse]
    total: int
    skip: int
    limit: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str

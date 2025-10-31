"""Pydantic schemas for authentication endpoints."""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    """
    Validate password meets strength requirements.

    Requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: The password to validate

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise ValueError('Password must contain at least one digit')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError(
            'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'
        )
    return password


class UserLogin(BaseModel):
    """User login request schema with camelCase."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)"
    )


class UserRegister(BaseModel):
    """User registration request schema with camelCase."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character"
    )
    name: str = Field(..., min_length=1, max_length=100)
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)"
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class TokenResponse(BaseModel):
    """Token response schema with camelCase."""

    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int  # seconds


class TokenRefresh(BaseModel):
    """Token refresh request schema."""

    refreshToken: str


class UserResponse(BaseModel):
    """User response schema with camelCase."""

    id: str
    email: EmailStr
    name: str
    isActive: bool
    createdAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class LoginResponse(BaseModel):
    """Login response schema combining token and user info."""

    user: UserResponse
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""

    email: EmailStr
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)"
    )


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""

    token: str = Field(..., min_length=1)
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character"
    )

    @field_validator('newPassword')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Change password request schema for authenticated users."""

    currentPassword: str = Field(..., min_length=1, max_length=100)
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character"
    )

    @field_validator('newPassword')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)

"""Authentication module for FastAPI applications.

This module provides JWT-based authentication with:
- User registration and login
- Password reset functionality
- Token refresh
- Password change for authenticated users
"""

from fastapi import APIRouter

from .router import router

__all__ = ["router"]

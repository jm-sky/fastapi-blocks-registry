"""Middleware configuration for the application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings


def setup_middleware(app: FastAPI) -> None:
    """
    Configure middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=settings.server.cors_credentials,
        allow_methods=settings.server.cors_methods,
        allow_headers=settings.server.cors_headers,
    )

    # Trusted Host Middleware (for production)
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure this in production
        )

    # Add custom middleware here
    # Example: Request logging, rate limiting, etc.

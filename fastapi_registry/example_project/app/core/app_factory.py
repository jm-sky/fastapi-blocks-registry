"""Application factory for creating FastAPI app instances."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting application", extra={"environment": settings.environment})

    # Add your startup logic here
    # Example: Initialize database connection, cache, etc.

    yield

    # Shutdown
    logger.info("Shutting down application")
    # Add your shutdown logic here
    # Example: Close database connections, etc.


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application instance.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development() else None,
        redoc_url="/api/redoc" if settings.is_development() else None,
        openapi_url="/api/openapi.json" if settings.is_development() else None,
    )

    # Setup middleware
    setup_middleware(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Register routers
    register_routers(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors."""
        import logging

        logger = logging.getLogger(__name__)
        logger.exception("Unhandled exception occurred")

        if settings.is_development():
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
        )


def register_routers(app: FastAPI) -> None:
    """
    Register API routers.

    Args:
        app: FastAPI application instance
    """
    # Import and register module routers here
    # Example:
    # from app.modules.auth.router import router as auth_router
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": settings.version,
        }

    @app.get("/", tags=["System"])
    async def root() -> dict:
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.version,
            "docs": "/api/docs" if settings.is_development() else None,
        }

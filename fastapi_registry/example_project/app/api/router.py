"""Main API router aggregating all module routers."""

from fastapi import APIRouter

# Module routers registration
# When you add modules using 'fastapi-registry add <module>', the CLI will automatically
# add the necessary imports and include_router calls here.
from app.modules.auth.router import router as auth_router
from app.modules.logs.router import router as logs_router
from app.modules.users.router import router as users_router

# Main API router
api_router = APIRouter()


# Health check endpoint
@api_router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status message
    """
    return {"status": "healthy"}


# Register module routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(logs_router, prefix="/logs", tags=["Logs", "Monitoring"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])

# Register Two-Factor module (optional, added during development)
try:
    from app.modules.two_factor.router import router as two_factor_router

    api_router.include_router(two_factor_router, prefix="/two-factor", tags=["Two-Factor Authentication", "Security", "WebAuthn", "TOTP"])
except ImportError:
    # Module may be absent in some builds; ignore if not present
    pass

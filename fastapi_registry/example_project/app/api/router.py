"""Main API router aggregating all module routers."""

from fastapi import APIRouter

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


# Module routers registration
# When you add modules using 'fastapi-registry add <module>', the CLI will automatically
# add the necessary imports and include_router calls here.
#
# You can also manually register module routers:
# from app.modules.auth.router import router as auth_router
# api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Register Two-Factor module (added during development)
try:
    from app.modules.two_factor.router import router as two_factor_router

    api_router.include_router(two_factor_router)
except Exception:
    # Module may be absent in some builds; ignore if not present
    pass

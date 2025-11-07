# Router Duplicates Issue

## Problem
The `backend/app/api/router.py` file contains duplicate router registrations, causing potential conflicts and confusion.

## Details
- Lines 29-31: First set of router registrations
- Lines 43-49: Duplicate router registrations
- Line 49: Uses `two_factor_router` outside of try-except block, which can cause `NameError` if the import fails

## Impact
- Duplicate route registrations
- Potential `NameError` if two_factor module import fails
- Code confusion and maintenance issues

## Fix Applied
Removed duplicate router registrations and fixed the try-except block to only catch `ImportError`:

```python
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
```

## Recommendation
The CLI should ensure that router registrations are not duplicated when adding modules. Consider adding a check or using a set to track registered routers.


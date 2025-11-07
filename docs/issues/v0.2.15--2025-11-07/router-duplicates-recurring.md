# Router Duplicates Issue - Recurring Problem

## Problem
The `backend/app/api/router.py` file continues to have duplicate router registrations in new CLI versions. This is a **recurring issue** that appears in multiple CLI versions.

## Versions Affected
- v0.2.14 - Fixed manually
- v0.2.15 - **Reappeared** - Fixed manually again

## Details
The CLI continues to generate duplicate router registrations:
- Duplicate `two_factor_router` registrations within the same try-except block
- Duplicate registrations of `auth_router`, `logs_router`, and `users_router` after the try-except block
- This causes potential route conflicts and code confusion

## Example of Generated Code (Incorrect)
```python
# Register Two-Factor module (optional, added during development)
try:
    from app.modules.two_factor.router import router as two_factor_router

    api_router.include_router(two_factor_router, prefix="/two-factor", tags=["Two-Factor Authentication", "Security", "WebAuthn", "TOTP"])
    api_router.include_router(two_factor_router, prefix="/two-factor", tags=['Two-Factor Authentication', 'Security', 'WebAuthn', 'TOTP'])  # DUPLICATE
except ImportError:
    pass

api_router.include_router(auth_router, prefix="/auth", tags=['Authentication'])  # DUPLICATE
api_router.include_router(logs_router, prefix="/logs", tags=['Logs', 'Monitoring'])  # DUPLICATE
api_router.include_router(users_router, prefix="/users", tags=['Users'])  # DUPLICATE
```

## Correct Code
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

## Impact
- Duplicate route registrations (may cause conflicts)
- Code confusion and maintenance issues
- Requires manual fixes after each CLI update

## Recommendation
The CLI should:
1. **Check for existing router registrations** before adding new ones
2. **Use a set or dictionary** to track registered routers
3. **Avoid duplicate registrations** when updating the router file
4. **Test router generation** to ensure no duplicates are created

This is a **critical issue** that should be fixed in the CLI source code to prevent recurring manual fixes.


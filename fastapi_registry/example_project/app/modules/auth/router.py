"""FastAPI router for authentication endpoints.

This module provides authentication endpoints with security features:
- Rate limiting (ENABLED by default - essential security)
- reCAPTCHA protection (decorators present, DISABLED by default)

To enable reCAPTCHA (optional but recommended):
1. Set RECAPTCHA_ENABLED=true in .env
2. Configure RECAPTCHA_SECRET_KEY and RECAPTCHA_SITE_KEY
3. Decorators are already applied - they become active when enabled

To disable rate limiting (NOT recommended):
- Comment out @rate_limit decorators
- Set RATE_LIMIT_ENABLED=false in .env
"""

from fastapi import APIRouter, HTTPException, Request, status

from .decorators import rate_limit, recaptcha_protected
from .dependencies import AuthServiceDep, CurrentUser
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from .schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
    TokenRefresh,
    UserLogin,
    UserRegister,
    UserResponse,
)

# Create router
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password",
    tags=["Authentication"]
)
@rate_limit("5/minute")  # Prevent registration abuse
@recaptcha_protected("register")  # Disabled by default, enable via RECAPTCHA_ENABLED=true
async def register(user_data: UserRegister, auth_service: AuthServiceDep, request: Request) -> UserResponse:
    """
    Register a new user.

    Security features:
    - ✅ Rate limiting: 5 requests/minute (enabled)
    - ⚪ reCAPTCHA: Disabled by default (enable via RECAPTCHA_ENABLED=true)
    - 💡 Recommendation: Add email verification in production
    """
    try:
        user = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name
        )
        return UserResponse(**user.to_response())
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login user",
    description="Authenticate user and return JWT tokens",
    tags=["Authentication"]
)
@rate_limit("10/minute")  # CRITICAL: Prevent brute force attacks
@recaptcha_protected("login")  # Disabled by default, enable via RECAPTCHA_ENABLED=true
async def login(
    credentials: UserLogin,
    auth_service: AuthServiceDep,
    request: Request
) -> LoginResponse:
    """
    Login user and return tokens.

    Security features:
    - ✅ Rate limiting: 10 requests/minute (enabled - CRITICAL)
    - ⚪ reCAPTCHA: Disabled by default (enable via RECAPTCHA_ENABLED=true)
    - 💡 Recommendation: Implement account lockout after N failed attempts
    """
    try:
        return await auth_service.login_user(
            email=credentials.email,
            password=credentials.password
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh access token",
    description="Get new access token using refresh token",
    tags=["Authentication"]
)
@rate_limit("20/minute")  # Prevent token refresh abuse
async def refresh_token(
    token_data: TokenRefresh,
    auth_service: AuthServiceDep,
    request: Request
) -> dict:
    """
    Refresh access token.

    Security features:
    - ✅ Rate limiting: 20 requests/minute (enabled)
    - 💡 Recommendation: Consider implementing refresh token rotation
    """
    try:
        return await auth_service.refresh_access_token(token_data.refreshToken)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Request a password reset email (development: token is printed to console)",
    tags=["Authentication"]
)
@rate_limit("3/minute")  # CRITICAL: Prevent email enumeration and spam
@recaptcha_protected("forgot_password")  # Disabled by default, enable via RECAPTCHA_ENABLED=true
async def forgot_password(
    request_data: ForgotPasswordRequest,
    auth_service: AuthServiceDep,
    request: Request
) -> MessageResponse:
    """
    Request password reset.

    Security features:
    - ✅ Rate limiting: 3 requests/minute (enabled - CRITICAL)
    - ⚪ reCAPTCHA: Disabled by default, RECOMMENDED (enable via RECAPTCHA_ENABLED=true)
    - ✅ Generic response message (prevents email enumeration)
    """
    # Always return success message to prevent email enumeration
    await auth_service.request_password_reset(request_data.email)
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password using reset token",
    tags=["Authentication"]
)
@rate_limit("5/minute")  # Prevent token brute force
async def reset_password(
    request_data: ResetPasswordRequest,
    auth_service: AuthServiceDep,
    request: Request
) -> MessageResponse:
    """
    Reset password with token.

    Security features:
    - ✅ Rate limiting: 5 requests/minute (enabled)
    - ✅ Token is single-use and short-lived (1 hour)
    """
    try:
        await auth_service.reset_password(request_data.token, request_data.newPassword)
        return MessageResponse(message="Password has been reset successfully")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change password for authenticated user",
    tags=["Authentication"]
)
@rate_limit("3/minute")  # Prevent password change abuse
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    request: Request
) -> MessageResponse:
    """
    Change password for authenticated user.

    Security features:
    - ✅ Rate limiting: 3 requests/minute (enabled)
    - ✅ Authentication required (JWT token)
    - ✅ Current password verification required
    """
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            current_password=request_data.currentPassword,
            new_password=request_data.newPassword
        )
        return MessageResponse(message="Password changed successfully")
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get currently authenticated user information",
    tags=["Authentication"]
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """
    Get current user information.

    Security features:
    - ✅ Authentication required (JWT token via CurrentUser)
    - ⚪ Rate limiting: Not needed (read-only, already auth-protected)
    """
    return UserResponse(**current_user.to_response())

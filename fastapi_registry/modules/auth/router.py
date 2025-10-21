"""FastAPI router for authentication endpoints."""

from fastapi import APIRouter, HTTPException, status

from .dependencies import CurrentUser
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError
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
    UserResponse
)
from .service import AuthService

# Create router
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password"
)
async def register(user_data: UserRegister) -> UserResponse:
    """Register a new user."""
    try:
        user = AuthService.register_user(
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
    description="Authenticate user and return JWT tokens"
)
async def login(credentials: UserLogin) -> LoginResponse:
    """Login user and return tokens."""
    try:
        return AuthService.login_user(
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
    description="Get new access token using refresh token"
)
async def refresh_token(token_data: TokenRefresh) -> dict:
    """Refresh access token."""
    try:
        return AuthService.refresh_access_token(token_data.refreshToken)
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
    description="Request a password reset email (development: token is printed to console)"
)
async def forgot_password(request: ForgotPasswordRequest) -> MessageResponse:
    """Request password reset."""
    # Always return success message to prevent email enumeration
    AuthService.request_password_reset(request.email)
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password using reset token"
)
async def reset_password(request: ResetPasswordRequest) -> MessageResponse:
    """Reset password with token."""
    try:
        AuthService.reset_password(request.token, request.newPassword)
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
    description="Change password for authenticated user"
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser
) -> MessageResponse:
    """Change password for authenticated user."""
    try:
        AuthService.change_password(
            user_id=current_user.id,
            current_password=request.currentPassword,
            new_password=request.newPassword
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
    description="Get currently authenticated user information"
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse(**current_user.to_response())

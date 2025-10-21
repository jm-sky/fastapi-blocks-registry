"""Authentication service layer for business logic."""

from .auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRES_MINUTES
)
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError
)
from .models import User, user_store
from .schemas import LoginResponse, UserResponse


class AuthService:
    """Service class for authentication operations."""

    @staticmethod
    def register_user(email: str, password: str, name: str) -> User:
        """
        Register a new user.

        Args:
            email: User email
            password: Plain text password
            name: User full name

        Returns:
            Created user

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        try:
            user = user_store.create_user(email, password, name)
            return user
        except UserAlreadyExistsError:
            raise

    @staticmethod
    def login_user(email: str, password: str) -> LoginResponse:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Login response with tokens and user info

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Get user by email
        user = user_store.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password
        if not user.verify_password(password):
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Generate tokens
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=ACCESS_TOKEN_EXPIRES_MINUTES * 60  # Convert to seconds
        )

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        try:
            payload = verify_token(refresh_token)

            # Verify token type
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")

            # Get user ID
            user_id = payload.get("sub")
            if not user_id:
                raise InvalidTokenError("Invalid token payload")

            # Verify user exists
            user = user_store.get_user_by_id(user_id)
            if not user or not user.isActive:
                raise InvalidTokenError("User not found or inactive")

            # Generate new tokens
            new_access_token = create_access_token(data={"sub": user_id})
            new_refresh_token = create_refresh_token(data={"sub": user_id})

            return {
                "accessToken": new_access_token,
                "refreshToken": new_refresh_token,
                "tokenType": "bearer",
                "expiresIn": ACCESS_TOKEN_EXPIRES_MINUTES * 60
            }

        except Exception:
            raise InvalidTokenError("Invalid or expired refresh token")

    @staticmethod
    def request_password_reset(email: str) -> bool:
        """
        Generate password reset token for user.

        Args:
            email: User email

        Returns:
            True if token generated successfully, False if user not found

        Note:
            In production, this should send an email with the reset link.
            For development, the token can be logged or returned.
        """
        token = user_store.generate_reset_token(email)
        if token:
            # TODO: Send email with reset link containing the token
            # For now, just log it (remove in production!)
            print(f"Password reset token for {email}: {token}")
            return True
        return False

    @staticmethod
    def reset_password(token: str, new_password: str) -> bool:
        """
        Reset password using reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            True if password reset successfully

        Raises:
            InvalidTokenError: If token is invalid
        """
        success = user_store.reset_password_with_token(token, new_password)
        if not success:
            raise InvalidTokenError("Invalid or expired reset token")
        return True

    @staticmethod
    def change_password(
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            InvalidCredentialsError: If current password is incorrect
            UserNotFoundError: If user not found
        """
        success = user_store.change_password(user_id, current_password, new_password)
        if not success:
            user = user_store.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundError("User not found")
            raise InvalidCredentialsError("Current password is incorrect")
        return True

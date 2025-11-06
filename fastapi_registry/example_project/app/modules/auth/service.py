"""Authentication service layer for business logic."""

import logging
import os

from ...core.config import settings
from ...core.email import get_email_service
from .auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from .models import User
from .schemas import LoginResponse, UserResponse
from .types.repository import UserRepositoryInterface

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations."""
    user_repository: UserRepositoryInterface

    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository


    async def register_user(self, email: str, password: str, name: str) -> User:
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
            user = await self.user_repository.create_user(email, password, name)
            
            # Send welcome email
            try:
                email_service = get_email_service()
                await email_service.send_welcome_email(to=email, name=name)
            except Exception as e:
                # Log error but don't fail registration if email fails
                logger.warning(f"Failed to send welcome email: {e}")
            
            return user
        except UserAlreadyExistsError:
            raise


    async def login_user(self, email: str, password: str) -> LoginResponse:
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
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password
        if not user.verify_password(password):
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "tfaVerified": False,
                "tfaMethod": None,
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user.id,
                "email": user.email,
                "tfaVerified": False,
                "tfaMethod": None,
            }
        )

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60  # Convert to seconds
        )


    async def refresh_access_token(self, refresh_token: str) -> dict[str, str | int]:
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
            user = await self.user_repository.get_user_by_id(user_id)
            if not user or not user.isActive:
                raise InvalidTokenError("User not found or inactive")

            # Preserve 2FA state from refresh token
            old_tfa_verified = payload.get("tfaVerified", False)
            old_tfa_method = payload.get("tfaMethod")

            # Generate new tokens with preserved 2FA state
            new_access_token = create_access_token(
                data={
                    "sub": user_id,
                    "email": user.email,
                    "tfaVerified": old_tfa_verified,
                    "tfaMethod": old_tfa_method,
                    # tid/trol NOT preserved (security)
                }
            )
            new_refresh_token = create_refresh_token(
                data={
                    "sub": user_id,
                    "email": user.email,
                    "tfaVerified": old_tfa_verified,
                    "tfaMethod": old_tfa_method,
                }
            )

            return {
                "accessToken": new_access_token,
                "refreshToken": new_refresh_token,
                "tokenType": "bearer",
                "expiresIn": settings.security.access_token_expires_minutes * 60
            }

        except InvalidTokenError:
            # Re-raise known errors
            raise
        except Exception as e:
            # Log unexpected errors for debugging
            logger.error(f"Unexpected error during token refresh: {e}", exc_info=True)
            raise InvalidTokenError("Invalid or expired refresh token")


    async def request_password_reset(self, email: str) -> bool:
        """
        Generate password reset token for user.

        Args:
            email: User email

        Returns:
            True if token generated successfully, False if user not found

        Note:
            Sends email with reset link. In development mode, also logs token.
        """
        # Get user to get name for email
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            # Return True to prevent email enumeration
            return True
        
        token = await self.user_repository.generate_reset_token(email)
        if token:
            # Send email with reset link
            try:
                email_service = get_email_service()
                await email_service.send_password_reset_email(
                    to=email,
                    name=user.name,
                    reset_token=token
                )
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")
            
            # In development mode only, also log the token (NEVER in production!)
            environment = os.getenv("ENVIRONMENT", "production").lower()
            if environment == "development":
                logger.warning(
                    f"DEV MODE: Password reset token for {email}: {token}\n"
                    f"Reset link: /reset-password?token={token}"
                )
            else:
                # In production, just log that email was sent without exposing token
                logger.info(f"Password reset email sent to {email}")
            return True
        return False


    async def reset_password(self, token: str, new_password: str) -> bool:
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
        success = await self.user_repository.reset_password_with_token(token, new_password)
        if not success:
            raise InvalidTokenError("Invalid or expired reset token")
        return True


    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str | None = None
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            ip_address: IP address where change occurred (optional)

        Returns:
            True if password changed successfully

        Raises:
            InvalidCredentialsError: If current password is incorrect
            UserNotFoundError: If user not found
        """
        success = await self.user_repository.change_password(user_id, current_password, new_password)
        if not success:
            user = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundError("User not found")
            raise InvalidCredentialsError("Current password is incorrect")
        
        # Send password changed notification email
        try:
            email_service = get_email_service()
            await email_service.send_password_changed_email(
                to=user.email,
                name=user.name,
                ip_address=ip_address
            )
        except Exception as e:
            # Log error but don't fail password change if email fails
            logger.warning(f"Failed to send password changed email: {e}")
        
        return True

    async def delete_account(
        self,
        user_id: str,
        password: str | None = None,
        confirmation: str = "",
        soft_delete: bool = True
    ) -> bool:
        """
        Delete user account.

        Args:
            user_id: User ID to delete
            password: Current password for verification (optional but recommended)
            confirmation: Confirmation phrase (e.g., 'DELETE' or user email)
            soft_delete: If True, performs soft delete (default). If False, hard delete.

        Returns:
            True if account deleted successfully

        Raises:
            InvalidCredentialsError: If password is provided but incorrect
            UserNotFoundError: If user not found
        """
        # Get user to verify existence and for password verification
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("User not found")

        # Verify password if provided
        if password:
            if not user.verify_password(password):
                raise InvalidCredentialsError("Password is incorrect")

        # Verify confirmation phrase (should be 'DELETE' or user email)
        if confirmation.upper() != "DELETE" and confirmation.lower() != user.email.lower():
            raise InvalidCredentialsError("Confirmation phrase is incorrect")

        # Store user email and name before deletion for email notification
        user_email = user.email
        user_name = user.name

        # Delete user account
        success = await self.user_repository.delete_user(user_id, soft_delete=soft_delete)
        if not success:
            raise UserNotFoundError("Failed to delete user account")

        # Send account deletion confirmation email (before account is deleted)
        try:
            email_service = get_email_service()
            await email_service.send_account_deleted_email(
                to=user_email,
                name=user_name
            )
        except Exception as e:
            # Log error but don't fail deletion if email fails
            logger.warning(f"Failed to send account deletion email: {e}")

        # TODO: Invalidate all user sessions/tokens
        # TODO: Delete related data (2FA, passkeys, etc.)

        return True

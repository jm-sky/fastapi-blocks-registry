"""Custom exception classes for the application."""

from fastapi import status


class AppException(Exception):
    """
    Base exception for application-specific errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """
        Initialize application exception.

        Args:
            message: Error message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class BadRequestError(AppException):
    """Raised when request data is invalid (400)."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class UnauthorizedError(AppException):
    """Raised when authentication is required or failed (401)."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    """Raised when user doesn't have permission (403)."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Raised when there's a conflict with existing data (409)."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status.HTTP_409_CONFLICT)


# Module-specific exceptions can inherit from base exceptions
# Example:
# class UserNotFoundError(NotFoundError):
#     """Raised when a user is not found."""
#
#     def __init__(self, user_id: str):
#         super().__init__(f"User with ID {user_id} not found")

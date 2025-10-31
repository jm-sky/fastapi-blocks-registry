"""Custom exceptions for logs module.

This module defines custom exceptions specific to log operations.
"""


class LogError(Exception):
    """Base exception for log-related errors."""
    pass


class LogNotFoundError(LogError):
    """Exception raised when a log entry is not found."""

    def __init__(self, log_id: str):
        self.log_id = log_id
        super().__init__(f"Log with id {log_id} not found")


class LogCreationError(LogError):
    """Exception raised when log creation fails."""

    def __init__(self, message: str = "Failed to create log entry"):
        super().__init__(message)


class LogDeletionError(LogError):
    """Exception raised when log deletion fails."""

    def __init__(self, message: str = "Failed to delete log entries"):
        super().__init__(message)

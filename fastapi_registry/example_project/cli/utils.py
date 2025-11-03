"""Utility functions for CLI commands.

This module contains validators, formatters, and other helper functions
used across different CLI commands.
"""

import re


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Password requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if password meets all requirements
            - error_message: Empty string if valid, error description otherwise

    Example:
        >>> validate_password_strength("SecurePass123")
        (True, "")
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, ""


def format_user_role(is_admin: bool) -> str:
    """Format user role for display with color.

    Args:
        is_admin: Whether user is admin

    Returns:
        str: Formatted role string with Rich markup
    """
    return "[yellow]Admin[/yellow]" if is_admin else "[dim]User[/dim]"


def format_user_status(is_active: bool) -> str:
    """Format user status for display with color.

    Args:
        is_active: Whether user is active

    Returns:
        str: Formatted status string with Rich markup
    """
    return "[green]Active[/green]" if is_active else "[red]Inactive[/red]"


def truncate_id(user_id: str, length: int = 8) -> str:
    """Truncate user ID for display.

    Args:
        user_id: Full user ID (ULID or UUID)
        length: Number of characters to show before ellipsis

    Returns:
        str: Truncated ID with ellipsis
    """
    return user_id[:length] + "..." if len(user_id) > length else user_id

"""Email service with adapter pattern for sending emails.

This module provides email functionality with two adapters:
- FileEmailAdapter: Saves emails to files (development/testing)
- SMTPEmailAdapter: Sends emails via SMTP (production)

Usage:
    from app.core.email import get_email_service

    email_service = get_email_service()
    await email_service.send_welcome_email("user@example.com", "John Doe")
"""

from .service import EmailService, get_email_service
from .adapter import EmailAdapter

__all__ = ["EmailService", "EmailAdapter", "get_email_service"]

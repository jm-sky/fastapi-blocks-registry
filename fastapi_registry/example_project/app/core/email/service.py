"""Email service for sending various types of emails."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

if TYPE_CHECKING:
    from .adapter import EmailAdapter

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending templated emails."""

    def __init__(self, adapter: "EmailAdapter"):
        """Initialize email service with adapter.

        Args:
            adapter: Email adapter (FileEmailAdapter or SMTPEmailAdapter)
        """
        self.adapter = adapter
        self.templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"])
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict,
        from_email: str | None = None
    ) -> bool:
        """Send email using template.

        Args:
            to: Recipient email address
            subject: Email subject
            template_name: Name of template file (without .html extension)
            context: Template context variables
            from_email: Sender email address (optional)

        Returns:
            True if email sent successfully
        """
        try:
            # Load and render template
            template = self.jinja_env.get_template(f"{template_name}.html")
            html_body = template.render(**context)

            # Generate text version (simple strip of HTML tags)
            text_body = self._html_to_text(html_body)

            # Send via adapter
            return await self.adapter.send_email(
                to=to,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                from_email=from_email
            )

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple implementation).

        Args:
            html: HTML string

        Returns:
            Plain text version
        """
        # Simple HTML to text conversion
        import re
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def send_welcome_email(self, to: str, name: str) -> bool:
        """Send welcome email to new user.

        Args:
            to: Recipient email address
            name: User name

        Returns:
            True if email sent successfully
        """
        return await self.send_email(
            to=to,
            subject="Welcome to our platform!",
            template_name="welcome",
            context={
                "name": name,
                "email": to,
                "frontend_url": settings.frontend_url
            }
        )

    async def send_password_reset_email(self, to: str, name: str, reset_token: str) -> bool:
        """Send password reset email.

        Args:
            to: Recipient email address
            name: User name
            reset_token: Password reset token

        Returns:
            True if email sent successfully
        """
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        return await self.send_email(
            to=to,
            subject="Password Reset Request",
            template_name="password_reset",
            context={
                "name": name,
                "email": to,
                "reset_link": reset_link,
                "token": reset_token,
                "expires_hours": settings.security.password_reset_token_expires_hours,
                "frontend_url": settings.frontend_url
            }
        )

    async def send_password_changed_email(self, to: str, name: str, ip_address: str | None = None) -> bool:
        """Send password changed notification email.

        Args:
            to: Recipient email address
            name: User name
            ip_address: IP address where change occurred (optional)

        Returns:
            True if email sent successfully
        """
        return await self.send_email(
            to=to,
            subject="Password Changed",
            template_name="password_changed",
            context={
                "name": name,
                "email": to,
                "ip_address": ip_address or "Unknown",
                "frontend_url": settings.frontend_url
            }
        )

    async def send_account_deleted_email(self, to: str, name: str) -> bool:
        """Send account deletion confirmation email.

        Args:
            to: Recipient email address
            name: User name

        Returns:
            True if email sent successfully
        """
        return await self.send_email(
            to=to,
            subject="Account Deleted",
            template_name="account_deleted",
            context={
                "name": name,
                "email": to,
                "frontend_url": settings.frontend_url
            }
        )


def get_email_service() -> EmailService:
    """Get email service instance with configured adapter.

    Returns:
        EmailService instance
    """
    from .file_adapter import FileEmailAdapter
    from .smtp_adapter import SMTPEmailAdapter

    # Get email settings from config
    email_settings = getattr(settings, "email", None)

    if not email_settings or not email_settings.enabled:
        # Email disabled, use file adapter as fallback
        logger.warning("Email service is disabled, using file adapter")
        adapter = FileEmailAdapter(file_path="./emails")
        return EmailService(adapter)

    # Choose adapter based on configuration
    if email_settings.adapter == "smtp":
        adapter = SMTPEmailAdapter(
            host=email_settings.smtp_host,
            port=email_settings.smtp_port,
            user=email_settings.smtp_user,
            password=email_settings.smtp_password,
            from_email=email_settings.smtp_from,
            use_tls=email_settings.smtp_use_tls
        )
    else:
        # Default to file adapter
        adapter = FileEmailAdapter(file_path=email_settings.file_path)

    return EmailService(adapter)


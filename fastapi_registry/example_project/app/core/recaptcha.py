"""Google reCAPTCHA v3 verification service.

This module provides reCAPTCHA verification for protecting sensitive endpoints
from bots and automated attacks. It's an optional security feature that can be
enabled via configuration.

Usage:
    from app.core.recaptcha import verify_recaptcha

    # In your endpoint:
    await verify_recaptcha(token, action="login")
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RecaptchaError(Exception):
    """Exception raised for reCAPTCHA verification errors."""
    pass


async def verify_recaptcha(token: str, action: str = "submit") -> dict[str, Any]:
    """
    Verify reCAPTCHA token with Google's API.

    Args:
        token: The reCAPTCHA token from the client
        action: The expected action name (should match client-side action)

    Returns:
        Dict containing verification results with keys:
        - success: bool
        - score: float (0.0-1.0)
        - action: str
        - challenge_ts: str
        - hostname: str

    Raises:
        RecaptchaError: If verification fails or score is too low

    Example:
        try:
            result = await verify_recaptcha(token, action="register")
            logger.info(f"reCAPTCHA score: {result['score']}")
        except RecaptchaError as e:
            logger.warning(f"reCAPTCHA failed: {e}")
            raise HTTPException(status_code=400, detail="Bot detected")
    """
    # Skip verification if reCAPTCHA is disabled (for development/testing)
    if not settings.recaptcha.enabled:
        logger.debug("reCAPTCHA verification skipped (disabled in settings)")
        return {
            "success": True,
            "score": 1.0,
            "action": action,
            "skipped": True
        }

    if not token:
        raise RecaptchaError("reCAPTCHA token is required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.recaptcha.verify_url,
                data={
                    "secret": settings.recaptcha.secret_key,
                    "response": token,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

        # Log the result for debugging
        logger.info(
            f"reCAPTCHA verification: success={result.get('success')}, "
            f"score={result.get('score')}, action={result.get('action')}"
        )

        # Check if verification was successful
        if not result.get("success"):
            error_codes = result.get("error-codes", [])
            logger.warning(f"reCAPTCHA verification failed: {error_codes}")
            raise RecaptchaError(f"reCAPTCHA verification failed: {error_codes}")

        # Verify action matches (prevents token reuse across different forms)
        if result.get("action") != action:
            logger.warning(
                f"reCAPTCHA action mismatch: expected '{action}', "
                f"got '{result.get('action')}'"
            )
            raise RecaptchaError("reCAPTCHA action mismatch")

        # Check score threshold
        score = result.get("score", 0.0)
        if score < settings.recaptcha.min_score:
            logger.warning(
                f"reCAPTCHA score too low: {score} < {settings.recaptcha.min_score}"
            )
            raise RecaptchaError(
                f"reCAPTCHA verification failed: score too low ({score})"
            )

        return result  # type: ignore[no-any-return]

    except httpx.HTTPError as e:
        logger.error(f"reCAPTCHA HTTP error: {e}")
        raise RecaptchaError(f"reCAPTCHA service error: {e}")
    except RecaptchaError:
        # Re-raise RecaptchaError as is
        raise
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {e}")
        raise RecaptchaError(f"reCAPTCHA verification error: {e}")

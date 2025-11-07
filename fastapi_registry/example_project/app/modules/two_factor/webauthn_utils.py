"""WebAuthn utilities for passkey registration and authentication."""

from __future__ import annotations

from typing import Any

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    options_to_json,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    parse_registration_credential_json,
)
from app.core.config import settings


def _get_rp_id() -> str:
    """Get WebAuthn Relying Party ID from settings."""
    return getattr(getattr(settings, "two_factor", object()), "webauthn_rp_id", "localhost")


def _get_rp_name() -> str:
    """Get WebAuthn Relying Party name from settings."""
    return getattr(getattr(settings, "two_factor", object()), "webauthn_rp_name", "FastAPI App")


def _get_timeout() -> int:
    """Get WebAuthn timeout from settings."""
    return getattr(getattr(settings, "two_factor", object()), "webauthn_timeout", 60000)


def create_registration_options(user_id: str, user_email: str, user_name: str) -> tuple[dict[str, Any], str]:
    """
    Create WebAuthn registration options.

    Args:
        user_id: User ID (will be encoded as bytes)
        user_email: User email (used as user name)
        user_name: User display name

    Returns:
        (options_json, challenge) - options for frontend, challenge to store
    """
    options = generate_registration_options(
        rp_id=_get_rp_id(),
        rp_name=_get_rp_name(),
        user_id=user_id.encode(),
        user_name=user_email,
        user_display_name=user_name,
        timeout=_get_timeout(),
    )

    return options_to_json(options), bytes_to_base64url(options.challenge)


def verify_registration(
    credential_json: dict[str, Any],
    expected_challenge: str,
    expected_origin: str,
    expected_rp_id: str | None = None,
) -> dict[str, Any]:
    """
    Verify WebAuthn registration response.

    Args:
        credential_json: Credential JSON from frontend (navigator.credentials.create result)
        expected_challenge: Challenge that was sent to frontend
        expected_origin: Expected origin (e.g., "https://example.com")
        expected_rp_id: Expected Relying Party ID (uses settings if None)

    Returns:
        Verified credential data:
        - credential_id: Base64url-encoded credential ID
        - public_key: Base64url-encoded public key
        - counter: Initial signature counter
        - aaguid: Authenticator AAGUID
        - transports: List of transport types
        - backup_eligible: Backup eligible flag
        - backup_state: Backup state flag

    Raises:
        Exception: If verification fails
    """
    credential = parse_registration_credential_json(credential_json)

    rp_id = expected_rp_id or _get_rp_id()

    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_origin=expected_origin,
        expected_rp_id=rp_id,
    )

    # Extract transports if available
    transports = []
    if hasattr(credential.response, "transports") and credential.response.transports:
        transports = [t.value for t in credential.response.transports]

    return {
        "credential_id": bytes_to_base64url(verification.credential_id),
        "public_key": bytes_to_base64url(verification.credential_public_key),
        "counter": verification.sign_count,
        "aaguid": str(verification.aaguid),
        "transports": transports,
        "backup_eligible": verification.credential_backup_eligible,
        "backup_state": verification.credential_backed_up,
    }

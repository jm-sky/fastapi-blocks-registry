"""Two-Factor (TOTP) service layer for setup and verification (Phase 1)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings

from .crypto_utils import decrypt_secret, encrypt_secret, generate_backup_codes, verify_backup_code
from .exceptions import InvalidTwoFactorCodeError, SetupTokenError
from .totp_utils import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_with_window,
)
from .types.jwt import PasskeyRegistrationTokenPayload, TotpSetupTokenPayload
from .types.repository import TwoFactorRepositoryInterface


def _create_setup_token(data: dict[str, Any]) -> str:
    """Create a short-lived JWT used during TOTP setup verification."""

    expires = datetime.now(UTC) + timedelta(minutes=10)
    # Determine token type from data
    token_type = data.get("type", "2fa_setup")

    if token_type == "passkey_registration":
        payload: PasskeyRegistrationTokenPayload = {
            "sub": data["sub"],
            "challenge": data["challenge"],
            "type": "passkey_registration",
            "exp": int(expires.timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
        }
    else:
        # TOTP setup token
        payload: TotpSetupTokenPayload = {
            "sub": data["sub"],
            "secret": data["secret"],
            "backup_codes_hashed": data["backup_codes_hashed"],
            "type": "2fa_setup",
            "exp": int(expires.timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
        }

    return jwt.encode(payload, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)


def _verify_setup_token(token: str) -> TotpSetupTokenPayload | PasskeyRegistrationTokenPayload:
    try:
        payload = jwt.decode(token, settings.security.secret_key, algorithms=[settings.security.jwt_algorithm])
        token_type = payload.get("type")
        if token_type == "passkey_registration":
            return payload  # type: ignore[return-value]
        elif token_type == "2fa_setup":
            return payload  # type: ignore[return-value]
        else:
            raise SetupTokenError(f"Invalid setup token type: {token_type}")
    except jwt.ExpiredSignatureError as exc:
        raise SetupTokenError("Setup token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise SetupTokenError("Invalid setup token") from exc


class TwoFactorService:
    def __init__(self, repository: TwoFactorRepositoryInterface):
        self.repository = repository

    async def initiate_totp_setup(self, user_id: str, email: str) -> dict[str, Any]:
        """Start TOTP setup by generating secret, URI and backup codes."""

        secret = generate_totp_secret()
        qr_uri = get_totp_provisioning_uri(secret, user_email=email)
        plain_codes, hashed_codes = generate_backup_codes()

        setup_token = _create_setup_token(
            {
                "sub": user_id,
                "secret": secret,
                "backup_codes_hashed": hashed_codes,
            }
        )

        return {
            "qrCodeUri": qr_uri,
            "secret": secret,
            "backupCodes": plain_codes,
            "setupToken": setup_token,
            "expiresAt": datetime.now(UTC) + timedelta(minutes=10),
        }

    async def verify_totp_setup(self, setup_token: str, code: str) -> dict[str, Any]:
        """Verify initial TOTP code and persist configuration."""

        payload = _verify_setup_token(setup_token)
        if payload.get("type") != "2fa_setup":
            raise SetupTokenError("Invalid token type for TOTP setup")

        # Type narrowing - payload is TotpSetupTokenPayload at this point
        user_id: str = payload["sub"]
        secret: str = payload["secret"]  # type: ignore[index]
        hashed_codes: list[str] = payload["backup_codes_hashed"]  # type: ignore[index]

        if not verify_totp_with_window(secret, code):
            raise InvalidTwoFactorCodeError("Invalid verification code")

        encrypted_secret = encrypt_secret(secret)
        await self.repository.create_totp_config(
            user_id=user_id,
            encrypted_secret=encrypted_secret,
            backup_codes_hashed_json=json.dumps(hashed_codes),
        )
        await self.repository.mark_totp_verified(user_id)

        return {"success": True, "message": "TOTP enabled"}

    async def get_totp_status(self, user_id: str) -> dict[str, Any]:
        config = await self.repository.get_totp_config(user_id)
        if not config:
            return {
                "isEnabled": False,
                "isVerified": False,
                "createdAt": None,
                "verifiedAt": None,
                "lastVerifiedAt": None,
                "backupCodesRemaining": 0,
            }

        try:
            backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
            used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []
        except Exception:
            backup_codes = []
            used_codes = []

        return {
            "isEnabled": bool(config.is_enabled),
            "isVerified": bool(config.verified_at is not None or config.is_enabled),
            "createdAt": config.created_at,
            "verifiedAt": config.verified_at,
            "lastVerifiedAt": config.last_verified_at,
            "backupCodesRemaining": max(0, len(backup_codes) - len(used_codes)),
        }

    async def regenerate_backup_codes(
        self,
        user_id: str,
        password: str | None = None,
        totp_code: str | None = None,
        user_repository=None,
    ) -> dict[str, Any]:
        """Regenerate backup codes. Requires password or current TOTP code."""
        from app.modules.auth.auth_utils import verify_password

        config = await self.repository.get_totp_config(user_id)
        if not config or not config.is_enabled:
            raise ValueError("TOTP is not enabled for this user")

        # Verify password or TOTP code
        if password:
            if not user_repository:
                raise ValueError("User repository required for password verification")
            user = await user_repository.get_user_by_id(user_id)
            if not user or not verify_password(password, user.hashedPassword):
                raise InvalidTwoFactorCodeError("Invalid password")
        elif totp_code:
            secret = decrypt_secret(config.secret)
            if not verify_totp_with_window(secret, totp_code):
                raise InvalidTwoFactorCodeError("Invalid TOTP code")
        else:
            raise ValueError("Either password or TOTP code must be provided")

        # Generate new backup codes
        plain_codes, hashed_codes = generate_backup_codes()
        await self.repository.update_backup_codes(user_id, json.dumps(hashed_codes))

        return {
            "codes": plain_codes,
            "count": len(plain_codes),
            "generatedAt": datetime.now(UTC),
        }

    async def disable_totp(
        self,
        user_id: str,
        password: str | None = None,
        backup_code: str | None = None,
        user_repository=None,
    ) -> dict[str, Any]:
        """Disable TOTP. Requires password or backup code."""
        from app.modules.auth.auth_utils import verify_password

        config = await self.repository.get_totp_config(user_id)
        if not config:
            raise ValueError("TOTP is not enabled for this user")

        # Verify password or backup code
        if password:
            if not user_repository:
                raise ValueError("User repository required for password verification")
            user = await user_repository.get_user_by_id(user_id)
            if not user or not verify_password(password, user.hashedPassword):
                raise InvalidTwoFactorCodeError("Invalid password")
        elif backup_code:
            backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
            used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []
            if not verify_backup_code(backup_code, backup_codes, used_codes):
                raise InvalidTwoFactorCodeError("Invalid backup code")
        else:
            raise ValueError("Either password or backup code must be provided")

        # Disable TOTP
        await self.repository.disable_totp(user_id)

        return {"success": True, "message": "TOTP disabled"}

    async def has_two_factor_enabled(self, user_id: str) -> bool:
        """Check if user has any 2FA method enabled."""
        config = await self.repository.get_totp_config(user_id)
        has_totp = config is not None and config.is_enabled
        passkeys = await self.repository.get_passkeys(user_id)
        has_passkeys = len(passkeys) > 0
        return has_totp or has_passkeys

    async def get_available_methods(self, user_id: str) -> list[str]:
        """Get list of available 2FA methods for user."""
        methods = []
        config = await self.repository.get_totp_config(user_id)
        if config and config.is_enabled:
            methods.append("totp")
        # Check for passkeys
        passkeys = await self.repository.get_passkeys(user_id)
        if passkeys:
            methods.append("webauthn")
        return methods

    async def get_preferred_method(self, user_id: str) -> str | None:
        """Get preferred 2FA method (last used or first available)."""
        methods = await self.get_available_methods(user_id)
        if methods:
            # For now, just return first method (TOTP)
            # In future, could check last_verified_at to determine preference
            return methods[0]
        return None

    async def verify_totp_login(self, two_factor_token: str, code: str) -> dict[str, Any]:
        """Verify TOTP code during login and return JWT tokens."""
        from app.modules.auth.auth_utils import create_access_token, create_refresh_token
        from .auth_utils import verify_two_factor_token

        # Verify 2FA token
        payload = verify_two_factor_token(two_factor_token)
        user_id: str = payload["sub"]

        # Get TOTP config
        config = await self.repository.get_totp_config(user_id)
        if not config or not config.is_enabled:
            raise InvalidTwoFactorCodeError("TOTP is not enabled for this user")

        # Try TOTP code first
        secret = decrypt_secret(config.secret)
        is_valid = verify_totp_with_window(secret, code)

        # If TOTP code invalid, try backup codes
        if not is_valid:
            backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
            used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []

            if verify_backup_code(code, backup_codes, used_codes):
                # Mark backup code as used
                from .crypto_utils import mark_backup_code_used

                used_codes = mark_backup_code_used(code, used_codes)
                await self.repository.mark_backup_code_used(user_id, json.dumps(used_codes))
                is_valid = True
            else:
                raise InvalidTwoFactorCodeError("Invalid verification code")

        if not is_valid:
            raise InvalidTwoFactorCodeError("Invalid verification code")

        # Update last verified timestamp
        await self.repository.update_totp_last_verified(user_id)

        # Get email from 2FA token payload (should be present after our changes)
        # If not present (backward compatibility), we'd need to fetch user, but for now assume it's there
        user_email = payload.get("email")
        if not user_email:
            # Fallback: if email not in payload (shouldn't happen with new implementation),
            # we'd need to get user from repository, but for now raise error
            # In production, you might want to fetch user here
            raise InvalidTwoFactorCodeError("User email not found in token")

        # Determine 2FA method used (TOTP or backup code - both are TOTP method)
        tfa_method = "totp"

        # Generate JWT tokens with 2FA verification status
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_email,
                "tfaVerified": True,
                "tfaMethod": tfa_method,
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user_id,
                "email": user_email,
                "tfaVerified": True,
                "tfaMethod": tfa_method,
            }
        )

        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "expiresIn": settings.security.access_token_expires_minutes * 60,
        }

    async def initiate_passkey_registration(self, user_id: str, user_email: str, user_name: str, name: str | None = None) -> dict[str, Any]:
        """Initiate passkey registration by generating WebAuthn options."""
        from .webauthn_utils import create_registration_options

        # Generate registration options and challenge
        options_json, challenge = create_registration_options(user_id, user_email, user_name)

        # Create registration token (similar to setup token)
        registration_token = _create_setup_token(
            {
                "sub": user_id,
                "challenge": challenge,
                "type": "passkey_registration",
            }
        )

        # Get expiration (default 10 minutes for setup tokens)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        return {
            "options": options_json,
            "registrationToken": registration_token,
            "expiresAt": expires_at,
        }

    async def complete_passkey_registration(
        self,
        registration_token: str,
        credential_json: dict[str, Any],
        name: str | None = None,
        user_agent: str | None = None,
        origin: str | None = None,
    ) -> dict[str, Any]:
        """Complete passkey registration by verifying credential and saving."""
        from .webauthn_utils import verify_registration
        from .crypto_utils import encrypt_secret
        import json

        # Verify registration token
        payload = _verify_setup_token(registration_token)
        if payload.get("type") != "passkey_registration":
            raise SetupTokenError("Invalid registration token type")

        # Type narrowing - payload is PasskeyRegistrationTokenPayload at this point
        user_id: str = payload["sub"]
        expected_challenge: str = payload["challenge"]  # type: ignore[index]

        # Get origin from settings if not provided
        if not origin:
            origin = getattr(
                getattr(settings, "two_factor", object()),
                "webauthn_origin",
                "http://localhost:3000",
            )

        # Verify WebAuthn credential
        verified_data = verify_registration(
            credential_json=credential_json,
            expected_challenge=expected_challenge,
            expected_origin=origin,
        )

        # Encrypt public key
        encrypted_public_key = encrypt_secret(verified_data["public_key"])

        # Generate name if not provided
        if not name:
            # Try to generate from user agent or use default
            if user_agent:
                # Simple extraction (could be improved)
                if "iPhone" in user_agent or "iPad" in user_agent:
                    name = "iPhone/iPad"
                elif "Mac" in user_agent:
                    name = "Mac"
                elif "Windows" in user_agent:
                    name = "Windows Device"
                elif "Android" in user_agent:
                    name = "Android Device"
                else:
                    name = "Security Key"
            else:
                name = "Security Key"

        # Save transports as JSON
        transports_json = json.dumps(verified_data.get("transports", [])) if verified_data.get("transports") else None

        # Create passkey in database
        passkey_id = await self.repository.create_passkey(
            user_id=user_id,
            name=name,
            credential_id=verified_data["credential_id"],
            encrypted_public_key=encrypted_public_key,
            counter=verified_data["counter"],
            aaguid=verified_data.get("aaguid"),
            transports_json=transports_json,
            backup_eligible=verified_data.get("backup_eligible", False),
            backup_state=verified_data.get("backup_state", False),
            user_agent=user_agent,
        )

        # Get created passkey
        passkeys = await self.repository.get_passkeys(user_id)
        created_passkey = next((pk for pk in passkeys if pk.id == passkey_id), None)

        if not created_passkey:
            raise ValueError("Failed to retrieve created passkey")

        # Convert to response format
        transports = json.loads(created_passkey.transports) if created_passkey.transports else None

        return {
            "id": created_passkey.id,
            "name": created_passkey.name,
            "createdAt": created_passkey.created_at,
            "lastUsedAt": created_passkey.last_used_at,
            "isEnabled": created_passkey.is_enabled,
            "userAgent": created_passkey.user_agent,
            "aaguid": created_passkey.aaguid,
            "transports": transports,
            "backupEligible": created_passkey.backup_eligible,
            "backupState": created_passkey.backup_state,
        }

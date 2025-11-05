"""Pydantic schemas for TOTP setup and status."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InitiateTotpRequest(BaseModel):
    pass


class VerifyTotpSetupRequest(BaseModel):
    setupToken: str
    code: str = Field(..., min_length=6, max_length=8)


class TotpInitiateResponse(BaseModel):
    qrCodeUri: str
    secret: str
    backupCodes: list[str]
    setupToken: str
    expiresAt: datetime


class TotpStatusResponse(BaseModel):
    isEnabled: bool
    isVerified: bool
    createdAt: datetime | None = None
    verifiedAt: datetime | None = None
    lastVerifiedAt: datetime | None = None
    backupCodesRemaining: int = 0


class RegenerateBackupCodesRequest(BaseModel):
    password: str | None = None
    totpCode: str | None = None


class BackupCodesResponse(BaseModel):
    codes: list[str]
    count: int
    generatedAt: datetime


class DisableTotpRequest(BaseModel):
    password: str | None = None
    backupCode: str | None = None


class TwoFactorRequiredResponse(BaseModel):
    """Response when user needs 2FA verification during login."""

    requiresTwoFactor: bool = True
    twoFactorToken: str
    methods: list[str]  # ["totp", "webauthn"]
    preferredMethod: str | None = None
    allowBackupCodes: bool = True
    expiresAt: datetime


class VerifyTotpLoginRequest(BaseModel):
    """Request schema for TOTP verification during login."""

    twoFactorToken: str
    code: str = Field(..., min_length=6, max_length=12)  # 6-digit TOTP or backup code


# WebAuthn/Passkey schemas
class InitiatePasskeyRegistrationRequest(BaseModel):
    """Request to initiate passkey registration."""

    name: str | None = None  # Optional friendly name


class CompletePasskeyRegistrationRequest(BaseModel):
    """Request to complete passkey registration."""

    registrationToken: str
    credential: dict  # PublicKeyCredential from WebAuthn API
    name: str | None = None  # Optional name override
    userAgent: str | None = None  # Optional, can be extracted from headers


class PasskeyRegistrationInitiateResponse(BaseModel):
    """Response for passkey registration initiation."""

    options: dict  # PublicKeyCredentialCreationOptions
    registrationToken: str
    expiresAt: datetime


class PasskeyResponse(BaseModel):
    """Response model for a passkey."""

    id: str
    name: str
    createdAt: datetime
    lastUsedAt: datetime | None
    isEnabled: bool
    userAgent: str | None
    aaguid: str | None
    transports: list[str] | None
    backupEligible: bool
    backupState: bool


class PasskeyListResponse(BaseModel):
    """Response for list of passkeys."""

    passkeys: list[PasskeyResponse]
    total: int

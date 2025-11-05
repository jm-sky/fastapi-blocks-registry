"""FastAPI router for TOTP setup (Phase 1 & 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.limiter import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.repositories import get_user_repository
from app.modules.auth.types.repository import UserRepositoryInterface
from .repositories import get_two_factor_repository
from .schemas import (
    BackupCodesResponse,
    CompletePasskeyRegistrationRequest,
    DisableTotpRequest,
    InitiatePasskeyRegistrationRequest,
    InitiateTotpRequest,
    PasskeyRegistrationInitiateResponse,
    PasskeyResponse,
    RegenerateBackupCodesRequest,
    TotpInitiateResponse,
    TotpStatusResponse,
    VerifyTotpLoginRequest,
    VerifyTotpSetupRequest,
)
from .service import TwoFactorService

router = APIRouter(prefix="/two-factor", tags=["Two-Factor Authentication"])


def get_service(repo=Depends(get_two_factor_repository)) -> TwoFactorService:
    return TwoFactorService(repository=repo)


@router.post("/totp/initiate", response_model=TotpInitiateResponse)
@rate_limit("3/minute")
async def initiate_totp_setup(
    _: InitiateTotpRequest | None = None,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
):
    data = await service.initiate_totp_setup(user_id=current_user.id, email=current_user.email)
    return data


@router.post("/totp/verify")
@rate_limit("5/minute")
async def verify_totp_setup(
    body: VerifyTotpSetupRequest,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
):
    try:
        return await service.verify_totp_setup(setup_token=body.setupToken, code=body.code)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/totp/status", response_model=TotpStatusResponse)
@rate_limit("10/minute")
async def totp_status(
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
):
    return await service.get_totp_status(user_id=current_user.id)


@router.post("/totp/regenerate-backup-codes", response_model=BackupCodesResponse)
@rate_limit("3/minute")
async def regenerate_backup_codes(
    body: RegenerateBackupCodesRequest,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
):
    try:
        return await service.regenerate_backup_codes(
            user_id=current_user.id,
            password=body.password,
            totp_code=body.totpCode,
            user_repository=user_repo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/totp/disable")
@rate_limit("3/minute")
async def disable_totp(
    body: DisableTotpRequest,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
):
    try:
        return await service.disable_totp(
            user_id=current_user.id,
            password=body.password,
            backup_code=body.backupCode,
            user_repository=user_repo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/totp/verify-login")
@rate_limit("5/minute")
async def verify_totp_login(
    body: VerifyTotpLoginRequest,
    request: Request,
    service: TwoFactorService = Depends(get_service),
):
    """Verify TOTP code during login and return JWT tokens.

    This endpoint is public (no auth required) as it's part of the login flow.
    Rate limiting is applied both globally and per-user.
    """
    from .decorators import require_2fa_rate_limit

    # Apply per-user rate limiting wrapper
    @require_2fa_rate_limit(max_attempts=5, window_minutes=15)
    async def _verify_with_rate_limit():
        try:
            return await service.verify_totp_login(
                two_factor_token=body.twoFactorToken,
                code=body.code,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

    return await _verify_with_rate_limit()


# WebAuthn/Passkey endpoints
@router.post("/webauthn/register/initiate", response_model=PasskeyRegistrationInitiateResponse)
@rate_limit("5/minute")
async def initiate_passkey_registration(
    body: InitiatePasskeyRegistrationRequest,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
):
    """Initiate passkey registration by generating WebAuthn options."""
    return await service.initiate_passkey_registration(
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.name,
        name=body.name,
    )


@router.post("/webauthn/register/complete", response_model=PasskeyResponse)
@rate_limit("5/minute")
async def complete_passkey_registration(
    body: CompletePasskeyRegistrationRequest,
    request: Request,
    current_user: CurrentUser = Depends(),
    service: TwoFactorService = Depends(get_service),
):
    """Complete passkey registration by verifying WebAuthn credential."""
    # Extract user agent from request headers
    user_agent = request.headers.get("User-Agent")
    origin = request.headers.get("Origin") or request.headers.get("Referer")

    try:
        return await service.complete_passkey_registration(
            registration_token=body.registrationToken,
            credential_json=body.credential,
            name=body.name,
            user_agent=user_agent,
            origin=origin,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

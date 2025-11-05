# Plan implementacji modułu 2FA (Two-Factor Authentication)

## 📋 Przegląd

Ten dokument zawiera plan implementacji modułu 2FA dla FastAPI Blocks Registry. Moduł będzie wspierał dwa typy weryfikacji dwuskładnikowej:
1. **TOTP (Time-based One-Time Password)** - aplikacje autentykacyjne (Google Authenticator, Authy, etc.)
2. **WebAuthn/Passkeys** - klucze bezpieczeństwa (YubiKey, Touch ID, Face ID, Windows Hello, etc.)

**Ostatnia aktualizacja:** 2025-01-05 (wersja 2.0 - po review)
**Status:** Gotowy do implementacji

## 🔗 Powiązane dokumenty

- **[JWT_FLOW.md](./JWT_FLOW.md)** - Szczegółowy opis flow JWT, wszystkich stanów tokenów i integracji z 2FA
- [BACKEND_ROADMAP.md](./BACKEND_ROADMAP.md) - Roadmap backendu
- [FRONTEND_ROADMAP.md](./FRONTEND_ROADMAP.md) - Roadmap frontendu

---

## 🔍 Analiza wzorców z modułu `auth`

### Obecna struktura modułu `auth`

Moduł `auth` używa następujących wzorców i struktur:

#### Architektura
- **Repository Pattern** - abstrakcja warstwy danych (`types/repository.py`)
- **Service Layer** - logika biznesowa (`service.py`)
- **Router** - endpointy API (`router.py`)
- **Dependencies** - FastAPI dependency injection (`dependencies.py`)
- **Schemas** - Pydantic validation (`schemas.py`)
- **Models** - Pydantic models dla API (`models.py`) - **camelCase**
- **DB Models** - SQLAlchemy ORM (`db_models.py`) - **snake_case**
- **Repositories** - implementacja bazy danych (`repositories.py`)
- **Exceptions** - niestandardowe wyjątki (`exceptions.py`)
- **Utils** - funkcje pomocnicze (`auth_utils.py`)

#### Konwencje
- **camelCase** dla pól w schemas (API responses)
- **snake_case** dla pól w bazie danych (SQLAlchemy)
- **Modular config** - nested settings w `app.core.config`
- **Rate limiting** - dekoratory na endpointach
- **JWT tokens** - access/refresh/password-reset tokens
- **Async/await** - wszystkie operacje I/O są asynchroniczne

#### Integracja z User
- Moduł `auth` ma własny model `User` (Pydantic) i `UserDB` (SQLAlchemy)
- Tabele w bazie: `users` z polami dla reset tokenów
- JWT zawiera `sub` (user_id) w payload

---

## 🏗️ Proponowana struktura modułu `two_factor`

### Lokalizacja
```
fastapi_registry/example_project/app/modules/two_factor/
├── __init__.py
├── router.py                    # API endpoints
├── service.py                   # Business logic
├── dependencies.py              # FastAPI dependencies (2FA checks)
├── models.py                    # Pydantic models dla API (camelCase) - TOTPConfig, Passkey
├── db_models.py                 # SQLAlchemy ORM models (snake_case) - tables
├── schemas.py                   # Request/Response schemas (camelCase)
├── repositories.py              # Database repository implementation
├── types/
│   ├── __init__.py
│   └── repository.py            # Repository interface
├── totp_utils.py                # TOTP generation/verification utilities
├── webauthn_utils.py            # WebAuthn utilities (registration/authentication)
├── crypto_utils.py              # Encryption/hashing utilities
├── exceptions.py                # Custom exceptions
├── decorators.py                # Per-user rate limiting decorators
└── README.md                    # Documentation
```

**UWAGA:** Nazewnictwo zgodne z modułem `auth`:
- `models.py` = Pydantic models (API, camelCase)
- `db_models.py` = SQLAlchemy models (Database, snake_case)

### Struktura bazy danych

#### Tabela `totp_configs`
```python
- id: str (ULID/UUID, primary key)
- user_id: str (foreign key -> users.id, UNIQUE constraint)
- secret: str (encrypted TOTP secret)
- backup_codes: str (JSON array of HASHED backup codes)
- backup_codes_used: str | None (JSON array of used backup code hashes)
- is_enabled: bool (default: False)
- created_at: datetime
- verified_at: datetime | None (null until user verifies setup)
- last_verified_at: datetime | None (for audit purposes)
- failed_attempts: int (default: 0, for per-user rate limiting)
- locked_until: datetime | None (account lockout after max attempts)
```

**ZMIANA:** Backup codes są **HASHOWANE** (jak hasła), nie szyfrowane. Użytkownik widzi je tylko raz podczas setup.

#### Tabela `passkeys`
```python
- id: str (ULID/UUID, primary key)
- user_id: str (foreign key -> users.id, NO UNIQUE - user może mieć wiele passkeys)
- name: str (user-given name, e.g., "MacBook Pro", "iPhone 14")
- credential_id: str (unique, indexed)
- public_key: str (encrypted)
- counter: int (for replay attack prevention)
- aaguid: str | None (Authenticator AAGUID - do identyfikacji typu urządzenia)
- transports: str | None (JSON array: ["usb", "nfc", "ble", "internal"])
- backup_eligible: bool (default: False, WebAuthn flag)
- backup_state: bool (default: False, WebAuthn flag)
- is_enabled: bool (default: True)
- created_at: datetime
- last_used_at: datetime | None
- user_agent: str | None (przydatne do identyfikacji urządzenia)
```

#### Rozszerzenie tabeli `users` (OPCJONALNE)

**REKOMENDACJA:** **NIE** dodawać pól do tabeli `users`. Zamiast tego:
- Sprawdzaj istnienie rekordów w `totp_configs`/`passkeys`
- Dodaj computed property w Pydantic User model

```python
# W models.py (Pydantic User model)
class User(BaseModel):
    # ... existing fields ...

    async def has_two_factor_enabled(self, repository) -> bool:
        """Check if user has any 2FA method enabled."""
        # Query will be handled by service layer
        pass
```

**Alternatywa (jeśli wydajność krytyczna):** Dodaj pola jako cache, ale źródłem prawdy są tabele 2FA:
```python
# OPCJONALNE pola w users (wymaga migracji)
- two_factor_enabled: bool (cache/flag)
- two_factor_method: str | None ("totp", "webauthn", "both")
- two_factor_updated_at: datetime | None
```

---

## 🔐 Funkcjonalności TOTP

### Przepływ konfiguracji TOTP

1. **Initiate TOTP Setup** (`POST /two-factor/totp/initiate`)
   - Generuje secret
   - Zwraca QR code URI (otpauth://, nie obraz - frontend generuje QR)
   - Zwraca backup codes (w plain text - JEDYNY RAZ!)
   - Zwraca setup verification token (tymczasowy, 10 min expiration)

2. **Verify TOTP Setup** (`POST /two-factor/totp/verify`)
   - Użytkownik wprowadza kod z aplikacji autentykacyjnej
   - Weryfikuje kod TOTP (z time window tolerance)
   - Jeśli poprawny - zapisuje konfigurację jako `is_enabled=True`, `verified_at=now()`
   - Inwaliduje setup verification token
   - Hashuje i zapisuje backup codes

3. **Get TOTP Status** (`GET /two-factor/totp/status`)
   - Zwraca status TOTP (enabled, verified, created date)

4. **Regenerate Backup Codes** (`POST /two-factor/totp/regenerate-backup-codes`)
   - Generuje nowe backup codes (plain text, pokazuje użytkownikowi)
   - Hashuje i zapisuje nowe kody
   - Inwaliduje stare (czyści `backup_codes_used`)
   - Wymaga potwierdzenia hasłem lub bieżącym TOTP kodem

5. **Disable TOTP** (`POST /two-factor/totp/disable`)
   - Wyłącza TOTP dla użytkownika
   - Usuwa konfigurację z bazy (lub ustawia `is_enabled=False`)
   - Wymaga potwierdzenia hasłem lub backup code

### Przepływ logowania z TOTP

1. **Login Request** (`POST /auth/login`)
   - Standardowy login (bez zmian w auth module!)
   - **NOWE:** Po weryfikacji hasła, sprawdź czy user ma 2FA
   - Jeśli użytkownik ma TOTP enabled:
     - **NIE zwracaj access/refresh tokens**
     - Zwraca `TwoFactorRequiredResponse`:
       - `requiresTwoFactor: true`
       - `twoFactorToken` (tymczasowy, 5 min expiration)
       - `methods` (["totp"] lub ["totp", "webauthn"])
       - `preferredMethod` (ostatnio używana metoda)
     - Frontend przechodzi do ekranu wprowadzania kodu TOTP

2. **Verify TOTP on Login** (`POST /two-factor/totp/verify-login`)
   - Przyjmuje `twoFactorToken` i kod TOTP (lub backup code)
   - Weryfikuje kod
   - Jeśli backup code: sprawdź czy nie został użyty, oznacz jako użyty
   - Jeśli poprawny - zwraca normalne JWT tokens (access + refresh)
   - Aktualizuje `last_verified_at`
   - **Rate limiting:** Per-user + global (max 5 prób na 15 minut)

### Schemas TOTP

```python
# Request schemas
class InitiateTotpRequest(BaseModel):
    pass  # No input needed, user authenticated via CurrentUser

class VerifyTotpSetupRequest(BaseModel):
    setupToken: str  # From initiate response
    code: str = Field(..., min_length=6, max_length=8)  # 6-digit TOTP code

class VerifyTotpLoginRequest(BaseModel):
    twoFactorToken: str  # From login response
    code: str  # 6-digit TOTP code OR backup code (12 chars with dashes)

class RegenerateBackupCodesRequest(BaseModel):
    password: str | None = None  # For security
    totpCode: str | None = None  # Alternative: current TOTP code
    # One of the two must be provided

class DisableTotpRequest(BaseModel):
    password: str | None = None
    backupCode: str | None = None  # Can use backup code to disable
    # One of the two must be provided

# Response schemas
class TotpInitiateResponse(BaseModel):
    qrCodeUri: str  # otpauth:// URI for QR code generation (frontend)
    secret: str  # Plain secret (for manual entry in authenticator app)
    backupCodes: list[str]  # Plain backup codes (ONLY shown once!)
    setupToken: str  # For verification step
    expiresAt: datetime

class TotpStatusResponse(BaseModel):
    isEnabled: bool
    isVerified: bool  # Has user completed setup?
    createdAt: datetime | None
    verifiedAt: datetime | None
    lastVerifiedAt: datetime | None
    backupCodesRemaining: int  # How many unused backup codes

class BackupCodesResponse(BaseModel):
    codes: list[str]  # Plain backup codes (only during regeneration)
    count: int
    generatedAt: datetime
```

---

## 🔑 Funkcjonalności WebAuthn/Passkeys

### Przepływ rejestracji Passkey

1. **Initiate Passkey Registration** (`POST /two-factor/webauthn/register/initiate`)
   - Przyjmuje `name` (opcjonalne, może być generowane na podstawie user agent)
   - Generuje WebAuthn challenge
   - Zwraca `PublicKeyCredentialCreationOptions` (JSON)
   - Zwraca `registrationToken` (tymczasowy, 10 min expiration)

2. **Complete Passkey Registration** (`POST /two-factor/webauthn/register/complete`)
   - Przyjmuje `registrationToken` i `credential` (z frontendu WebAuthn API)
   - Weryfikuje credential (challenge, origin, RP ID)
   - Zapisuje passkey do bazy danych (encrypted public key)
   - Zwraca informacje o zarejestrowanym passkey

### Przepływ autentykacji Passkey

1. **Initiate Passkey Authentication** (`POST /two-factor/webauthn/authenticate/initiate`)
   - Przyjmuje `twoFactorToken` (z login response)
   - Pobiera wszystkie aktywne passkeys użytkownika
   - Generuje WebAuthn challenge
   - Zwraca `PublicKeyCredentialRequestOptions` (JSON)

2. **Complete Passkey Authentication** (`POST /two-factor/webauthn/authenticate/complete`)
   - Przyjmuje `twoFactorToken` i `credential` (z frontendu WebAuthn API)
   - Weryfikuje credential i counter (replay attack prevention)
   - Sprawdza czy counter wzrósł (jeśli nie - możliwy atak)
   - Aktualizuje `last_used_at` i `counter`
   - Zwraca normalne JWT tokens (access + refresh)

### Zarządzanie Passkeys

1. **List Passkeys** (`GET /two-factor/webauthn/passkeys`)
   - Zwraca listę wszystkich passkeys użytkownika
   - Z nazwami, datami utworzenia, ostatniego użycia, user agent

2. **Rename Passkey** (`PATCH /two-factor/webauthn/passkeys/{passkey_id}`)
   - Zmienia nazwę passkey (tylko pole `name`)

3. **Delete Passkey** (`DELETE /two-factor/webauthn/passkeys/{passkey_id}`)
   - Usuwa passkey
   - Wymaga potwierdzenia hasłem lub innym passkeyem
   - **Walidacja:** Nie można usunąć ostatniego passkeya, jeśli to jedyna metoda 2FA

### Schemas WebAuthn

```python
# Request schemas
class InitiatePasskeyRegistrationRequest(BaseModel):
    name: str | None = None  # Optional friendly name

class CompletePasskeyRegistrationRequest(BaseModel):
    registrationToken: str
    credential: dict  # PublicKeyCredential from WebAuthn API (navigator.credentials.create)
    name: str | None = None  # Optional name override
    userAgent: str | None = None  # Optional, can be extracted from headers

class InitiatePasskeyAuthRequest(BaseModel):
    twoFactorToken: str  # From login response

class CompletePasskeyAuthRequest(BaseModel):
    twoFactorToken: str
    credential: dict  # PublicKeyCredential from WebAuthn API (navigator.credentials.get)

class UpdatePasskeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class DeletePasskeyRequest(BaseModel):
    password: str | None = None  # Confirm with password
    passkeyId: str | None = None  # Or confirm with another passkey

# Response schemas
class PasskeyRegistrationInitiateResponse(BaseModel):
    options: dict  # PublicKeyCredentialCreationOptions
    registrationToken: str
    expiresAt: datetime

class PasskeyAuthInitiateResponse(BaseModel):
    options: dict  # PublicKeyCredentialRequestOptions
    expiresAt: datetime

class PasskeyResponse(BaseModel):
    id: str
    name: str
    createdAt: datetime
    lastUsedAt: datetime | None
    isEnabled: bool
    userAgent: str | None
    aaguid: str | None
    transports: list[str] | None  # ["usb", "nfc", "ble", "internal"]
    backupEligible: bool
    backupState: bool

class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyResponse]
    total: int
```

---

## 🔄 Integracja z modułem `auth` (Backward Compatible)

### Strategia: NIE modyfikuj bezpośrednio auth module

**WAŻNE:** Aby zachować backward compatibility i nie wprowadzać breaking changes, **NIE modyfikujemy** `auth/service.py` ani `auth/router.py` bezpośrednio.

### Podejście 1: Middleware (REKOMENDOWANE)

Stwórz middleware w module `two_factor`, który intercepts login response.

```python
# W two_factor/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.modules.two_factor.service import TwoFactorService

class TwoFactorMiddleware(BaseHTTPMiddleware):
    """Middleware to intercept login and check 2FA."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only for /auth/login endpoint
        if request.url.path == "/auth/login" and request.method == "POST":
            # Check if response is LoginResponse (status 200)
            if response.status_code == 200:
                # Extract user_id from response
                # Check if user has 2FA enabled
                # If yes, return TwoFactorRequiredResponse instead
                pass

        return response
```

**Problem:** Middleware nie może łatwo modyfikować response body w FastAPI.

### Podejście 2: Dependency Injection (ZALECANE)

Stwórz optional dependency, który sprawdza 2FA po login.

```python
# W two_factor/dependencies.py
from typing import Annotated
from fastapi import Depends
from app.modules.auth.schemas import LoginResponse

async def check_two_factor_requirement(
    login_response: LoginResponse,
    two_factor_service: Annotated[TwoFactorService, Depends(get_two_factor_service)]
) -> LoginResponse | TwoFactorRequiredResponse:
    """
    Check if user requires 2FA after successful login.

    Returns TwoFactorRequiredResponse if 2FA enabled, otherwise original LoginResponse.
    """
    user_id = login_response.user.id

    if await two_factor_service.has_two_factor_enabled(user_id):
        # Generate 2FA token
        two_factor_token = create_two_factor_token(data={"sub": user_id})
        methods = await two_factor_service.get_available_methods(user_id)
        preferred = await two_factor_service.get_preferred_method(user_id)

        return TwoFactorRequiredResponse(
            requiresTwoFactor=True,
            twoFactorToken=two_factor_token,
            methods=methods,
            preferredMethod=preferred,
            expiresAt=datetime.utcnow() + timedelta(minutes=5)
        )

    return login_response
```

**Problem:** Wymaga modyfikacji `auth/router.py`, ale minimal i backwards compatible.

### Podejście 3: Extended Auth Service (NAJLEPSZE)

Stwórz `AuthServiceWith2FA`, który rozszerza `AuthService`.

```python
# W two_factor/auth_integration.py
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import LoginResponse
from app.modules.two_factor.service import TwoFactorService
from app.modules.two_factor.schemas import TwoFactorRequiredResponse

class AuthServiceWith2FA(AuthService):
    """
    Extended AuthService that checks 2FA after login.

    Usage: Replace AuthService with this in dependencies when 2FA module is installed.
    """

    def __init__(self, user_repository, two_factor_service: TwoFactorService):
        super().__init__(user_repository)
        self.two_factor_service = two_factor_service

    async def login_user(
        self, email: str, password: str
    ) -> LoginResponse | TwoFactorRequiredResponse:
        """Login with 2FA check."""
        # Call parent login (password verification)
        # This doesn't generate tokens yet if 2FA enabled
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        if not user.verify_password(password):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Check 2FA
        if await self.two_factor_service.has_two_factor_enabled(user.id):
            two_factor_token = create_two_factor_token(data={"sub": user.id})
            methods = await self.two_factor_service.get_available_methods(user.id)
            preferred = await self.two_factor_service.get_preferred_method(user.id)

            return TwoFactorRequiredResponse(
                requiresTwoFactor=True,
                twoFactorToken=two_factor_token,
                methods=methods,
                preferredMethod=preferred,
                expiresAt=datetime.utcnow() + timedelta(minutes=5)
            )

        # No 2FA - generate tokens as normal
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60
        )
```

**Użycie:** W dokumentacji modułu instrukcja, jak zamienić dependency:
```python
# In your main.py or auth router, replace:
# from app.modules.auth.dependencies import get_auth_service
# with:
from app.modules.two_factor.auth_integration import get_auth_service_with_2fa as get_auth_service
```

### Nowe schemas w `two_factor/schemas.py`

```python
class TwoFactorRequiredResponse(BaseModel):
    """Response when user needs 2FA verification."""
    requiresTwoFactor: bool = True
    twoFactorToken: str
    methods: list[str]  # ["totp", "webauthn"]
    preferredMethod: str | None = None  # Last used method
    allowBackupCodes: bool = True  # If TOTP enabled
    expiresAt: datetime
```

### Backward Compatibility Notes

**Dla użytkowników bez 2FA:**
- Wszystko działa jak wcześniej
- Login zwraca `LoginResponse` z tokenami

**Dla użytkowników z 2FA:**
- Login zwraca `TwoFactorRequiredResponse` (union type w FastAPI)
- Frontend musi obsłużyć ten case i pokazać ekran 2FA
- Dopiero po weryfikacji 2FA dostają access/refresh tokens

**Dla istniejących projektów:**
- Jeśli nie zainstalują modułu 2FA - zero zmian
- Jeśli zainstalują - muszą zamienić dependency (dokumentacja)
- Mogą też używać starego endpoint `/auth/login` i nowego `/auth/login-with-2fa`

---

## 🛡️ Security Implementation

### 1. Encryption i Hashing

#### Encryption dla TOTP secrets i public keys

```python
# W two_factor/crypto_utils.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings

def get_encryption_key() -> bytes:
    """
    Get encryption key for 2FA secrets.

    Priority:
    1. TWO_FACTOR_ENCRYPTION_KEY (dedicated key)
    2. SECRET_KEY (fallback)
    """
    key_source = os.getenv("TWO_FACTOR_ENCRYPTION_KEY") or settings.security.secret_key

    # Derive proper Fernet key (32 bytes) from secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'fastapi_2fa_salt_v1',  # Fixed salt for consistency
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_source.encode()))
    return key

def encrypt_secret(plaintext: str) -> str:
    """
    Encrypt TOTP secret or WebAuthn public key.

    Args:
        plaintext: Secret to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    f = Fernet(get_encryption_key())
    return f.encrypt(plaintext.encode()).decode()

def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypt TOTP secret or WebAuthn public key.

    Args:
        ciphertext: Encrypted secret

    Returns:
        Decrypted plaintext
    """
    f = Fernet(get_encryption_key())
    return f.decrypt(ciphertext.encode()).decode()
```

#### Hashing dla backup codes

**WAŻNE:** Backup codes są **HASHOWANE**, nie szyfrowane (jak hasła).

```python
# W two_factor/crypto_utils.py
import hashlib
import secrets

def generate_backup_codes(count: int = 10) -> tuple[list[str], list[str]]:
    """
    Generate backup codes.

    Returns:
        (plain_codes, hashed_codes) - plain dla użytkownika, hashed do DB
    """
    plain_codes = []
    hashed_codes = []

    for _ in range(count):
        # Format: XXXX-XXXX-XXXX (czytelny dla użytkownika)
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        part3 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}-{part3}"

        plain_codes.append(code)

        # Hash like password (SHA-256 sufficient for backup codes)
        hashed = hashlib.sha256(code.encode()).hexdigest()
        hashed_codes.append(hashed)

    return plain_codes, hashed_codes

def verify_backup_code(
    code: str,
    hashed_codes: list[str],
    used_codes: list[str]
) -> bool:
    """
    Verify backup code and check if not used.

    Args:
        code: User-provided backup code
        hashed_codes: List of valid hashed codes from DB
        used_codes: List of already used code hashes from DB

    Returns:
        True if code is valid and not used
    """
    # Normalize input (remove spaces, uppercase)
    code = code.replace(" ", "").replace("-", "").upper()
    # Re-add dashes for consistent format
    if len(code) == 12:
        code = f"{code[0:4]}-{code[4:8]}-{code[8:12]}"

    code_hash = hashlib.sha256(code.encode()).hexdigest()

    # Check if code is valid
    if code_hash not in hashed_codes:
        return False

    # Check if not already used
    if code_hash in used_codes:
        return False

    return True

def mark_backup_code_used(
    code: str,
    used_codes: list[str]
) -> list[str]:
    """
    Mark backup code as used.

    Args:
        code: Backup code that was just used
        used_codes: Current list of used codes

    Returns:
        Updated list of used codes
    """
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    if code_hash not in used_codes:
        used_codes.append(code_hash)
    return used_codes
```

### 2. Rate Limiting - Per-User

Oprócz globalnego rate limiting (per-IP), dodaj per-user rate limiting dla weryfikacji 2FA.

```python
# W two_factor/decorators.py
from functools import wraps
from datetime import datetime, timedelta
from typing import Callable
from fastapi import HTTPException, Request
from app.modules.two_factor.auth_utils import verify_two_factor_token

# Simple in-memory store (w produkcji: Redis)
_verification_attempts: dict[str, list[datetime]] = {}
_lockouts: dict[str, datetime] = {}

def extract_user_from_request(request: Request) -> str | None:
    """Extract user_id from 2FA token in request body."""
    try:
        # Assuming token is in request body
        import json
        body = request._body.decode() if hasattr(request, '_body') else None
        if body:
            data = json.loads(body)
            token = data.get('twoFactorToken')
            if token:
                payload = verify_two_factor_token(token)
                return payload.get('sub')
    except:
        pass
    return None

def require_2fa_rate_limit(max_attempts: int = 5, window_minutes: int = 15):
    """
    Per-user 2FA verification rate limiting.

    Args:
        max_attempts: Maximum failed attempts before lockout
        window_minutes: Time window for counting attempts
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get('request')
            if not request:
                # Find Request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # Can't rate limit without request, proceed
                return await func(*args, **kwargs)

            # Extract user_id from token
            user_id = extract_user_from_request(request)
            if not user_id:
                # Can't identify user, proceed (global rate limit will catch abuse)
                return await func(*args, **kwargs)

            # Check if locked out
            now = datetime.utcnow()
            if user_id in _lockouts:
                if now < _lockouts[user_id]:
                    remaining = (_lockouts[user_id] - now).total_seconds() / 60
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many failed attempts. Account temporarily locked. Try again in {int(remaining)} minutes."
                    )
                else:
                    # Lockout expired
                    del _lockouts[user_id]
                    if user_id in _verification_attempts:
                        del _verification_attempts[user_id]

            # Track attempt
            if user_id not in _verification_attempts:
                _verification_attempts[user_id] = []

            # Clean old attempts outside window
            cutoff = now - timedelta(minutes=window_minutes)
            _verification_attempts[user_id] = [
                t for t in _verification_attempts[user_id] if t > cutoff
            ]

            # Check if approaching limit (for warning)
            attempts_count = len(_verification_attempts[user_id])

            # Execute function
            try:
                result = await func(*args, **kwargs)
                # On success, clear attempts
                if user_id in _verification_attempts:
                    del _verification_attempts[user_id]
                return result
            except HTTPException as e:
                # On 401 (verification failure), record attempt
                if e.status_code == 401:
                    _verification_attempts[user_id].append(now)

                    # Check if limit exceeded
                    if len(_verification_attempts[user_id]) >= max_attempts:
                        _lockouts[user_id] = now + timedelta(minutes=window_minutes)
                        raise HTTPException(
                            status_code=429,
                            detail=f"Too many failed attempts. Account locked for {window_minutes} minutes."
                        )
                raise
            except Exception:
                # Other exceptions - don't count as verification failure
                raise

        return wrapper
    return decorator
```

**PRODUKCJA:** Zamienić in-memory store na Redis:
```python
import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True
)

def track_failed_attempt(user_id: str, window_minutes: int = 15) -> int:
    """Track failed 2FA attempt in Redis."""
    key = f"2fa_attempts:{user_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_minutes * 60)
    return count

def clear_failed_attempts(user_id: str):
    """Clear failed attempts after successful verification."""
    redis_client.delete(f"2fa_attempts:{user_id}")

def is_locked_out(user_id: str) -> tuple[bool, int]:
    """Check if user is locked out."""
    key = f"2fa_lockout:{user_id}"
    ttl = redis_client.ttl(key)
    if ttl > 0:
        return True, ttl // 60  # minutes remaining
    return False, 0

def lockout_user(user_id: str, duration_minutes: int = 15):
    """Lockout user for specified duration."""
    key = f"2fa_lockout:{user_id}"
    redis_client.setex(key, duration_minutes * 60, "1")
```

### 3. TOTP Time Window Tolerance

```python
# W two_factor/totp_utils.py
import pyotp
from app.core.config import settings

def verify_totp_with_window(
    secret: str,
    code: str,
    window: int = 1
) -> bool:
    """
    Verify TOTP code with time window tolerance.

    Args:
        secret: TOTP secret (base32)
        code: 6-digit code from user
        window: Time window (default 1 = ±30s for 30s period)

    Returns:
        True if code is valid within time window
    """
    totp = pyotp.TOTP(
        secret,
        interval=settings.two_factor.totp_period,
        digits=settings.two_factor.totp_digits,
    )

    # pyotp.verify() supports valid_window parameter
    return totp.verify(code, valid_window=window)

def generate_totp_secret() -> str:
    """Generate random TOTP secret."""
    return pyotp.random_base32()

def get_totp_provisioning_uri(
    secret: str,
    user_email: str,
    issuer: str | None = None
) -> str:
    """
    Get TOTP provisioning URI for QR code.

    Returns:
        otpauth:// URI
    """
    issuer = issuer or settings.two_factor.totp_issuer
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user_email,
        issuer_name=issuer
    )
```

### 4. WebAuthn Security

```python
# W two_factor/webauthn_utils.py
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    parse_registration_credential_json,
    parse_authentication_credential_json,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorTransport,
)
from app.core.config import settings

def create_registration_options(user_id: str, user_email: str, user_name: str):
    """
    Create WebAuthn registration options.

    Returns:
        (options_json, challenge) - options for frontend, challenge to store
    """
    options = generate_registration_options(
        rp_id=settings.two_factor.webauthn_rp_id,
        rp_name=settings.two_factor.webauthn_rp_name,
        user_id=user_id.encode(),
        user_name=user_email,
        user_display_name=user_name,
        timeout=settings.two_factor.webauthn_timeout,
    )

    return options_to_json(options), bytes_to_base64url(options.challenge)

def verify_registration(
    credential_json: dict,
    expected_challenge: str,
    expected_origin: str,
    expected_rp_id: str
) -> dict:
    """
    Verify WebAuthn registration response.

    Returns:
        Verified credential data (credential_id, public_key, counter, etc.)

    Raises:
        Exception if verification fails
    """
    credential = parse_registration_credential_json(credential_json)

    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_origin=expected_origin,
        expected_rp_id=expected_rp_id,
    )

    return {
        "credential_id": bytes_to_base64url(verification.credential_id),
        "public_key": bytes_to_base64url(verification.credential_public_key),
        "counter": verification.sign_count,
        "aaguid": str(verification.aaguid),
        "credential_type": verification.credential_type,
        "transports": credential.response.transports if hasattr(credential.response, 'transports') else [],
        "backup_eligible": verification.credential_backup_eligible,
        "backup_state": verification.credential_backed_up,
    }

def create_authentication_options(passkeys: list[dict], challenge_bytes: bytes | None = None):
    """
    Create WebAuthn authentication options.

    Args:
        passkeys: List of user's passkeys (must have credential_id)
        challenge_bytes: Optional custom challenge

    Returns:
        (options_json, challenge)
    """
    # Convert passkeys to PublicKeyCredentialDescriptor
    allow_credentials = [
        PublicKeyCredentialDescriptor(
            id=base64url_to_bytes(pk["credential_id"]),
            transports=[AuthenticatorTransport(t) for t in pk.get("transports", [])]
        )
        for pk in passkeys
    ]

    options = generate_authentication_options(
        rp_id=settings.two_factor.webauthn_rp_id,
        timeout=settings.two_factor.webauthn_timeout,
        allow_credentials=allow_credentials,
        user_verification="preferred",
        challenge=challenge_bytes,
    )

    return options_to_json(options), bytes_to_base64url(options.challenge)

def verify_authentication(
    credential_json: dict,
    expected_challenge: str,
    credential_public_key: str,
    credential_current_counter: int,
    expected_origin: str,
    expected_rp_id: str
) -> int:
    """
    Verify WebAuthn authentication response.

    Returns:
        New counter value

    Raises:
        Exception if verification fails or counter didn't increase (replay attack)
    """
    credential = parse_authentication_credential_json(credential_json)

    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_origin=expected_origin,
        expected_rp_id=expected_rp_id,
        credential_public_key=base64url_to_bytes(credential_public_key),
        credential_current_sign_count=credential_current_counter,
        require_user_verification=False,  # "preferred" mode
    )

    new_counter = verification.new_sign_count

    # CRITICAL: Verify counter increased (replay attack prevention)
    if new_counter <= credential_current_counter:
        raise ValueError(
            f"Counter did not increase (possible replay attack). "
            f"Current: {credential_current_counter}, Received: {new_counter}"
        )

    return new_counter
```

### 5. Audit Logging Integration

```python
# W two_factor/service.py
from app.modules.logs.service import LogService
from app.modules.logs.models import LogLevel

class TwoFactorService:
    def __init__(
        self,
        repository,
        log_service: LogService | None = None
    ):
        self.repository = repository
        self.log_service = log_service

    async def _log(
        self,
        level: LogLevel,
        message: str,
        user_id: str | None = None,
        metadata: dict | None = None
    ):
        """Helper to log 2FA events."""
        if self.log_service:
            await self.log_service.log(
                level=level,
                message=message,
                user_id=user_id,
                module="two_factor",
                function_name=None,
                metadata=metadata or {}
            )

    async def verify_totp_login(self, two_factor_token: str, code: str):
        """Verify TOTP during login."""
        try:
            # Extract user_id from token
            payload = verify_two_factor_token(two_factor_token)
            user_id = payload["sub"]

            # Get TOTP config
            totp_config = await self.repository.get_totp_config(user_id)

            # Verify code
            secret = decrypt_secret(totp_config.secret)
            is_valid = verify_totp_with_window(secret, code)

            if not is_valid:
                # Try backup codes
                is_backup = await self._verify_backup_code(totp_config, code)
                if not is_backup:
                    await self._log(
                        LogLevel.WARNING,
                        "2FA login failed - invalid code",
                        user_id=user_id,
                        metadata={"method": "totp", "code_length": len(code)}
                    )
                    raise InvalidTwoFactorCodeError("Invalid verification code")

            # Success
            await self._log(
                LogLevel.INFO,
                "2FA login successful",
                user_id=user_id,
                metadata={"method": "totp", "used_backup_code": is_backup}
            )

            # Update last_verified_at
            await self.repository.update_totp_last_verified(user_id)

            # Generate tokens
            return self._generate_auth_tokens(user_id)

        except Exception as e:
            await self._log(
                LogLevel.ERROR,
                f"2FA login error: {str(e)}",
                user_id=user_id if 'user_id' in locals() else None,
                metadata={"error": str(e)}
            )
            raise
```

---

## 🔧 Configuration

### Nowe settings w `app/core/config.py`

```python
class TwoFactorSettings(BaseSettings):
    """Two-factor authentication configuration."""

    model_config = _base_config

    # TOTP settings
    totp_issuer: str = Field(
        default="FastAPI App",
        validation_alias="TOTP_ISSUER",
        description="TOTP issuer name (shown in authenticator apps)"
    )
    totp_algorithm: str = Field(
        default="SHA1",
        validation_alias="TOTP_ALGORITHM",
        description="TOTP hashing algorithm (SHA1, SHA256, SHA512)"
    )
    totp_period: int = Field(
        default=30,
        validation_alias="TOTP_PERIOD",
        description="TOTP time period in seconds"
    )
    totp_digits: int = Field(
        default=6,
        validation_alias="TOTP_DIGITS",
        description="TOTP code length (6 or 8)"
    )
    totp_time_window: int = Field(
        default=1,
        validation_alias="TOTP_TIME_WINDOW",
        description="TOTP time window tolerance (1 = ±30s for 30s period)"
    )
    backup_codes_count: int = Field(
        default=10,
        validation_alias="BACKUP_CODES_COUNT",
        description="Number of backup codes to generate"
    )

    # WebAuthn settings
    webauthn_rp_id: str = Field(
        default="localhost",
        validation_alias="WEBAUTHN_RP_ID",
        description="WebAuthn Relying Party ID (domain, e.g., 'example.com')"
    )
    webauthn_rp_name: str = Field(
        default="FastAPI App",
        validation_alias="WEBAUTHN_RP_NAME",
        description="WebAuthn Relying Party name (displayed to user)"
    )
    webauthn_origin: str = Field(
        default="http://localhost:3000",
        validation_alias="WEBAUTHN_ORIGIN",
        description="WebAuthn origin (frontend URL, must match exactly)"
    )
    webauthn_timeout: int = Field(
        default=60000,
        validation_alias="WEBAUTHN_TIMEOUT",
        description="WebAuthn challenge timeout in milliseconds"
    )

    # Token expiration settings
    two_factor_token_expires_minutes: int = Field(
        default=5,
        validation_alias="TWO_FACTOR_TOKEN_EXPIRES_MINUTES",
        description="2FA verification token expiration (used during login)"
    )
    setup_token_expires_minutes: int = Field(
        default=10,
        validation_alias="SETUP_TOKEN_EXPIRES_MINUTES",
        description="2FA setup token expiration (TOTP/WebAuthn registration)"
    )

    # Rate limiting settings (per-user)
    max_verification_attempts: int = Field(
        default=5,
        validation_alias="MAX_VERIFICATION_ATTEMPTS",
        description="Max 2FA verification attempts before lockout"
    )
    verification_lockout_minutes: int = Field(
        default=15,
        validation_alias="VERIFICATION_LOCKOUT_MINUTES",
        description="Lockout duration after max attempts"
    )

    # Encryption settings
    encryption_key: str | None = Field(
        default=None,
        validation_alias="TWO_FACTOR_ENCRYPTION_KEY",
        description="Dedicated encryption key for 2FA secrets (if not set, uses SECRET_KEY)"
    )

    @field_validator("totp_digits")
    @classmethod
    def validate_totp_digits(cls, v: int) -> int:
        """Validate TOTP digits is 6 or 8."""
        if v not in [6, 8]:
            raise ValueError("TOTP digits must be 6 or 8")
        return v

    @field_validator("webauthn_origin")
    @classmethod
    def validate_webauthn_origin(cls, v: str) -> str:
        """Validate WebAuthn origin is HTTPS in production."""
        # In production, WebAuthn requires HTTPS (except localhost)
        # This is a warning, not a hard error (dev environments use HTTP)
        if not v.startswith(("http://localhost", "http://127.0.0.1", "https://")):
            import warnings
            warnings.warn(
                f"WebAuthn origin '{v}' should use HTTPS in production. "
                "localhost/127.0.0.1 are allowed for development."
            )
        return v
```

### Environment variables (.env)

```bash
# ============================================
# Two-Factor Authentication (2FA) Settings
# ============================================

# TOTP Configuration
TOTP_ISSUER=My App Name
TOTP_ALGORITHM=SHA1
TOTP_PERIOD=30
TOTP_DIGITS=6
TOTP_TIME_WINDOW=1
BACKUP_CODES_COUNT=10

# WebAuthn/Passkeys Configuration
# IMPORTANT: WEBAUTHN_RP_ID must match your domain (no protocol, no port)
# Examples: "example.com", "api.example.com", "localhost"
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=My App Name
# IMPORTANT: WEBAUTHN_ORIGIN must match frontend URL exactly (with protocol and port)
WEBAUTHN_ORIGIN=http://localhost:3000
WEBAUTHN_TIMEOUT=60000

# Token Expiration
TWO_FACTOR_TOKEN_EXPIRES_MINUTES=5
SETUP_TOKEN_EXPIRES_MINUTES=10

# Rate Limiting (per-user)
MAX_VERIFICATION_ATTEMPTS=5
VERIFICATION_LOCKOUT_MINUTES=15

# Encryption (optional - uses SECRET_KEY if not set)
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
TWO_FACTOR_ENCRYPTION_KEY=your-secret-encryption-key-min-32-chars

# ============================================
# Production WebAuthn Configuration Example
# ============================================
# WEBAUTHN_RP_ID=example.com
# WEBAUTHN_RP_NAME=Example App
# WEBAUTHN_ORIGIN=https://example.com
```

---

## 📝 Registry Entry (`registry.json`)

```json
{
  "two_factor": {
    "name": "Two-Factor Authentication",
    "description": "TOTP and WebAuthn/Passkeys support for enhanced security. Includes backup codes, rate limiting, and audit logging.",
    "version": "1.0.0",
    "path": "example_project/app/modules/two_factor",
    "dependencies": [
      "pyotp>=2.9.0",
      "webauthn>=2.3.0",
      "cryptography>=41.0.0"
    ],
    "module_dependencies": ["auth"],
    "common_dependencies": [],
    "python_version": ">=3.12",
    "env": {
      "TOTP_ISSUER": "FastAPI App",
      "TOTP_ALGORITHM": "SHA1",
      "TOTP_PERIOD": "30",
      "TOTP_DIGITS": "6",
      "TOTP_TIME_WINDOW": "1",
      "BACKUP_CODES_COUNT": "10",
      "WEBAUTHN_RP_ID": "localhost",
      "WEBAUTHN_RP_NAME": "FastAPI App",
      "WEBAUTHN_ORIGIN": "http://localhost:3000",
      "WEBAUTHN_TIMEOUT": "60000",
      "TWO_FACTOR_TOKEN_EXPIRES_MINUTES": "5",
      "SETUP_TOKEN_EXPIRES_MINUTES": "10",
      "MAX_VERIFICATION_ATTEMPTS": "5",
      "VERIFICATION_LOCKOUT_MINUTES": "15",
      "TWO_FACTOR_ENCRYPTION_KEY": ""
    },
    "settings_class": "TwoFactorSettings",
    "router_prefix": "/two-factor",
    "tags": ["Two-Factor Authentication", "Security", "WebAuthn", "TOTP"],
    "author": "FastAPI Blocks Registry",
    "repository": "https://github.com/yourusername/fastapi-blocks-registry",
    "features": [
      "TOTP (Time-based One-Time Password) support",
      "WebAuthn/Passkeys support (YubiKey, Touch ID, Face ID, etc.)",
      "Backup codes (hashed, single-use)",
      "Per-user rate limiting and account lockout",
      "Encrypted TOTP secrets and WebAuthn keys",
      "Multiple 2FA methods per user",
      "Admin emergency recovery",
      "Audit logging integration",
      "Backward compatible with existing projects"
    ],
    "notes": "IMPORTANT: WebAuthn requires HTTPS in production (localhost exempt for dev). Update auth/dependencies.py to use AuthServiceWith2FA for 2FA integration. See README.md for integration guide."
  }
}
```

---

## 🎯 API Endpoints Summary

### TOTP Endpoints

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|------------|
| POST | `/two-factor/totp/initiate` | Rozpocznij konfigurację TOTP | Required | 3/minute |
| POST | `/two-factor/totp/verify` | Zweryfikuj i aktywuj TOTP | Required | 5/minute |
| GET | `/two-factor/totp/status` | Status TOTP | Required | 10/minute |
| POST | `/two-factor/totp/regenerate-backup-codes` | Wygeneruj nowe backup codes | Required | 3/minute |
| POST | `/two-factor/totp/disable` | Wyłącz TOTP | Required | 3/minute |
| POST | `/two-factor/totp/verify-login` | Zweryfikuj TOTP podczas logowania | Public | 5/minute + per-user |

### WebAuthn Endpoints

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|------------|
| POST | `/two-factor/webauthn/register/initiate` | Rozpocznij rejestrację passkey | Required | 5/minute |
| POST | `/two-factor/webauthn/register/complete` | Zakończ rejestrację passkey | Required | 5/minute |
| GET | `/two-factor/webauthn/passkeys` | Lista passkeys użytkownika | Required | 10/minute |
| PATCH | `/two-factor/webauthn/passkeys/{id}` | Zmień nazwę passkey | Required | 10/minute |
| DELETE | `/two-factor/webauthn/passkeys/{id}` | Usuń passkey | Required | 5/minute |
| POST | `/two-factor/webauthn/authenticate/initiate` | Rozpocznij autentykację passkey | Public | 10/minute |
| POST | `/two-factor/webauthn/authenticate/complete` | Zakończ autentykację passkey | Public | 5/minute + per-user |

### General Endpoints

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|------------|
| GET | `/two-factor/status` | Ogólny status 2FA (jakie metody są aktywne) | Required | 10/minute |
| GET | `/two-factor/methods` | Dostępne metody 2FA dla użytkownika | Required | 10/minute |

### Admin Endpoints (Optional)

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|------------|
| POST | `/admin/users/{user_id}/disable-2fa` | Admin emergency 2FA disable | Admin | 5/minute |
| GET | `/admin/users/{user_id}/2fa-status` | Get user's 2FA status | Admin | 10/minute |

---

## 🧪 Testing Strategy

### Unit Tests (Mock dependencies)

```python
# tests/unit/test_totp_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.modules.two_factor.service import TwoFactorService
from app.modules.two_factor.crypto_utils import generate_backup_codes

@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    repo = Mock()
    repo.get_totp_config = AsyncMock(return_value=None)
    repo.create_totp_config = AsyncMock()
    repo.update_totp_config = AsyncMock()
    return repo

@pytest.fixture
def two_factor_service(mock_repository):
    """Create TwoFactorService with mocked repository."""
    return TwoFactorService(repository=mock_repository)

@pytest.mark.asyncio
async def test_initiate_totp_setup(two_factor_service, mock_repository):
    """Test TOTP setup initiation."""
    user_id = "user123"
    email = "test@example.com"

    result = await two_factor_service.initiate_totp_setup(
        user_id=user_id,
        email=email
    )

    # Verify response structure
    assert "qrCodeUri" in result
    assert "secret" in result
    assert "backupCodes" in result
    assert "setupToken" in result
    assert "expiresAt" in result

    # Verify backup codes
    assert len(result["backupCodes"]) == 10
    assert all("-" in code for code in result["backupCodes"])

    # Verify QR code URI format
    assert result["qrCodeUri"].startswith("otpauth://totp/")
    assert email in result["qrCodeUri"]

    # Verify repository was NOT called yet (setup not complete)
    mock_repository.create_totp_config.assert_not_called()

@pytest.mark.asyncio
async def test_verify_totp_setup_success(two_factor_service, mock_repository):
    """Test successful TOTP setup verification."""
    import pyotp

    # Generate real TOTP secret and code
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Mock setup token
    setup_token = "mock_setup_token"

    with patch('app.modules.two_factor.service.verify_setup_token') as mock_verify:
        mock_verify.return_value = {
            "sub": "user123",
            "secret": secret,
            "backup_codes_hashed": ["hash1", "hash2"],
        }

        result = await two_factor_service.verify_totp_setup(
            setup_token=setup_token,
            code=code
        )

        # Verify success
        assert result["success"] is True
        assert "message" in result

        # Verify repository was called to save config
        mock_repository.create_totp_config.assert_called_once()

@pytest.mark.asyncio
async def test_verify_totp_login_invalid_code(two_factor_service, mock_repository):
    """Test TOTP login with invalid code."""
    from app.modules.two_factor.exceptions import InvalidTwoFactorCodeError

    # Mock TOTP config
    mock_repository.get_totp_config.return_value = Mock(
        secret="encrypted_secret",
        is_enabled=True
    )

    with patch('app.modules.two_factor.service.decrypt_secret') as mock_decrypt:
        mock_decrypt.return_value = pyotp.random_base32()

        with pytest.raises(InvalidTwoFactorCodeError):
            await two_factor_service.verify_totp_login(
                two_factor_token="mock_token",
                code="000000"  # Invalid code
            )

@pytest.mark.asyncio
async def test_backup_code_verification():
    """Test backup code generation and verification."""
    from app.modules.two_factor.crypto_utils import (
        generate_backup_codes,
        verify_backup_code,
        mark_backup_code_used
    )

    # Generate codes
    plain_codes, hashed_codes = generate_backup_codes(count=5)

    assert len(plain_codes) == 5
    assert len(hashed_codes) == 5

    # Verify valid code
    is_valid = verify_backup_code(
        code=plain_codes[0],
        hashed_codes=hashed_codes,
        used_codes=[]
    )
    assert is_valid is True

    # Mark as used
    used_codes = mark_backup_code_used(plain_codes[0], [])

    # Verify can't reuse
    is_valid = verify_backup_code(
        code=plain_codes[0],
        hashed_codes=hashed_codes,
        used_codes=used_codes
    )
    assert is_valid is False

    # Verify invalid code
    is_valid = verify_backup_code(
        code="INVALID-CODE-1234",
        hashed_codes=hashed_codes,
        used_codes=[]
    )
    assert is_valid is False
```

### Integration Tests (Real dependencies)

```python
# tests/integration/test_totp_flow.py
import pytest
import pyotp
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_user(client):
    """Create and authenticate a test user."""
    # Register
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "Test123!@#",
            "name": "Test User"
        }
    )
    assert register_response.status_code == 201

    # Login
    login_response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    assert login_response.status_code == 200

    data = login_response.json()
    return {
        "user": data["user"],
        "access_token": data["accessToken"],
        "refresh_token": data["refreshToken"]
    }

@pytest.mark.asyncio
async def test_full_totp_setup_and_login_flow(client, authenticated_user):
    """Test complete TOTP setup and login flow."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Initiate TOTP setup
    response = await client.post(
        "/two-factor/totp/initiate",
        headers=headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "qrCodeUri" in data
    assert "secret" in data
    assert "backupCodes" in data
    assert "setupToken" in data

    secret = data["secret"]
    setup_token = data["setupToken"]
    backup_codes = data["backupCodes"]

    # 2. Generate TOTP code
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # 3. Verify and complete setup
    response = await client.post(
        "/two-factor/totp/verify",
        headers=headers,
        json={
            "setupToken": setup_token,
            "code": code
        }
    )
    assert response.status_code == 200

    # 4. Check status
    response = await client.get(
        "/two-factor/totp/status",
        headers=headers
    )
    assert response.status_code == 200
    status = response.json()
    assert status["isEnabled"] is True
    assert status["isVerified"] is True

    # 5. Test login flow with 2FA
    response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["requiresTwoFactor"] is True
    assert "twoFactorToken" in data
    assert "totp" in data["methods"]

    two_factor_token = data["twoFactorToken"]

    # 6. Complete 2FA verification
    code = totp.now()
    response = await client.post(
        "/two-factor/totp/verify-login",
        json={
            "twoFactorToken": two_factor_token,
            "code": code
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data

    # 7. Test backup code login
    response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    two_factor_token = response.json()["twoFactorToken"]

    response = await client.post(
        "/two-factor/totp/verify-login",
        json={
            "twoFactorToken": two_factor_token,
            "code": backup_codes[0]  # Use first backup code
        }
    )
    assert response.status_code == 200

    # 8. Try to reuse backup code (should fail)
    response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    two_factor_token = response.json()["twoFactorToken"]

    response = await client.post(
        "/two-factor/totp/verify-login",
        json={
            "twoFactorToken": two_factor_token,
            "code": backup_codes[0]  # Same backup code
        }
    )
    assert response.status_code == 401  # Should fail

@pytest.mark.asyncio
async def test_rate_limiting_per_user(client, authenticated_user):
    """Test per-user rate limiting on 2FA verification."""
    # Setup 2FA first (abbreviated)
    access_token = authenticated_user["access_token"]
    # ... setup TOTP ...

    # Get 2FA token
    response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    two_factor_token = response.json()["twoFactorToken"]

    # Try invalid code 5 times
    for i in range(5):
        response = await client.post(
            "/two-factor/totp/verify-login",
            json={
                "twoFactorToken": two_factor_token,
                "code": "000000"  # Invalid
            }
        )
        assert response.status_code == 401

    # 6th attempt should be locked out
    response = await client.post(
        "/two-factor/totp/verify-login",
        json={
            "twoFactorToken": two_factor_token,
            "code": "000000"
        }
    )
    assert response.status_code == 429  # Too Many Requests
    assert "locked" in response.json()["detail"].lower()
```

### WebAuthn Tests (Mock browser API)

```python
# tests/unit/test_webauthn_utils.py
import pytest
from app.modules.two_factor.webauthn_utils import (
    create_registration_options,
    create_authentication_options,
)

def test_create_registration_options():
    """Test WebAuthn registration options generation."""
    options_json, challenge = create_registration_options(
        user_id="user123",
        user_email="test@example.com",
        user_name="Test User"
    )

    assert options_json is not None
    assert challenge is not None
    assert isinstance(options_json, dict)

    # Verify structure
    assert "rp" in options_json
    assert "user" in options_json
    assert "challenge" in options_json
    assert "pubKeyCredParams" in options_json

    # Verify RP info
    assert options_json["rp"]["id"] == "localhost"
    assert options_json["rp"]["name"] is not None

    # Verify user info
    assert options_json["user"]["name"] == "test@example.com"
    assert options_json["user"]["displayName"] == "Test User"

def test_create_authentication_options():
    """Test WebAuthn authentication options generation."""
    passkeys = [
        {"credential_id": "cred123", "transports": ["usb", "nfc"]},
        {"credential_id": "cred456", "transports": ["internal"]}
    ]

    options_json, challenge = create_authentication_options(passkeys)

    assert options_json is not None
    assert challenge is not None
    assert isinstance(options_json, dict)

    # Verify structure
    assert "challenge" in options_json
    assert "rpId" in options_json
    assert "allowCredentials" in options_json

    # Verify allowed credentials
    assert len(options_json["allowCredentials"]) == 2
```

---

## 📚 Database Migrations

### Przykładowa migracja Alembic

```python
# alembic/versions/001_add_two_factor_tables.py
"""Add two-factor authentication tables

Revision ID: 001_add_2fa
Revises: previous_revision
Create Date: 2025-01-05 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, UTC

# revision identifiers, used by Alembic.
revision = '001_add_2fa'
down_revision = 'previous_revision'  # Update to your last migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create two-factor authentication tables."""

    # Create totp_configs table
    op.create_table(
        'totp_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('secret', sa.Text, nullable=False, comment='Encrypted TOTP secret'),
        sa.Column('backup_codes', sa.Text, nullable=False, comment='JSON array of hashed backup codes'),
        sa.Column('backup_codes_used', sa.Text, nullable=True, comment='JSON array of used backup code hashes'),
        sa.Column('is_enabled', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts', sa.Integer, default=0, nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes for totp_configs
    op.create_index('ix_totp_configs_user_id', 'totp_configs', ['user_id'])
    op.create_index('ix_totp_configs_is_enabled', 'totp_configs', ['is_enabled'])

    # Create passkeys table
    op.create_table(
        'passkeys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('credential_id', sa.String(1024), nullable=False, unique=True, comment='Base64url-encoded credential ID'),
        sa.Column('public_key', sa.Text, nullable=False, comment='Encrypted public key'),
        sa.Column('counter', sa.Integer, default=0, nullable=False, comment='Signature counter for replay attack prevention'),
        sa.Column('aaguid', sa.String(36), nullable=True, comment='Authenticator AAGUID'),
        sa.Column('transports', sa.Text, nullable=True, comment='JSON array of transport types'),
        sa.Column('backup_eligible', sa.Boolean, default=False, nullable=False, comment='WebAuthn backup eligible flag'),
        sa.Column('backup_state', sa.Boolean, default=False, nullable=False, comment='WebAuthn backup state flag'),
        sa.Column('is_enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
    )

    # Indexes for passkeys
    op.create_index('ix_passkeys_user_id', 'passkeys', ['user_id'])
    op.create_index('ix_passkeys_credential_id', 'passkeys', ['credential_id'])
    op.create_index('ix_passkeys_is_enabled', 'passkeys', ['is_enabled'])

    print("✓ Two-factor authentication tables created successfully")


def downgrade() -> None:
    """Drop two-factor authentication tables."""
    op.drop_table('passkeys')
    op.drop_table('totp_configs')
    print("✓ Two-factor authentication tables dropped")
```

**Użycie:**
```bash
# Generate migration (if using auto-generate)
alembic revision --autogenerate -m "Add two-factor authentication tables"

# Run migration
alembic upgrade head

# Rollback (if needed)
alembic downgrade -1
```

---

## 🌐 Frontend Requirements

Ten moduł dostarcza **tylko backend API**. Frontend musi zaimplementować:

### 1. TOTP/Authenticator Setup Flow

**Komponenty potrzebne:**
- QR code generator (np. `qrcode.react` lub `qrcode.js`)
- Input dla 6-cyfrowego kodu TOTP
- Wyświetlanie backup codes z możliwością skopiowania/pobrania

**Przepływ:**
```typescript
// 1. Initiate setup
const response = await fetch('/two-factor/totp/initiate', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
const { qrCodeUri, secret, backupCodes, setupToken } = await response.json();

// 2. Generate QR code (frontend)
<QRCode value={qrCodeUri} size={256} />

// 3. Show backup codes (IMPORTANT: user must save these!)
<BackupCodesDisplay codes={backupCodes} />

// 4. Verify code from authenticator
const code = getUserInput(); // 6 digits
await fetch('/two-factor/totp/verify', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` },
  body: JSON.stringify({ setupToken, code })
});
```

### 2. WebAuthn/Passkey Registration

**Browser API wymagane:**
- `navigator.credentials.create()` - rejestracja passkey
- `navigator.credentials.get()` - autentykacja passkey

**Przepływ:**
```typescript
// 1. Check browser support
if (!window.PublicKeyCredential) {
  alert('WebAuthn not supported in this browser');
  return;
}

// 2. Initiate registration
const response = await fetch('/two-factor/webauthn/register/initiate', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` },
  body: JSON.stringify({ name: 'My iPhone' })
});
const { options, registrationToken } = await response.json();

// 3. Create credential (browser shows native UI)
const credential = await navigator.credentials.create({
  publicKey: options
});

// 4. Complete registration
await fetch('/two-factor/webauthn/register/complete', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` },
  body: JSON.stringify({
    registrationToken,
    credential: credentialToJSON(credential)
  })
});

// Helper function
function credentialToJSON(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64(credential.rawId),
    response: {
      clientDataJSON: arrayBufferToBase64(credential.response.clientDataJSON),
      attestationObject: arrayBufferToBase64(credential.response.attestationObject)
    },
    type: credential.type
  };
}
```

### 3. Login Flow z 2FA

**Logika:**
```typescript
// 1. Normal login
const response = await fetch('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});
const data = await response.json();

// 2. Check if 2FA required
if (data.requiresTwoFactor) {
  const { twoFactorToken, methods, preferredMethod } = data;

  // Show 2FA screen with available methods
  if (methods.includes('totp')) {
    // Show TOTP input
  }
  if (methods.includes('webauthn')) {
    // Show "Use security key" button
  }

  // 3a. TOTP verification
  const code = getUserInput();
  const verifyResponse = await fetch('/two-factor/totp/verify-login', {
    method: 'POST',
    body: JSON.stringify({ twoFactorToken, code })
  });

  // 3b. WebAuthn verification
  const authResponse = await fetch('/two-factor/webauthn/authenticate/initiate', {
    method: 'POST',
    body: JSON.stringify({ twoFactorToken })
  });
  const { options } = await authResponse.json();

  const credential = await navigator.credentials.get({
    publicKey: options
  });

  const completeResponse = await fetch('/two-factor/webauthn/authenticate/complete', {
    method: 'POST',
    body: JSON.stringify({
      twoFactorToken,
      credential: credentialToJSON(credential)
    })
  });

  // 4. Get tokens
  const { accessToken, refreshToken } = await completeResponse.json();
  // Store tokens and redirect
} else {
  // No 2FA, normal login
  const { accessToken, refreshToken } = data;
}
```

### 4. Requirements Checklist

- [ ] QR code library (qrcode.js, qrcode.react, etc.)
- [ ] 6-digit code input component (styled, auto-focus)
- [ ] Backup codes display (copy to clipboard, download as file)
- [ ] WebAuthn support detection
- [ ] WebAuthn error handling (user cancelled, timeout, not supported)
- [ ] 2FA status indicator in user settings
- [ ] Passkey management UI (list, rename, delete)
- [ ] "Remember this device" option (optional)
- [ ] HTTPS in production (WebAuthn requirement)

---

## 🚀 Plan implementacji (fazy)

### Faza 1: TOTP Basic (MVP) - Dzień 1-2

1. ✅ Struktura modułu (katalogi, __init__.py)
2. ✅ Crypto utilities (`crypto_utils.py`) - encryption, hashing, backup codes
3. ✅ TOTP utilities (`totp_utils.py`) - generate secret, verify code, provisioning URI
4. ✅ Database models (`db_models.py`) - TOTPConfigDB
5. ✅ Pydantic models (`models.py`) - TOTPConfig
6. ✅ Repository interface (`types/repository.py`)
7. ✅ Repository implementation (`repositories.py`) - TOTP CRUD
8. ✅ Exceptions (`exceptions.py`)
9. ✅ Service layer basic (`service.py`) - initiate setup, verify setup
10. ✅ Schemas (`schemas.py`) - Request/Response dla TOTP
11. ✅ Router endpoints (`router.py`) - initiate, verify, status
12. ✅ Tests basic (unit tests dla utilities)

### Faza 2: TOTP Complete - Dzień 3

1. ✅ Backup codes full implementation
2. ✅ Regenerate backup codes endpoint
3. ✅ Disable TOTP endpoint
4. ✅ Per-user rate limiting decorator
5. ✅ Apply rate limiting to endpoints
6. ✅ Error handling i validation
7. ✅ Integration tests dla TOTP flow
8. ✅ Documentation (docstrings)

### Faza 3: Auth Integration - Dzień 4

1. ✅ 2FA token utilities (create, verify)
2. ✅ `AuthServiceWith2FA` extension
3. ✅ `TwoFactorRequiredResponse` schema
4. ✅ Login flow z 2FA check
5. ✅ TOTP verify-login endpoint
6. ✅ Integration tests dla login flow
7. ✅ Backward compatibility check
8. ✅ Documentation update

### Faza 4: WebAuthn Basic - Dzień 5-6

1. ✅ WebAuthn utilities (`webauthn_utils.py`)
2. ✅ Database models dla passkeys (`db_models.py`)
3. ✅ Pydantic models dla passkeys (`models.py`)
4. ✅ Repository dla passkeys (CRUD)
5. ✅ Service layer (registration flow)
6. ✅ Schemas dla WebAuthn
7. ✅ Router endpoints (register/initiate, register/complete)
8. ✅ Unit tests dla WebAuthn utilities

### Faza 5: WebAuthn Complete - Dzień 7

1. ✅ Authentication flow (initiate, complete)
2. ✅ Counter verification (replay attack prevention)
3. ✅ Passkey management (list, rename, delete)
4. ✅ WebAuthn verify-login endpoint
5. ✅ Validation (can't delete last passkey)
6. ✅ Error handling
7. ✅ Integration tests

### Faza 6: Security & Polish - Dzień 8-9

1. ✅ Audit logging integration (logs module)
2. ✅ Admin recovery endpoint
3. ✅ Multiple methods support (TOTP + WebAuthn)
4. ✅ Preferred method tracking
5. ✅ Configuration class (`TwoFactorSettings`)
6. ✅ Environment variables documentation
7. ✅ Comprehensive error messages
8. ✅ Security review

### Faza 7: Testing & Documentation - Dzień 10

1. ✅ Complete unit test suite
2. ✅ Complete integration test suite
3. ✅ Rate limiting tests
4. ✅ Backup codes tests
5. ✅ WebAuthn flow tests
6. ✅ README.md
7. ✅ API documentation (OpenAPI)
8. ✅ Integration guide
9. ✅ Frontend requirements doc
10. ✅ Registry entry

### Faza 8: Database & Deployment - Dzień 11

1. ✅ Alembic migration scripts
2. ✅ Migration testing (upgrade/downgrade)
3. ✅ Database indexes verification
4. ✅ Performance testing
5. ✅ Production checklist
6. ✅ Security checklist
7. ✅ Release notes

---

## ✅ Pre-Implementation Checklist

Przed rozpoczęciem implementacji, upewnij się że:

### Decyzje

- [x] ✅ Backup codes: **HASHED** (jak hasła)
- [x] ✅ QR code generation: **Frontend** (backend zwraca URI)
- [x] ✅ WebAuthn library: **`webauthn`** (py_webauthn)
- [x] ✅ Encryption key: **Dedicated** (`TWO_FACTOR_ENCRYPTION_KEY`) z fallback
- [x] ✅ Rate limiting: **Global + per-user**
- [x] ✅ Error messages: **Ogólne** (szczegóły w logach)
- [x] ✅ Users table: **NO rozszerzenia** (używaj queries)
- [x] ✅ Auth integration: **Extended service** (`AuthServiceWith2FA`)
- [x] ✅ Multiple 2FA methods: **TAK** (user wybiera)
- [x] ✅ Recovery: **Admin + backup codes**

### Przygotowanie

- [ ] Zainstalować zależności: `pyotp`, `webauthn`, `cryptography`
- [ ] Przeczytać dokumentację WebAuthn (py_webauthn)
- [ ] Przygotować środowisko testowe z HTTPS (dla WebAuthn)
- [ ] Przygotować przykładowe frontend komponenty (dla testów)
- [ ] Skonfigurować Redis (jeśli używane do rate limiting)
- [ ] Przygotować plan migracji dla istniejących projektów

### Dokumentacja

- [ ] Przeczytać RFC 6238 (TOTP)
- [ ] Przeczytać WebAuthn Level 3 spec (podstawy)
- [ ] Zapoznać się z py_webauthn examples
- [ ] Zapoznać się z cryptography.Fernet docs

---

## 🔗 Przydatne zasoby

### Specyfikacje i standardy
- [RFC 6238 - TOTP: Time-Based One-Time Password Algorithm](https://tools.ietf.org/html/rfc6238)
- [WebAuthn Level 3 Specification](https://www.w3.org/TR/webauthn-3/)
- [FIDO2 Project](https://fidoalliance.org/fido2/)

### Biblioteki
- [pyotp Documentation](https://github.com/pyotp/pyotp)
- [py_webauthn Documentation](https://github.com/duo-labs/py_webauthn)
- [Cryptography Documentation](https://cryptography.io/)

### Przykłady i tutoriale
- [WebAuthn.io Demo](https://webauthn.io/) - Test WebAuthn in browser
- [WebAuthn Guide](https://webauthn.guide/) - Excellent visual guide
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

### Testowanie
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [HTTPX Async Client](https://www.python-httpx.org/async/)

---

## 📋 Podsumowanie zmian w wersji 2.0

1. **Backup codes:** Zmienione z encryption na **hashing** (jak hasła)
2. **Database schema:** Dodane pola: `backup_codes_used`, `failed_attempts`, `locked_until`, `aaguid`, `transports`, `backup_eligible`, `backup_state`, `user_agent`
3. **Rate limiting:** Dodany **per-user rate limiting** oprócz globalnego
4. **Security:** Szczegółowa implementacja crypto_utils (encryption, hashing)
5. **Auth integration:** Strategia **Extended Service** (backward compatible)
6. **Audit logging:** Integracja z modułem `logs`
7. **Admin recovery:** Nowy endpoint dla emergency disable
8. **Testing:** Konkretne przykłady unit i integration testów
9. **Migrations:** Przykładowa migracja Alembic
10. **Frontend requirements:** Szczegółowe wymagania i przykłady
11. **Configuration:** Kompletna klasa `TwoFactorSettings`
12. **WebAuthn:** Dodane pola dla lepszego tracking (aaguid, transports, backup state)
13. **Error handling:** Ogólne komunikaty + szczegółowe logi
14. **Documentation:** Znacznie rozszerzona, gotowa do implementacji

---

**Data utworzenia:** 2025-01-05
**Ostatnia aktualizacja:** 2025-01-05 (wersja 2.0)
**Status:** ✅ **Gotowy do implementacji**
**Reviewer:** Human + Claude Code

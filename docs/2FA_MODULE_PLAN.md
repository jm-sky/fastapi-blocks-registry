# Plan implementacji modułu 2FA (Two-Factor Authentication)

## 📋 Przegląd

Ten dokument zawiera plan implementacji modułu 2FA dla FastAPI Blocks Registry. Moduł będzie wspierał dwa typy weryfikacji dwuskładnikowej:
1. **TOTP (Time-based One-Time Password)** - aplikacje autentykacyjne (Google Authenticator, Authy, etc.)
2. **WebAuthn/Passkeys** - klucze bezpieczeństwa (YubiKey, Touch ID, Face ID, Windows Hello, etc.)

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
- **Models** - Pydantic models dla API (`models.py`)
- **DB Models** - SQLAlchemy ORM (`db_models.py`)
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
├── dependencies.py             # FastAPI dependencies (2FA checks)
├── models.py                    # Pydantic models (TOTPConfig, Passkey)
├── db_models.py                 # SQLAlchemy models (totp_configs, passkeys tables)
├── schemas.py                   # Request/Response schemas
├── repositories.py              # Database repository implementation
├── types/
│   ├── __init__.py
│   └── repository.py           # Repository interface
├── totp_utils.py                # TOTP generation/verification utilities
├── webauthn_utils.py            # WebAuthn utilities (registration/authentication)
├── exceptions.py                 # Custom exceptions
├── decorators.py                # Rate limiting decorators
└── README.md                    # Documentation
```

### Struktura bazy danych

#### Tabela `totp_configs`
```python
- id: str (ULID/UUID, primary key)
- user_id: str (foreign key -> users.id)
- secret: str (encrypted TOTP secret)
- backup_codes: str (encrypted JSON array of backup codes)
- is_enabled: bool (default: False)
- created_at: datetime
- verified_at: datetime | None (null until user verifies setup)
```

#### Tabela `passkeys`
```python
- id: str (ULID/UUID, primary key)
- user_id: str (foreign key -> users.id)
- name: str (user-given name, e.g., "MacBook Pro", "iPhone 14")
- credential_id: str (unique, indexed)
- public_key: str (encrypted)
- counter: int (for replay attack prevention)
- is_enabled: bool (default: True)
- created_at: datetime
- last_used_at: datetime | None
```

#### Rozszerzenie tabeli `users` (opcjonalne)
Możemy dodać pola do istniejącej tabeli `users`:
```python
- two_factor_enabled: bool (default: False)
- two_factor_method: str | None (None, "totp", "webauthn", "both")
```

**Uwaga:** To wymaga migracji Alembic. Alternatywnie, możemy sprawdzać czy istnieją rekordy w `totp_configs` lub `passkeys`.

---

## 🔐 Funkcjonalności TOTP

### Przepływ konfiguracji TOTP

1. **Initiate TOTP Setup** (`POST /two-factor/totp/initiate`)
   - Generuje secret
   - Zwraca QR code data URL (lub raw data do wygenerowania QR po stronie frontendu)
   - Zwraca backup codes (w plain text - tylko raz!)
   - Zwraca setup verification token (tymczasowy, 10 min expiration)

2. **Verify TOTP Setup** (`POST /two-factor/totp/verify`)
   - Użytkownik wprowadza kod z aplikacji autentykacyjnej
   - Weryfikuje kod TOTP
   - Jeśli poprawny - zapisuje konfigurację jako `is_enabled=True`
   - Inwaliduje setup verification token

3. **List Backup Codes** (`GET /two-factor/totp/backup-codes`)
   - Zwraca zaszyfrowane backup codes (tylko jeśli użytkownik je jeszcze nie widział)
   - Albo wymaga ponownego wprowadzenia hasła do odszyfrowania

4. **Regenerate Backup Codes** (`POST /two-factor/totp/regenerate-backup-codes`)
   - Generuje nowe backup codes
   - Inwaliduje stare
   - Wymaga potwierdzenia hasłem lub TOTP

5. **Disable TOTP** (`POST /two-factor/totp/disable`)
   - Wyłącza TOTP dla użytkownika
   - Wymaga potwierdzenia hasłem lub jednym z backup codes

### Przepływ logowania z TOTP

1. **Login Request** (`POST /auth/login`)
   - Standardowy login
   - Jeśli użytkownik ma TOTP enabled:
     - Zwraca `requiresTwoFactor: true`
     - Zwraca `twoFactorToken` (tymczasowy, 5 min expiration)
     - Frontend przechodzi do ekranu wprowadzania kodu TOTP

2. **Verify TOTP on Login** (`POST /two-factor/totp/verify-login`)
   - Przyjmuje `twoFactorToken` i kod TOTP
   - Weryfikuje kod
   - Jeśli poprawny - zwraca normalne JWT tokens (access + refresh)

### Schemas TOTP

```python
# Request schemas
class InitiateTotpRequest(BaseModel):
    pass  # No input needed

class VerifyTotpSetupRequest(BaseModel):
    setupToken: str  # From initiate response
    code: str  # 6-digit TOTP code

class VerifyTotpLoginRequest(BaseModel):
    twoFactorToken: str  # From login response
    code: str  # 6-digit TOTP code or backup code

class RegenerateBackupCodesRequest(BaseModel):
    password: str  # For security

class DisableTotpRequest(BaseModel):
    password: str  # Or backup code
    code: str | None  # Optional: current TOTP code

# Response schemas
class TotpInitiateResponse(BaseModel):
    qrCodeUrl: str  # Data URL with QR code
    secret: str  # Plain secret (for manual entry)
    backupCodes: list[str]  # Plain backup codes (only shown once!)
    setupToken: str  # For verification step
    expiresAt: datetime

class TotpStatusResponse(BaseModel):
    isEnabled: bool
    isVerified: bool  # Has user completed setup?
    createdAt: datetime | None
    verifiedAt: datetime | None

class BackupCodesResponse(BaseModel):
    codes: list[str]  # Encrypted or plain? (security question)
    expiresAt: datetime | None  # If time-limited
```

---

## 🔑 Funkcjonalności WebAuthn/Passkeys

### Przepływ rejestracji Passkey

1. **Initiate Passkey Registration** (`POST /two-factor/webauthn/register/initiate`)
   - Przyjmuje `name` (opcjonalne, może być generowane)
   - Generuje WebAuthn challenge
   - Zwraca `PublicKeyCredentialCreationOptions` (JSON)
   - Zwraca `registrationToken` (tymczasowy, 10 min expiration)

2. **Complete Passkey Registration** (`POST /two-factor/webauthn/register/complete`)
   - Przyjmuje `registrationToken` i `credential` (z frontendu WebAuthn API)
   - Weryfikuje credential
   - Zapisuje passkey do bazy danych
   - Zwraca informacje o zarejestrowanym passkey

### Przepływ autentykacji Passkey

1. **Initiate Passkey Authentication** (`POST /two-factor/webauthn/authenticate/initiate`)
   - Przyjmuje `twoFactorToken` (z login response)
   - Pobiera wszystkie passkeys użytkownika
   - Generuje WebAuthn challenge
   - Zwraca `PublicKeyCredentialRequestOptions` (JSON)

2. **Complete Passkey Authentication** (`POST /two-factor/webauthn/authenticate/complete`)
   - Przyjmuje `twoFactorToken` i `credential` (z frontendu WebAuthn API)
   - Weryfikuje credential i counter (replay attack prevention)
   - Aktualizuje `last_used_at` i `counter`
   - Zwraca normalne JWT tokens (access + refresh)

### Zarządzanie Passkeys

1. **List Passkeys** (`GET /two-factor/webauthn/passkeys`)
   - Zwraca listę wszystkich passkeys użytkownika
   - Z nazwami, datami utworzenia, ostatniego użycia

2. **Rename Passkey** (`PATCH /two-factor/webauthn/passkeys/{passkey_id}`)
   - Zmienia nazwę passkey

3. **Delete Passkey** (`DELETE /two-factor/webauthn/passkeys/{passkey_id}`)
   - Usuwa passkey
   - Wymaga potwierdzenia hasłem lub innym passkeyem
   - Nie można usunąć ostatniego passkeya (jeśli to jedyna metoda 2FA)

### Schemas WebAuthn

```python
# Request schemas
class InitiatePasskeyRegistrationRequest(BaseModel):
    name: str | None = None  # Optional friendly name

class CompletePasskeyRegistrationRequest(BaseModel):
    registrationToken: str
    credential: dict  # PublicKeyCredential from WebAuthn API
    name: str | None  # Optional name override

class InitiatePasskeyAuthRequest(BaseModel):
    twoFactorToken: str

class CompletePasskeyAuthRequest(BaseModel):
    twoFactorToken: str
    credential: dict  # PublicKeyCredential from WebAuthn API

class UpdatePasskeyRequest(BaseModel):
    name: str

class DeletePasskeyRequest(BaseModel):
    password: str  # Or other passkey

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

class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyResponse]
```

---

## 🔄 Integracja z modułem `auth`

### Modyfikacje w `auth/service.py`

**Login flow z 2FA:**
```python
async def login_user(self, email: str, password: str) -> LoginResponse | TwoFactorRequiredResponse:
    # ... existing password verification ...
    
    # Check if user has 2FA enabled
    has_2fa = await two_factor_service.has_two_factor_enabled(user.id)
    
    if has_2fa:
        # Generate temporary 2FA token
        two_factor_token = create_two_factor_token(data={"sub": user.id})
        return TwoFactorRequiredResponse(
            twoFactorToken=two_factor_token,
            methods=await two_factor_service.get_available_methods(user.id)  # ["totp", "webauthn"]
        )
    
    # Normal login flow...
```

### Nowe schemas w `auth/schemas.py`

```python
class TwoFactorRequiredResponse(BaseModel):
    requiresTwoFactor: bool = True
    twoFactorToken: str
    methods: list[str]  # ["totp", "webauthn"]
    expiresAt: datetime
```

### Modyfikacje w `auth/router.py`

Endpoint `/auth/login` może zwracać `LoginResponse` lub `TwoFactorRequiredResponse` (union type).

---

## 🛡️ Security Considerations

### TOTP Security
- **Secret encryption**: TOTP secrets powinny być szyfrowane w bazie danych (użyć `settings.security.secret_key` jako encryption key)
- **Backup codes**: Szyfrowane, jednorazowe użycie, możliwość regeneracji
- **Rate limiting**: Ograniczenie prób weryfikacji (np. 5 prób na 15 minut)
- **Setup token expiration**: Krótki czas życia (10 minut)
- **Verification before enable**: Użytkownik musi zweryfikować kod przed aktywacją

### WebAuthn Security
- **Counter**: Zapobieganie replay attacks
- **Challenge verification**: Każdy challenge używany tylko raz
- **Origin verification**: Weryfikacja origin w credential
- **RP ID verification**: Weryfikacja Relying Party ID
- **Credential storage**: Public keys szyfrowane w bazie
- **Rate limiting**: Ograniczenie prób rejestracji/autentykacji

### General Security
- **Session management**: 2FA tokens krótkotrwałe (5-10 minut)
- **Audit logging**: Logowanie wszystkich akcji 2FA (przez moduł `logs`)
- **Recovery**: Backup codes dla TOTP, możliwość wyłączenia przez admina (emergency)
- **Multiple methods**: Użytkownik może mieć TOTP + wiele passkeys jednocześnie

---

## 📦 Dependencies

### Python packages
```python
# TOTP
"pyotp>=2.9.0"  # TOTP generation/verification
"qrcode[pil]>=7.4.2"  # QR code generation (optional, może być po stronie frontendu)

# WebAuthn
"webauthn>=2.3.0"  # WebAuthn protocol implementation
# LUB
"fido2>=1.1.1"  # Alternative WebAuthn library

# Encryption (jeśli nie używamy istniejących utils)
# Możemy użyć cryptography z FastAPI/utils
```

### Database
- Wymaga migracji Alembic dla nowych tabel
- Foreign keys do tabeli `users`

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
        description="TOTP hashing algorithm"
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
    backup_codes_count: int = Field(
        default=10,
        validation_alias="BACKUP_CODES_COUNT",
        description="Number of backup codes to generate"
    )
    
    # WebAuthn settings
    webauthn_rp_id: str = Field(
        default="localhost",
        validation_alias="WEBAUTHN_RP_ID",
        description="WebAuthn Relying Party ID (domain)"
    )
    webauthn_rp_name: str = Field(
        default="FastAPI App",
        validation_alias="WEBAUTHN_RP_NAME",
        description="WebAuthn Relying Party name"
    )
    webauthn_origin: str = Field(
        default="http://localhost:3000",
        validation_alias="WEBAUTHN_ORIGIN",
        description="WebAuthn origin (frontend URL)"
    )
    webauthn_timeout: int = Field(
        default=60000,
        validation_alias="WEBAUTHN_TIMEOUT",
        description="WebAuthn challenge timeout in milliseconds"
    )
    
    # Security settings
    two_factor_token_expires_minutes: int = Field(
        default=10,
        validation_alias="TWO_FACTOR_TOKEN_EXPIRES_MINUTES",
        description="2FA verification token expiration"
    )
    setup_token_expires_minutes: int = Field(
        default=10,
        validation_alias="SETUP_TOKEN_EXPIRES_MINUTES",
        description="2FA setup token expiration"
    )
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
```

### Environment variables (.env)
```bash
# TOTP
TOTP_ISSUER=My App Name
TOTP_ALGORITHM=SHA1
TOTP_PERIOD=30
TOTP_DIGITS=6
BACKUP_CODES_COUNT=10

# WebAuthn
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=My App Name
WEBAUTHN_ORIGIN=http://localhost:3000
WEBAUTHN_TIMEOUT=60000

# Security
TWO_FACTOR_TOKEN_EXPIRES_MINUTES=10
SETUP_TOKEN_EXPIRES_MINUTES=10
MAX_VERIFICATION_ATTEMPTS=5
VERIFICATION_LOCKOUT_MINUTES=15
```

---

## 📝 Registry Entry (`registry.json`)

```json
{
  "two_factor": {
    "name": "Two-Factor Authentication",
    "description": "TOTP and WebAuthn/Passkeys support for enhanced security",
    "version": "1.0.0",
    "path": "example_project/app/modules/two_factor",
    "dependencies": [
      "pyotp>=2.9.0",
      "qrcode[pil]>=7.4.2",
      "webauthn>=2.3.0",
      "cryptography>=41.0.0"
    ],
    "module_dependencies": ["auth"],
    "python_version": ">=3.12",
    "env": {
      "TOTP_ISSUER": "FastAPI App",
      "TOTP_ALGORITHM": "SHA1",
      "TOTP_PERIOD": "30",
      "TOTP_DIGITS": "6",
      "BACKUP_CODES_COUNT": "10",
      "WEBAUTHN_RP_ID": "localhost",
      "WEBAUTHN_RP_NAME": "FastAPI App",
      "WEBAUTHN_ORIGIN": "http://localhost:3000",
      "WEBAUTHN_TIMEOUT": "60000",
      "TWO_FACTOR_TOKEN_EXPIRES_MINUTES": "10",
      "SETUP_TOKEN_EXPIRES_MINUTES": "10",
      "MAX_VERIFICATION_ATTEMPTS": "5",
      "VERIFICATION_LOCKOUT_MINUTES": "15"
    },
    "settings_class": "TwoFactorSettings",
    "router_prefix": "/two-factor",
    "tags": ["Two-Factor Authentication", "Security"],
    "author": "FastAPI Blocks Registry",
    "repository": "https://github.com/yourusername/fastapi-blocks-registry"
  }
}
```

---

## 🎯 API Endpoints Summary

### TOTP Endpoints
- `POST /two-factor/totp/initiate` - Rozpocznij konfigurację TOTP
- `POST /two-factor/totp/verify` - Zweryfikuj i aktywuj TOTP
- `GET /two-factor/totp/status` - Status TOTP
- `GET /two-factor/totp/backup-codes` - Pobierz backup codes (wymaga hasła)
- `POST /two-factor/totp/regenerate-backup-codes` - Wygeneruj nowe backup codes
- `POST /two-factor/totp/disable` - Wyłącz TOTP
- `POST /two-factor/totp/verify-login` - Zweryfikuj TOTP podczas logowania

### WebAuthn Endpoints
- `POST /two-factor/webauthn/register/initiate` - Rozpocznij rejestrację passkey
- `POST /two-factor/webauthn/register/complete` - Zakończ rejestrację passkey
- `GET /two-factor/webauthn/passkeys` - Lista passkeys użytkownika
- `PATCH /two-factor/webauthn/passkeys/{id}` - Zmień nazwę passkey
- `DELETE /two-factor/webauthn/passkeys/{id}` - Usuń passkey
- `POST /two-factor/webauthn/authenticate/initiate` - Rozpocznij autentykację passkey
- `POST /two-factor/webauthn/authenticate/complete` - Zakończ autentykację passkey

### General Endpoints
- `GET /two-factor/status` - Ogólny status 2FA (jakie metody są aktywne)
- `GET /two-factor/methods` - Dostępne metody 2FA dla użytkownika

---

## ❓ Pytania i wątpliwości do rozwiązania

### 1. Struktura danych i relacje
- **Pytanie**: Czy rozszerzać tabelę `users` o pola `two_factor_enabled` i `two_factor_method`, czy sprawdzać istnienie rekordów w `totp_configs`/`passkeys`?
- **Rekomendacja**: Sprawdzanie rekordów jest bardziej elastyczne (można mieć wiele passkeys), ale dodanie pól do `users` jest szybsze w query. Proponuję **oba podejścia** - pola w `users` jako cache/flag, ale źródłem prawdy są tabele 2FA.

### 2. Szyfrowanie danych wrażliwych
- **Pytanie**: Jak szyfrować TOTP secrets i backup codes? Użyć `settings.security.secret_key` czy osobny encryption key?
- **Rekomendacja**: Użyć osobnego klucza szyfrowania (np. `TWO_FACTOR_ENCRYPTION_KEY`) dla lepszej separacji. Jeśli nie podano - fallback do `secret_key`.

### 3. Backup codes storage
- **Pytanie**: Jak przechowywać backup codes? Hashed (jak hasła) czy encrypted (możliwość odszyfrowania)?
- **Rekomendacja**: **Encrypted** - użytkownik może je zobaczyć ponownie po wprowadzeniu hasła. Alternatywnie: hashed + jednorazowe użycie + możliwość regeneracji.

### 4. QR code generation
- **Pytanie**: Generować QR code po stronie backendu czy przekazać raw data do frontendu?
- **Rekomendacja**: **Raw data** (URI string) - frontend może użyć biblioteki do generowania QR. Mniej zależności po stronie backendu.

### 5. WebAuthn library choice
- **Pytanie**: Którą bibliotekę użyć - `webauthn` czy `fido2`?
- **Rekomendacja**: `webauthn` (py_webauthn) - bardziej popularna, lepsza dokumentacja, aktywna społeczność.

### 6. Rate limiting
- **Pytanie**: Czy używać istniejących dekoratorów `@rate_limit` czy osobne limity dla 2FA?
- **Rekomendacja**: Użyć istniejących dekoratorów, ale z bardziej restrykcyjnymi limitami dla endpointów 2FA (np. 3/minute dla weryfikacji).

### 7. Error handling
- **Pytanie**: Jakie szczegółowe błędy zwracać? "Invalid code" czy bardziej ogólne "Verification failed"?
- **Rekomendacja**: **Ogólne komunikaty** - nie ujawniać szczegółów (zapobieganie enumeration attacks). Szczegóły w logach.

### 8. Frontend integration
- **Pytanie**: Czy moduł powinien zawierać przykładowe strony frontendowe?
- **Uwaga**: Plan dotyczy backendu. Frontend będzie osobnym modułem w registry frontendowym (Vue). Backend powinien zwracać wszystkie potrzebne dane (QR data, WebAuthn options, etc.).

### 9. Migration strategy
- **Pytanie**: Jak obsłużyć migrację dla istniejących projektów? Czy moduł powinien automatycznie tworzyć tabele?
- **Rekomendacja**: **Alembic migrations** - standardowy sposób. Moduł powinien zawierać przykładowe migracje w dokumentacji.

### 10. Multiple 2FA methods
- **Pytanie**: Czy użytkownik może mieć włączone TOTP i WebAuthn jednocześnie? Jeśli tak, która metoda jest wymagana podczas logowania?
- **Rekomendacja**: **Tak, można mieć obie**. Podczas logowania użytkownik wybiera metodę (frontend pokazuje dostępne opcje). Jeśli tylko jedna - automatycznie użyta.

### 11. Recovery flow
- **Pytanie**: Co jeśli użytkownik straci dostęp do 2FA (zgubione urządzenie, bez backup codes)?
- **Rekomendacja**: **Admin recovery** - admin może wyłączyć 2FA dla użytkownika. Alternatywnie: email recovery link (wymaga dodatkowego modułu email).

### 12. Testing strategy
- **Pytanie**: Jak testować TOTP i WebAuthn? Mock libraries czy rzeczywiste wywołania?
- **Rekomendacja**: **Mock libraries** dla unit tests, **rzeczywiste wywołania** dla integration tests (z testowym authenticatorem/device).

---

## 📚 Dokumentacja i przykłady

### README.md powinien zawierać:
1. Przegląd funkcjonalności
2. Instalacja i konfiguracja
3. Przykłady użycia API
4. Przykłady integracji z frontendem
5. Troubleshooting
6. Security best practices

### Przykładowe użycie w kodzie:
```python
# W przykładzie projektu (example_project)
# Przykład użycia w innej części aplikacji
from app.modules.two_factor.dependencies import require_two_factor
from app.modules.auth.dependencies import CurrentUser

@router.post("/sensitive-action")
async def sensitive_action(
    current_user: CurrentUser,
    two_factor_verified: bool = Depends(require_two_factor)
):
    # This endpoint requires 2FA verification
    pass
```

---

## 🚀 Plan implementacji (fazy)

### Faza 1: TOTP Basic (MVP)
1. ✅ Struktura modułu
2. ✅ TOTP utilities (`totp_utils.py`)
3. ✅ Database models (`db_models.py`)
4. ✅ Repository interface i implementacja
5. ✅ Service layer (basic)
6. ✅ Router endpoints (initiate, verify, status)
7. ✅ Integracja z auth/login flow
8. ✅ Tests (basic)

### Faza 2: TOTP Complete
1. ✅ Backup codes
2. ✅ Regenerate backup codes
3. ✅ Disable TOTP
4. ✅ Rate limiting i security
5. ✅ Error handling
6. ✅ Documentation

### Faza 3: WebAuthn Basic
1. ✅ WebAuthn utilities (`webauthn_utils.py`)
2. ✅ Database models dla passkeys
3. ✅ Repository dla passkeys
4. ✅ Service layer (registration flow)
5. ✅ Router endpoints (register/initiate, register/complete)
6. ✅ Tests

### Faza 4: WebAuthn Complete
1. ✅ Authentication flow
2. ✅ Passkey management (list, rename, delete)
3. ✅ Security (counter, challenge verification)
4. ✅ Rate limiting
5. ✅ Error handling
6. ✅ Documentation

### Faza 5: Integration & Polish
1. ✅ Integracja z auth module (complete)
2. ✅ Multiple methods support
3. ✅ Admin recovery (opcjonalnie)
4. ✅ Audit logging integration
5. ✅ Comprehensive tests
6. ✅ Final documentation
7. ✅ Registry entry

---

## 📋 Checklist przed rozpoczęciem implementacji

- [ ] Ustalić odpowiedzi na pytania z sekcji "Pytania i wątpliwości"
- [ ] Zdecydować o bibliotece WebAuthn (`webauthn` vs `fido2`)
- [ ] Zdecydować o strategii szyfrowania
- [ ] Zdecydować o strategii backup codes
- [ ] Zaprojektować dokładne API contracts (OpenAPI schemas)
- [ ] Zaprojektować flow dla edge cases (loss of device, etc.)
- [ ] Zaplanować testy (unit, integration, e2e)
- [ ] Zaplanować migracje Alembic

---

## 🔗 Przydatne zasoby

- [TOTP RFC 6238](https://tools.ietf.org/html/rfc6238)
- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [pyotp Documentation](https://github.com/pyotp/pyotp)
- [py_webauthn Documentation](https://github.com/duo-labs/py_webauthn)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

---

**Data utworzenia:** 2025-01-XX  
**Ostatnia aktualizacja:** 2025-01-XX  
**Status:** Plan do review

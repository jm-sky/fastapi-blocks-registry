# JWT Token Flow and State Management

## 📋 Przegląd

Ten dokument opisuje przepływ tokenów JWT w systemie, wszystkie możliwe stany tokenów oraz interfejs payload zgodny z frontendem.

**Ostatnia aktualizacja:** 2025-01-05  
**Status:** W trakcie uzgodnień backend-frontend

---

## 🔗 Powiązane dokumenty

- **[JWT_COMPATIBILITY_ANALYSIS.md](./JWT_COMPATIBILITY_ANALYSIS.md)** - Szczegółowa analiza obecnego kodu Python i wymaganych zmian
- [2FA_MODULE_PLAN.md](./2FA_MODULE_PLAN.md) - Szczegóły implementacji modułu 2FA
- [BACKEND_ROADMAP.md](./BACKEND_ROADMAP.md) - Roadmap backendu
- [FRONTEND_ROADMAP.md](./FRONTEND_ROADMAP.md) - Roadmap frontendu

---

## 🎯 Unified JWT Payload Structure

### Frontend Interface (TypeScript)

```typescript
export type JWTTwoFactorMethod = 'totp' | 'webauthn'

export interface JWTPayloadOptions {
  email: string
  tid?: string
  trol?: string
  tfaPending?: boolean
  tfaVerified?: boolean
  tfaMethod?: JWTTwoFactorMethod | null
}

export interface JWTPayload {
  sub: string    // Subject (User ID)
  email: string  // User Email
  tid?: string   // Tenant ID
  trol?: string  // Tenant Role
  iat: number    // Issued At
  exp: number    // Expiration
  aud?: string   // Audience
  tfaPending?: boolean
  tfaVerified?: boolean
  tfaMethod?: JWTTwoFactorMethod | null
}
```

### Backend Interface (Python TypedDict)

**Lokalizacja:** `app/modules/auth/types/jwt.py` (rozszerzona)

```python
class JWTPayload(TypedDict, total=False):
    """Unified JWT token payload structure.
    
    Attributes:
        sub: Subject (User ID)
        email: User email address
        tid: Tenant ID (optional, multi-tenant support)
        trol: Tenant Role (optional, role within tenant)
        iat: Issued at (Unix timestamp)
        exp: Expiration time (Unix timestamp)
        aud: Audience (optional, token audience)
        tfaPending: Whether 2FA verification is required (optional)
        tfaVerified: Whether 2FA has been verified (optional)
        tfaMethod: 2FA method used - 'totp' or 'webauthn' (optional)
        type: Token type - 'access', 'refresh', '2fa_verification', etc.
    """
    sub: str
    email: str
    tid: str | None
    trol: str | None
    iat: int
    exp: int
    aud: str | None
    tfaPending: bool | None
    tfaVerified: bool | None
    tfaMethod: str | None  # 'totp' | 'webauthn'
    type: str  # 'access' | 'refresh' | '2fa_verification' | '2fa_setup' | 'passkey_registration'
```

---

## 🔄 Możliwe stany JWT Token

### 1. Użytkownik zalogowany, bez tenant, bez 2FA

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "iat": 1704460800,
  "exp": 1704462600,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": false,
  "tfaMethod": null
}
```

**Kiedy:**
- Użytkownik zalogował się bez 2FA
- Nie wybrał jeszcze tenant (jeśli system wspiera multi-tenant)
- Pełny dostęp do aplikacji

**Flow:**
```
Login → Password verification → JWT access token (bez 2FA) → Frontend
```

---

### 2. Użytkownik zalogowany, wybrał tenant, bez 2FA

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "tid": "tenant_456",
  "trol": "admin",
  "iat": 1704460800,
  "exp": 1704462600,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": false,
  "tfaMethod": null
}
```

**Kiedy:**
- Użytkownik zalogowany bez 2FA
- Wybrał tenant z dostępnych tenantów
- Ma przypisaną rolę w tenant (`trol`)

**Flow:**
```
Login → Password verification → JWT access token → Wybór tenant → 
Update token z tid/trol → Frontend
```

**Endpoint:** `POST /api/tenants/{tenant_id}/select` (do implementacji)

---

### 3. Użytkownik zalogowany, czeka na weryfikację 2FA (`tfaPending: true`)

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "iat": 1704460800,
  "exp": 1704461000,
  "type": "2fa_verification",
  "tfaPending": true,
  "tfaVerified": false,
  "tfaMethod": null
}
```

**Kiedy:**
- Użytkownik ma włączone 2FA
- Wprowadził poprawne hasło
- Czeka na weryfikację kodu TOTP lub passkey

**Flow:**
```
Login → Password verification → 
System wykrywa 2FA enabled → 
Zwraca TwoFactorRequiredResponse z twoFactorToken → 
Frontend pokazuje ekran 2FA → 
User wprowadza kod → 
POST /two-factor/totp/verify-login → 
JWT access token (tfaVerified: true)
```

**Uwaga:** Ten token jest krótkotrwały (5 min) i służy tylko do weryfikacji 2FA. Nie można używać go do normalnych requestów API.

---

### 4. Użytkownik zalogowany, 2FA zweryfikowane, bez tenant

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "iat": 1704460800,
  "exp": 1704462600,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "totp"
}
```

**Kiedy:**
- Użytkownik pomyślnie zweryfikował 2FA
- Ma pełny dostęp do aplikacji
- Nie wybrał jeszcze tenant

**Flow:**
```
Login → Password → 2FA verification → 
JWT access token (tfaVerified: true, tfaMethod: 'totp'|'webauthn') → 
Frontend
```

---

### 5. Użytkownik zalogowany, 2FA zweryfikowane, wybrał tenant

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "tid": "tenant_456",
  "trol": "member",
  "iat": 1704460800,
  "exp": 1704462600,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "webauthn"
}
```

**Kiedy:**
- Użytkownik zweryfikował 2FA
- Wybrał tenant
- Ma pełny dostęp z kontekstem tenant

**Flow:**
```
Login → Password → 2FA verification → 
JWT access token (tfaVerified: true) → 
Wybór tenant → 
Update token z tid/trol → 
Frontend
```

---

### 6. Refresh token (bez 2FA)

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "iat": 1704460800,
  "exp": 1704468600,
  "type": "refresh",
  "tfaPending": false,
  "tfaVerified": false,
  "tfaMethod": null
}
```

**Kiedy:**
- Używany do odświeżania access token
- Nie zawiera `tid`/`trol` (tenant context musi być ponownie ustawiony)
- Dłuższy czas wygaśnięcia (7 dni)

**Flow:**
```
Access token expired → 
POST /auth/refresh z refresh token → 
Nowy access token (bez tenant context, trzeba ponownie wybrać)
```

---

### 7. Refresh token (z 2FA)

**Payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "iat": 1704460800,
  "exp": 1704468600,
  "type": "refresh",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "totp"
}
```

**Kiedy:**
- Refresh token dla użytkownika z 2FA
- Po refresh access token też ma `tfaVerified: true`

---

## 📊 State Transition Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    LOGIN FLOW                           │
└─────────────────────────────────────────────────────────┘

1. POST /auth/login (email, password)
   │
   ├─→ Password invalid → 401 Unauthorized
   │
   └─→ Password valid
       │
       ├─→ 2FA disabled
       │   └─→ JWT access token (tfaPending: false, tfaVerified: false)
       │       └─→ [State 1] Użytkownik bez tenant, bez 2FA
       │
       └─→ 2FA enabled
           └─→ TwoFactorRequiredResponse
               └─→ twoFactorToken (tfaPending: true) [State 3]
                   │
                   ├─→ User cancels → Token expires
                   │
                   └─→ POST /two-factor/totp/verify-login
                       │
                       ├─→ Code invalid → 401, retry
                       │
                       └─→ Code valid
                           └─→ JWT access token (tfaVerified: true) [State 4]
                               │
                               └─→ User selects tenant
                                   └─→ Updated token (tid, trol) [State 5]
```

---

## 🔐 Token Types

### Access Token
- **Typ:** `"access"`
- **Expiration:** 30 minut (default)
- **Zawartość:**
  - `sub`, `email`, `iat`, `exp`
  - `tid`, `trol` (opcjonalnie, jeśli tenant wybrany)
  - `tfaPending`, `tfaVerified`, `tfaMethod` (opcjonalnie)
- **Użycie:** Normalne requesty API, wymaga Bearer token w header

### Refresh Token
- **Typ:** `"refresh"`
- **Expiration:** 7 dni (default)
- **Zawartość:**
  - `sub`, `email`, `iat`, `exp`
  - `tfaVerified`, `tfaMethod` (jeśli użytkownik ma 2FA)
  - **NIE zawiera** `tid`/`trol` (tenant context nie jest zachowany)
- **Użycie:** Tylko do odświeżania access token (`POST /auth/refresh`)

### 2FA Verification Token
- **Typ:** `"2fa_verification"`
- **Expiration:** 5 minut (default)
- **Zawartość:**
  - `sub`, `email`, `iat`, `exp`
  - `tfaPending: true`
  - `tfaVerified: false`
- **Użycie:** Tylko do weryfikacji 2FA, nie można używać do normalnych requestów

### Setup Tokens (TOTP/Passkey)
- **Typ:** `"2fa_setup"` lub `"passkey_registration"`
- **Expiration:** 10 minut (default)
- **Użycie:** Tylko podczas konfiguracji 2FA, nie są access tokens

---

## 🔄 Detailed Flow Examples

### Flow 1: Login bez 2FA, bez tenant

```
1. Frontend: POST /auth/login { email, password }
2. Backend: Weryfikuje hasło
3. Backend: Sprawdza czy user ma 2FA → NIE
4. Backend: Generuje JWT access token:
   {
     "sub": "user_123",
     "email": "user@example.com",
     "iat": 1704460800,
     "exp": 1704462600,
     "type": "access",
     "tfaPending": false,
     "tfaVerified": false,
     "tfaMethod": null
   }
5. Frontend: Zapisuje token, użytkownik zalogowany
```

### Flow 2: Login z 2FA (TOTP)

```
1. Frontend: POST /auth/login { email, password }
2. Backend: Weryfikuje hasło
3. Backend: Sprawdza czy user ma 2FA → TAK (TOTP enabled)
4. Backend: Zwraca TwoFactorRequiredResponse:
   {
     "requiresTwoFactor": true,
     "twoFactorToken": "eyJ...",
     "methods": ["totp"],
     "preferredMethod": "totp",
     "expiresAt": "2025-01-05T12:10:00Z"
   }
5. Frontend: Pokazuje ekran wprowadzania kodu TOTP
6. Frontend: POST /two-factor/totp/verify-login
   {
     "twoFactorToken": "eyJ...",
     "code": "123456"
   }
7. Backend: Weryfikuje kod TOTP
8. Backend: Generuje JWT access token:
   {
     "sub": "user_123",
     "email": "user@example.com",
     "iat": 1704460800,
     "exp": 1704462600,
     "type": "access",
     "tfaPending": false,
     "tfaVerified": true,
     "tfaMethod": "totp"
   }
9. Frontend: Zapisuje token, użytkownik zalogowany
```

### Flow 3: Wybór tenant (po loginie)

```
1. Frontend: User wybiera tenant z listy
2. Frontend: POST /api/tenants/{tenant_id}/select
   Headers: { Authorization: "Bearer {access_token}" }
3. Backend: Weryfikuje token
4. Backend: Sprawdza czy user ma dostęp do tenant
5. Backend: Generuje nowy JWT access token z tenant context:
   {
     "sub": "user_123",
     "email": "user@example.com",
     "tid": "tenant_456",
     "trol": "admin",
     "iat": 1704460800,
     "exp": 1704462600,
     "type": "access",
     "tfaPending": false,
     "tfaVerified": true,
     "tfaMethod": "totp"
   }
6. Frontend: Aktualizuje token, użytkownik ma dostęp do tenant
```

### Flow 4: Refresh token (z 2FA)

```
1. Frontend: Access token expired
2. Frontend: POST /auth/refresh
   {
     "refreshToken": "eyJ..."
   }
3. Backend: Weryfikuje refresh token
4. Backend: Sprawdza czy user ma 2FA → TAK
5. Backend: Generuje nowy access token:
   {
     "sub": "user_123",
     "email": "user@example.com",
     "iat": 1704460800,
     "exp": 1704462600,
     "type": "access",
     "tfaPending": false,
     "tfaVerified": true,  // Zachowane z refresh token
     "tfaMethod": "totp"   // Zachowane z refresh token
     // tid/trol NIE są zachowane - trzeba ponownie wybrać tenant
   }
6. Frontend: Aktualizuje access token
```

---

## 🛡️ Security Considerations

### Token Expiration
- **Access token:** 30 minut (krótki, bezpieczny)
- **Refresh token:** 7 dni (długi, do odświeżania)
- **2FA verification token:** 5 minut (bardzo krótki, tylko do weryfikacji)
- **Setup tokens:** 10 minut (tylko podczas konfiguracji)

### Token Validation Rules

1. **Access token:**
   - Wymagany `type: "access"`
   - Jeśli `tfaPending: true` → **ODRZUĆ** (token nie jest jeszcze zweryfikowany)
   - Jeśli `tfaVerified: true` → User ma zweryfikowane 2FA
   - Jeśli `tid` obecny → User ma aktywny tenant context

2. **Refresh token:**
   - Wymagany `type: "refresh"`
   - **NIE może** zawierać `tid`/`trol` (tenant context nie jest zachowywany)
   - Może zawierać `tfaVerified`/`tfaMethod` (zachowane z poprzedniego access token)

3. **2FA verification token:**
   - Wymagany `type: "2fa_verification"`
   - Wymagany `tfaPending: true`
   - **Tylko** do weryfikacji 2FA, nie do normalnych requestów

### Tenant Context

- **Tenant ID (`tid`):** Identyfikator aktywnego tenant
- **Tenant Role (`trol`):** Rola użytkownika w tenant (admin, member, viewer, etc.)
- **Zachowanie:** Tenant context **NIE jest** zachowywany w refresh token
- **Powód:** Bezpieczeństwo - wymusza ponowną weryfikację dostępu do tenant

---

## 🔧 Backend Implementation Requirements

### 1. Rozszerzenie `JWTPayload` TypedDict

**Plik:** `app/modules/auth/types/jwt.py`

```python
class JWTPayload(TypedDict, total=False):
    sub: str
    email: str
    tid: str | None
    trol: str | None
    iat: int
    exp: int
    aud: str | None
    tfaPending: bool | None
    tfaVerified: bool | None
    tfaMethod: str | None  # 'totp' | 'webauthn'
    type: str
```

### 2. Aktualizacja `create_access_token()`

**Plik:** `app/modules/auth/auth_utils.py`

```python
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    email: str | None = None,
    tid: str | None = None,
    trol: str | None = None,
    tfa_verified: bool = False,
    tfa_method: str | None = None,
) -> str:
    """Create JWT access token with optional tenant and 2FA context."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.security.access_token_expires_minutes)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "type": "access",
        "iat": int(datetime.now(UTC).timestamp()),
    })
    
    # Add email if provided
    if email:
        to_encode["email"] = email
    
    # Add tenant context if provided
    if tid:
        to_encode["tid"] = tid
    if trol:
        to_encode["trol"] = trol
    
    # Add 2FA context
    to_encode["tfaPending"] = False
    to_encode["tfaVerified"] = tfa_verified
    to_encode["tfaMethod"] = tfa_method
    
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt
```

### 3. Aktualizacja `AuthServiceWith2FA`

**Plik:** `app/modules/two_factor/auth_integration.py`

```python
async def login_user(
    self, email: str, password: str
) -> LoginResponse | TwoFactorRequiredResponse:
    # ... password verification ...
    
    if has_2fa:
        # Return TwoFactorRequiredResponse
        # twoFactorToken ma tfaPending: true
        ...
    else:
        # Generate access token bez 2FA
        access_token = create_access_token(
            data={"sub": user.id},
            email=user.email,
            tfa_verified=False,
            tfa_method=None
        )
        ...
```

### 4. Aktualizacja `verify_totp_login()`

**Plik:** `app/modules/two_factor/service.py`

```python
async def verify_totp_login(self, two_factor_token: str, code: str) -> dict[str, Any]:
    # ... verify 2FA code ...
    
    # Generate access token with 2FA verified
    access_token = create_access_token(
        data={"sub": user_id},
        email=user.email,  # Potrzebujemy email z user repository
        tfa_verified=True,
        tfa_method="totp"  # lub "webauthn"
    )
    ...
```

### 5. Endpoint wyboru tenant (do implementacji)

**Plik:** `app/modules/tenants/router.py` (nowy moduł lub w istniejącym)

```python
@router.post("/tenants/{tenant_id}/select")
async def select_tenant(
    tenant_id: str,
    current_user: CurrentUser = Depends(),
):
    """Select tenant and generate new access token with tenant context."""
    # Verify user has access to tenant
    # Get user role in tenant
    
    # Generate new access token with tenant context
    access_token = create_access_token(
        data={"sub": current_user.id},
        email=current_user.email,
        tid=tenant_id,
        trol=user_role,
        tfa_verified=current_user.tfa_verified,  # From current token
        tfa_method=current_user.tfa_method,      # From current token
    )
    
    return {"accessToken": access_token, ...}
```

---

## 📝 Frontend Integration Guide

### Checking Token State

```typescript
interface TokenState {
  isAuthenticated: boolean
  hasTenant: boolean
  requires2FA: boolean
  has2FAVerified: boolean
  twoFactorMethod: 'totp' | 'webauthn' | null
}

function parseTokenState(token: JWTPayload): TokenState {
  return {
    isAuthenticated: !!token.sub,
    hasTenant: !!token.tid,
    requires2FA: token.tfaPending === true,
    has2FAVerified: token.tfaVerified === true,
    twoFactorMethod: token.tfaMethod || null,
  }
}
```

### Handling Login Response

```typescript
async function login(email: string, password: string) {
  const response = await fetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  
  const data = await response.json()
  
  if (data.requiresTwoFactor) {
    // Show 2FA screen
    const { twoFactorToken, methods } = data
    return { type: '2fa_required', twoFactorToken, methods }
  } else {
    // Normal login
    const { accessToken, refreshToken } = data
    return { type: 'logged_in', accessToken, refreshToken }
  }
}
```

### Handling 2FA Verification

```typescript
async function verify2FA(twoFactorToken: string, code: string) {
  const response = await fetch('/two-factor/totp/verify-login', {
    method: 'POST',
    body: JSON.stringify({ twoFactorToken, code }),
  })
  
  const { accessToken, refreshToken } = await response.json()
  
  // Check token state
  const payload = decodeJWT(accessToken)
  if (payload.tfaVerified) {
    // User has verified 2FA
    console.log(`2FA method: ${payload.tfaMethod}`)
  }
}
```

### Selecting Tenant

```typescript
async function selectTenant(tenantId: string, accessToken: string) {
  const response = await fetch(`/api/tenants/${tenantId}/select`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  
  const { accessToken: newToken } = await response.json()
  
  // New token has tid and trol
  const payload = decodeJWT(newToken)
  console.log(`Tenant: ${payload.tid}, Role: ${payload.trol}`)
}
```

---

## ✅ Checklist implementacji

### Backend

- [ ] Rozszerzyć `JWTPayload` TypedDict o `email`, `tid`, `trol`, `tfaPending`, `tfaVerified`, `tfaMethod`
- [ ] Zaktualizować `create_access_token()` aby przyjmował wszystkie opcjonalne parametry
- [ ] Zaktualizować `create_refresh_token()` aby zachowywał `tfaVerified`/`tfaMethod` (bez `tid`/`trol`)
- [ ] Zaktualizować `AuthServiceWith2FA.login_user()` aby dodawał `email` do access token
- [ ] Zaktualizować `verify_totp_login()` aby dodawał `email`, `tfaVerified: true`, `tfaMethod` do access token
- [ ] Zaktualizować `verify_webauthn_login()` (Phase 5) aby dodawał `tfaMethod: "webauthn"`
- [ ] Stworzyć endpoint `POST /api/tenants/{tenant_id}/select` (jeśli multi-tenant)
- [ ] Dodać walidację w `get_current_user()` aby odrzucał tokeny z `tfaPending: true`
- [ ] Dodać helper do wyciągania tenant context z token (`tid`, `trol`)

### Frontend

- [ ] Zaktualizować TypeScript interfaces aby były zgodne z backendem
- [ ] Dodać funkcję `parseTokenState()` do analizy stanu tokenu
- [ ] Zaktualizować login flow aby obsługiwał `TwoFactorRequiredResponse`
- [ ] Zaktualizować refresh token flow aby zachowywał stan 2FA
- [ ] Dodać flow wyboru tenant (jeśli multi-tenant)
- [ ] Dodać walidację tokenów przed użyciem (sprawdzanie `tfaPending`)

---

## 🔍 Open Questions / Decisions Needed

1. **Multi-tenant support:**
   - Czy system wspiera multi-tenant?
   - Jeśli tak, gdzie są endpointy do zarządzania tenant?
   - Czy `tid`/`trol` są zawsze opcjonalne?

2. **Refresh token z tenant:**
   - Czy refresh token powinien zachowywać tenant context?
   - Obecna decyzja: **NIE** (bezpieczeństwo)
   - Czy to jest akceptowalne?

3. **2FA w refresh token:**
   - Czy refresh token powinien zawierać `tfaVerified`/`tfaMethod`?
   - Obecna decyzja: **TAK** (zachowuje stan 2FA)
   - Czy to jest akceptowalne?

4. **Email w token:**
   - Czy `email` powinien być zawsze w token?
   - Obecna decyzja: **TAK** (dla frontend convenience)
   - Alternatywa: Frontend pobiera email z `/auth/me` endpoint

5. **Audience (`aud`):**
   - Czy potrzebujemy `aud` field?
   - Jeśli tak, jakie wartości?

6. **Token expiration:**
   - Czy 30 minut dla access token jest OK?
   - Czy 5 minut dla 2FA verification token jest OK?

---

## 📚 Przykłady użycia

### Przykład 1: Pełny flow z 2FA i tenant

```python
# 1. Login
response = await client.post("/auth/login", json={
    "email": "user@example.com",
    "password": "SecurePass123!"
})
# Response: TwoFactorRequiredResponse

# 2. Verify 2FA
response = await client.post("/two-factor/totp/verify-login", json={
    "twoFactorToken": response.json()["twoFactorToken"],
    "code": "123456"
})
access_token = response.json()["accessToken"]

# 3. Decode token
payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
# {
#   "sub": "user_123",
#   "email": "user@example.com",
#   "tfaVerified": true,
#   "tfaMethod": "totp",
#   ...
# }

# 4. Select tenant
response = await client.post(
    f"/api/tenants/{tenant_id}/select",
    headers={"Authorization": f"Bearer {access_token}"}
)
new_access_token = response.json()["accessToken"]

# 5. Decode new token
payload = jwt.decode(new_access_token, SECRET_KEY, algorithms=["HS256"])
# {
#   "sub": "user_123",
#   "email": "user@example.com",
#   "tid": "tenant_456",
#   "trol": "admin",
#   "tfaVerified": true,
#   "tfaMethod": "totp",
#   ...
# }
```

### Przykład 2: Refresh token

```python
# Access token expired
response = await client.post("/auth/refresh", json={
    "refreshToken": refresh_token
})

new_access_token = response.json()["accessToken"]
payload = jwt.decode(new_access_token, SECRET_KEY, algorithms=["HS256"])

# Tenant context NIE jest zachowany
assert "tid" not in payload  # True
assert "trol" not in payload  # True

# 2FA context JEST zachowany
assert payload["tfaVerified"] == True  # True
assert payload["tfaMethod"] == "totp"  # True
```

---

**Data utworzenia:** 2025-01-05  
**Ostatnia aktualizacja:** 2025-01-05  
**Status:** ⚠️ **W trakcie uzgodnień** - wymaga review i akceptacji backend-frontend


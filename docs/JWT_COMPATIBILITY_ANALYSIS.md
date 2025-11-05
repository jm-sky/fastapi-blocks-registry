# Analiza kompatybilności JWT Payload - Backend Python

## 📋 Przegląd

Ten dokument analizuje obecny kod Python i sprawdza kompatybilność z nowym unified JWT payload schema (zgodnym z frontendowym interface).

**Data analizy:** 2025-01-05  
**Status:** Analiza wymaganych zmian

---

## 🔍 Obecne scenariusze w kodzie Python

### 1. Login bez 2FA (`AuthService.login_user`)

**Lokalizacja:** `app/modules/auth/service.py:55-92`

**Kod:**
```python
access_token = create_access_token(data={"sub": user.id})
refresh_token = create_refresh_token(data={"sub": user.id})
```

**Obecny payload:**
```json
{
  "sub": "user_123",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access"
}
```

**Brakuje:**
- ❌ `email` - mamy dostęp do `user.email`
- ❌ `tfaPending: false`
- ❌ `tfaVerified: false`
- ❌ `tfaMethod: null`

**Status:** ⚠️ **Wymaga zmian** - brakuje `email` i pól 2FA

---

### 2. Login z 2FA - TwoFactorRequiredResponse (`AuthServiceWith2FA.login_user`)

**Lokalizacja:** `app/modules/two_factor/auth_integration.py:43-96`

**Kod:**
```python
if has_2fa:
    two_factor_token = create_two_factor_token(data={"sub": user.id})
    # Zwraca TwoFactorRequiredResponse (nie access token)
else:
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
```

**Obecny payload (2FA token):**
```json
{
  "sub": "user_123",
  "exp": 1704461100,
  "iat": 1704460800,
  "type": "2fa_verification",
  "tfaPending": true  // ✅ Jest!
}
```

**Brakuje w 2FA token:**
- ❌ `email` - mamy dostęp do `user.email`

**Obecny payload (access token bez 2FA):**
```json
{
  "sub": "user_123",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access"
}
```

**Brakuje:**
- ❌ `email`
- ❌ `tfaPending: false`
- ❌ `tfaVerified: false`
- ❌ `tfaMethod: null`

**Status:** ⚠️ **Wymaga zmian** - `email` brakuje, pola 2FA tylko częściowo

---

### 3. Weryfikacja 2FA podczas logowania (`verify_totp_login`)

**Lokalizacja:** `app/modules/two_factor/service.py:253-299`

**Kod:**
```python
access_token = create_access_token(data={"sub": user_id})
refresh_token = create_refresh_token(data={"sub": user_id})
```

**Obecny payload:**
```json
{
  "sub": "user_123",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access"
}
```

**Brakuje:**
- ❌ `email` - musimy pobrać z repository
- ❌ `tfaPending: false`
- ❌ `tfaVerified: true` - **WAŻNE!** User zweryfikował 2FA
- ❌ `tfaMethod: "totp"` - **WAŻNE!** Wiemy że użył TOTP

**Status:** ⚠️ **Wymaga zmian** - krytyczne pola 2FA brakują

---

### 4. Refresh access token (`AuthService.refresh_access_token`)

**Lokalizacja:** `app/modules/auth/service.py:95-134`

**Kod:**
```python
payload = verify_token(refresh_token)
user_id = payload.get("sub")
user = await self.user_repository.get_user_by_id(user_id)

new_access_token = create_access_token(data={"sub": user_id})
new_refresh_token = create_refresh_token(data={"sub": user_id})
```

**Obecny payload (nowy access token):**
```json
{
  "sub": "user_123",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access"
}
```

**Brakuje:**
- ❌ `email` - mamy dostęp do `user.email`
- ❌ `tfaPending: false`
- ❌ `tfaVerified` - **WAŻNE!** Powinno być zachowane z refresh token
- ❌ `tfaMethod` - **WAŻNE!** Powinno być zachowane z refresh token
- ❌ `tid`/`trol` - **WAŻNE!** Nie powinno być zachowane (bezpieczeństwo)

**Status:** ⚠️ **Wymaga zmian** - nie zachowuje stanu 2FA z refresh token

---

### 5. Weryfikacja tokenu (`get_current_user`)

**Lokalizacja:** `app/modules/auth/dependencies.py:25-100`

**Obecny kod:**
```python
payload = verify_token(token)
if payload.get("type") != "access":
    raise HTTPException(...)

user_id = payload.get("sub")
user = await user_repository.get_user_by_id(user_id)
```

**Sprawdzane:**
- ✅ `type == "access"`
- ✅ `sub` (user_id)
- ✅ User exists and is active

**Brakuje:**
- ❌ Sprawdzenie `tfaPending` - **WAŻNE!** Powinno odrzucać tokeny z `tfaPending: true`
- ❌ Sprawdzenie `tid`/`trol` - jeśli multi-tenant, powinno walidować dostęp

**Status:** ⚠️ **Wymaga zmian** - brakuje walidacji `tfaPending`

---

### 6. Setup tokeny (TOTP/Passkey)

**Lokalizacja:** `app/modules/two_factor/service.py:23-50`

**Kod:**
```python
payload = {
    **data,
    "type": "2fa_setup" | "passkey_registration",
    "exp": expires,
    "iat": datetime.now(UTC),
}
```

**Status:** ✅ **OK** - Setup tokeny są wewnętrzne, nie są access tokens

---

## 🔄 Mapowanie scenariuszy na nowy schema

### Scenariusz 1: Login bez 2FA

**Obecny kod:**
```python
access_token = create_access_token(data={"sub": user.id})
```

**Wymagana zmiana:**
```python
access_token = create_access_token(
    data={"sub": user.id},
    email=user.email,
    tfa_verified=False,
    tfa_method=None
)
```

**Nowy payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": false,
  "tfaMethod": null
}
```

---

### Scenariusz 2: Login z 2FA - TwoFactorRequiredResponse

**Obecny kod:**
```python
two_factor_token = create_two_factor_token(data={"sub": user.id})
```

**Wymagana zmiana:**
```python
two_factor_token = create_two_factor_token(
    data={"sub": user.id, "email": user.email}
)
```

**Nowy payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704461100,
  "iat": 1704460800,
  "type": "2fa_verification",
  "tfaPending": true,
  "tfaVerified": false,
  "tfaMethod": null
}
```

---

### Scenariusz 3: Weryfikacja 2FA (TOTP)

**Obecny kod:**
```python
access_token = create_access_token(data={"sub": user_id})
```

**Wymagana zmiana:**
```python
# Pobierz user z repository
user = await user_repository.get_user_by_id(user_id)

access_token = create_access_token(
    data={"sub": user_id},
    email=user.email,
    tfa_verified=True,
    tfa_method="totp"
)
```

**Nowy payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "totp"
}
```

---

### Scenariusz 4: Weryfikacja 2FA (WebAuthn) - Phase 5

**Lokalizacja:** `app/modules/two_factor/service.py` (do implementacji)

**Wymagana zmiana:**
```python
access_token = create_access_token(
    data={"sub": user_id},
    email=user.email,
    tfa_verified=True,
    tfa_method="webauthn"
)
```

**Nowy payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "webauthn"
}
```

---

### Scenariusz 5: Refresh token

**Obecny kod:**
```python
new_access_token = create_access_token(data={"sub": user_id})
new_refresh_token = create_refresh_token(data={"sub": user_id})
```

**Wymagana zmiana:**
```python
# Zachowaj 2FA state z refresh token
old_tfa_verified = payload.get("tfaVerified", False)
old_tfa_method = payload.get("tfaMethod")

new_access_token = create_access_token(
    data={"sub": user_id},
    email=user.email,
    tfa_verified=old_tfa_verified,
    tfa_method=old_tfa_method
    # tid/trol NIE są zachowane
)
new_refresh_token = create_refresh_token(
    data={"sub": user_id},
    email=user.email,
    tfa_verified=old_tfa_verified,
    tfa_method=old_tfa_method
)
```

**Nowy payload (access token):**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,  // Zachowane z refresh token
  "tfaMethod": "totp"   // Zachowane z refresh token
  // tid/trol NIE są zachowane
}
```

**Nowy payload (refresh token):**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "exp": 1704468600,
  "iat": 1704460800,
  "type": "refresh",
  "tfaVerified": true,  // Zachowane
  "tfaMethod": "totp"   // Zachowane
  // tid/trol NIE są w refresh token
}
```

---

### Scenariusz 6: Wybór tenant (do implementacji)

**Lokalizacja:** Nowy endpoint lub moduł `tenants`

**Wymagana implementacja:**
```python
@router.post("/tenants/{tenant_id}/select")
async def select_tenant(
    tenant_id: str,
    current_user: CurrentUser = Depends(),
):
    # Pobierz tenant context z token
    token_payload = get_token_from_request()  # Helper function
    
    # Sprawdź dostęp do tenant
    tenant = await tenant_repository.get_tenant(tenant_id)
    user_role = await tenant_repository.get_user_role(
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    
    # Generuj nowy token z tenant context
    new_access_token = create_access_token(
        data={"sub": current_user.id},
        email=current_user.email,
        tid=tenant_id,
        trol=user_role,
        tfa_verified=token_payload.get("tfaVerified", False),
        tfa_method=token_payload.get("tfaMethod")
    )
    
    return {"accessToken": new_access_token, ...}
```

**Nowy payload:**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "tid": "tenant_456",
  "trol": "admin",
  "exp": 1704462600,
  "iat": 1704460800,
  "type": "access",
  "tfaPending": false,
  "tfaVerified": true,
  "tfaMethod": "totp"
}
```

---

## ⚠️ Problemy kompatybilności

### 1. Brak `email` we wszystkich tokenach

**Problem:**
- Wszystkie miejsca tworzenia tokenów przekazują tylko `{"sub": user_id}`
- `email` nie jest w tokenie, frontend musi go pobierać z `/auth/me`

**Rozwiązanie:**
- Dodać `email` do wszystkich wywołań `create_access_token()` i `create_refresh_token()`
- Mamy dostęp do `user.email` w większości miejsc

**Status:** ✅ **Łatwe do naprawy**

---

### 2. Brak pól 2FA w access/refresh tokens

**Problem:**
- `tfaPending`, `tfaVerified`, `tfaMethod` nie są ustawiane w access/refresh tokens
- Frontend nie może sprawdzić stanu 2FA z tokenu

**Rozwiązanie:**
- Rozszerzyć `create_access_token()` i `create_refresh_token()` o parametry 2FA
- Ustawiać `tfaVerified: true` i `tfaMethod` w `verify_totp_login()`
- Zachowywać w refresh token

**Status:** ⚠️ **Wymaga zmian, ale nie jest breaking**

---

### 3. Refresh token nie zachowuje stanu 2FA

**Problem:**
- Po refresh access token traci informację o 2FA
- User musi ponownie weryfikować 2FA (nieprawidłowe)

**Rozwiązanie:**
- W `refresh_access_token()` odczytać `tfaVerified`/`tfaMethod` z refresh token
- Przekazać do nowego access token

**Status:** ⚠️ **Wymaga zmian - może być breaking dla istniejących tokenów**

---

### 4. Brak walidacji `tfaPending` w `get_current_user`

**Problem:**
- Token z `tfaPending: true` może być użyty do normalnych requestów
- To jest security issue - token nie jest jeszcze zweryfikowany

**Rozwiązanie:**
- Dodać sprawdzenie w `get_current_user()`:
  ```python
  if payload.get("tfaPending") is True:
      raise HTTPException(401, "2FA verification required")
  ```

**Status:** ✅ **Łatwe do naprawy**

---

### 5. Brak `tid`/`trol` (multi-tenant)

**Problem:**
- Multi-tenant nie jest jeszcze zaimplementowany
- Brak endpointu do wyboru tenant
- Brak weryfikacji dostępu do tenant

**Rozwiązanie:**
- Zaimplementować moduł `tenants` lub endpoint w `auth`
- Dodać logikę wyboru tenant i aktualizacji tokenu

**Status:** ⚠️ **Do implementacji w przyszłości**

---

## 📊 Tabela kompatybilności

| Scenariusz | Obecny payload | Wymaga zmian | Priorytet | Breaking |
|------------|----------------|--------------|-----------|----------|
| Login bez 2FA | `{sub, exp, iat, type}` | ✅ Dodaj `email`, pola 2FA | Wysoki | ❌ Nie |
| Login z 2FA (token) | `{sub, exp, iat, type, tfaPending}` | ✅ Dodaj `email` | Średni | ❌ Nie |
| Login z 2FA (access) | `{sub, exp, iat, type}` | ✅ Dodaj `email`, `tfaVerified`, `tfaMethod` | Wysoki | ❌ Nie |
| Verify 2FA (TOTP) | `{sub, exp, iat, type}` | ✅ Dodaj `email`, `tfaVerified: true`, `tfaMethod: "totp"` | Wysoki | ❌ Nie |
| Verify 2FA (WebAuthn) | Nie zaimplementowane | ✅ Dodaj jak TOTP | Średni | ❌ Nie |
| Refresh token | `{sub, exp, iat, type}` | ✅ Dodaj `email`, zachowaj 2FA state | Wysoki | ⚠️ Może być |
| Select tenant | Nie zaimplementowane | ✅ Nowa funkcjonalność | Niski | ❌ Nie |
| `get_current_user` | Sprawdza tylko `type`, `sub` | ✅ Dodaj walidację `tfaPending` | Wysoki | ❌ Nie |

---

## 🔧 Wymagane zmiany w kodzie

### 1. Rozszerzenie `create_access_token()`

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

---

### 2. Rozszerzenie `create_refresh_token()`

**Plik:** `app/modules/auth/auth_utils.py`

```python
def create_refresh_token(
    data: dict[str, Any],
    email: str | None = None,
    tfa_verified: bool = False,
    tfa_method: str | None = None,
) -> str:
    """Create JWT refresh token with 2FA context (tenant context NOT preserved)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.security.refresh_token_expires_days)
    to_encode.update({
        "exp": int(expire.timestamp()),
        "type": "refresh",
        "iat": int(datetime.now(UTC).timestamp()),
    })
    
    # Add email if provided
    if email:
        to_encode["email"] = email
    
    # Add 2FA context (preserved in refresh token)
    to_encode["tfaVerified"] = tfa_verified
    to_encode["tfaMethod"] = tfa_method
    # NOTE: tid/trol are NOT preserved in refresh token (security)
    
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt
```

---

### 3. Aktualizacja `AuthService.login_user()`

**Plik:** `app/modules/auth/service.py`

```python
# Generate tokens
access_token = create_access_token(
    data={"sub": user.id},
    email=user.email,
    tfa_verified=False,
    tfa_method=None
)
refresh_token = create_refresh_token(
    data={"sub": user.id},
    email=user.email,
    tfa_verified=False,
    tfa_method=None
)
```

---

### 4. Aktualizacja `AuthServiceWith2FA.login_user()`

**Plik:** `app/modules/two_factor/auth_integration.py`

```python
if has_2fa:
    two_factor_token = create_two_factor_token(
        data={"sub": user.id, "email": user.email}
    )
    # ...
else:
    access_token = create_access_token(
        data={"sub": user.id},
        email=user.email,
        tfa_verified=False,
        tfa_method=None
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        email=user.email,
        tfa_verified=False,
        tfa_method=None
    )
```

---

### 5. Aktualizacja `verify_totp_login()`

**Plik:** `app/modules/two_factor/service.py`

```python
async def verify_totp_login(self, two_factor_token: str, code: str) -> dict[str, Any]:
    # ... verify code ...
    
    # Get user to get email
    from app.modules.auth.repositories import get_user_repository
    # Note: This requires passing user_repository or getting user from repository
    user = await self.repository.get_user_by_id(user_id)  # Need to add this method
    
    # Determine 2FA method used
    tfa_method = "totp"  # or "webauthn" if using passkey
    if not is_valid and verify_backup_code(...):
        tfa_method = "totp"  # Backup codes are for TOTP
    
    # Generate JWT tokens
    access_token = create_access_token(
        data={"sub": user_id},
        email=user.email,
        tfa_verified=True,
        tfa_method=tfa_method
    )
    refresh_token = create_refresh_token(
        data={"sub": user_id},
        email=user.email,
        tfa_verified=True,
        tfa_method=tfa_method
    )
```

**Problem:** Nie mamy dostępu do `user.email` w `verify_totp_login()` - potrzebujemy user repository.

---

### 6. Aktualizacja `refresh_access_token()`

**Plik:** `app/modules/auth/service.py`

```python
async def refresh_access_token(self, refresh_token: str) -> dict[str, str | int]:
    payload = verify_token(refresh_token)
    
    # ... verify user ...
    
    # Preserve 2FA state from refresh token
    old_tfa_verified = payload.get("tfaVerified", False)
    old_tfa_method = payload.get("tfaMethod")
    
    # Generate new tokens
    new_access_token = create_access_token(
        data={"sub": user_id},
        email=user.email,
        tfa_verified=old_tfa_verified,
        tfa_method=old_tfa_method
        # tid/trol NOT preserved
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user_id},
        email=user.email,
        tfa_verified=old_tfa_verified,
        tfa_method=old_tfa_method
    )
```

---

### 7. Aktualizacja `get_current_user()`

**Plik:** `app/modules/auth/dependencies.py`

```python
async def get_current_user(...):
    payload = verify_token(token)
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(...)
    
    # SECURITY: Reject tokens with tfaPending: true
    if payload.get("tfaPending") is True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA verification required. Token is pending 2FA verification.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ... rest of code ...
```

---

### 8. Aktualizacja `create_two_factor_token()`

**Plik:** `app/modules/two_factor/auth_utils.py`

```python
def create_two_factor_token(data: CreateTwoFactorTokenOptions) -> str:
    # ...
    payload: TwoFactorTokenPayload = {
        **data,
        "type": "2fa_verification",
        "exp": int(expires.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "tfaPending": True,
        "tfaVerified": False,
        "tfaMethod": None,
    }
    # ...
```

**Uwaga:** `CreateTwoFactorTokenOptions` powinno zawierać `email`.

---

## ✅ Kompatybilność wsteczna

### Czy nowy schema jest backward compatible?

**TAK** - z następującymi zastrzeżeniami:

1. **Nowe pola są opcjonalne:**
   - `email`, `tid`, `trol`, `tfaPending`, `tfaVerified`, `tfaMethod` są `None` w TypedDict
   - Stare tokeny bez tych pól będą działać

2. **Walidacja `tfaPending`:**
   - Nowa walidacja odrzuca tokeny z `tfaPending: true`
   - Stare tokeny nie mają tego pola, więc przejdą walidację ✅

3. **Refresh token:**
   - Stare refresh tokeny nie mają `tfaVerified`/`tfaMethod`
   - Po refresh, nowe tokeny będą miały `tfaVerified: False` (default)
   - To jest OK - user bez 2FA będzie miał `False`

4. **Breaking changes:**
   - ❌ **Brak** - wszystkie zmiany są backward compatible

---

## 📝 Checklist implementacji

### Priorytet Wysoki

- [ ] Rozszerzyć `create_access_token()` o parametry `email`, `tid`, `trol`, `tfa_verified`, `tfa_method`
- [ ] Rozszerzyć `create_refresh_token()` o parametry `email`, `tfa_verified`, `tfa_method`
- [ ] Zaktualizować `AuthService.login_user()` - dodać `email`, pola 2FA
- [ ] Zaktualizować `AuthServiceWith2FA.login_user()` - dodać `email`, pola 2FA
- [ ] Zaktualizować `verify_totp_login()` - dodać `email`, `tfaVerified: true`, `tfaMethod: "totp"`
- [ ] Zaktualizować `refresh_access_token()` - zachować stan 2FA z refresh token
- [ ] Dodać walidację `tfaPending` w `get_current_user()`
- [ ] Zaktualizować `create_two_factor_token()` - dodać `email`, `tfaPending: true`

### Priorytet Średni

- [ ] Zaktualizować `verify_webauthn_login()` (Phase 5) - dodać `tfaMethod: "webauthn"`
- [ ] Dodać helper do wyciągania tenant context z token (`get_tenant_from_token()`)

### Priorytet Niski (do implementacji)

- [ ] Endpoint `POST /api/tenants/{tenant_id}/select`
- [ ] Moduł `tenants` (jeśli nie istnieje)

---

## 🎯 Podsumowanie

### Obecny stan

- ✅ **6 scenariuszy** zidentyfikowanych
- ⚠️ **Wszystkie wymagają zmian** - brakuje `email` i pól 2FA
- ✅ **Backward compatible** - zmiany nie są breaking
- ✅ **Łatwe do naprawy** - większość zmian to dodanie parametrów

### Główne problemy

1. **Brak `email`** - mamy dostęp do `user.email` w większości miejsc
2. **Brak pól 2FA** - trzeba dodać do wszystkich wywołań
3. **Refresh token nie zachowuje 2FA** - trzeba naprawić
4. **Brak walidacji `tfaPending`** - security issue

### Rekomendacja

**TAK** - możemy użyć nowego schematu payload. Wszystkie zmiany są:
- ✅ Backward compatible
- ✅ Proste do implementacji
- ✅ Nie breaking

**Następne kroki:**
1. Zaimplementować zmiany z checklist (priorytet wysoki)
2. Przetestować backward compatibility
3. Zaktualizować frontend (jeśli potrzebne)

---

**Data analizy:** 2025-01-05  
**Status:** ✅ **Kompatybilne - wymaga zmian, ale nie breaking**


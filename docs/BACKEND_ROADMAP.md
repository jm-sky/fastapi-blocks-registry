# ROADMAP - FastAPI Blocks Registry (Backend)

## Przegląd
Plan implementacji modułów backendowych zgodnych z wymaganiami frontendowymi z FRONTEND_ROADMAP.md.

---

## 🔐 Multi-Tenancy

### Opis
System wielodostępowy, gdzie jeden użytkownik może mieć dostęp do wielu tenantów (organizacji/przestrzeni roboczych). User może przełączać się między tenantami.

### Nowy moduł: `tenants`

**Lokalizacja:** `fastapi_registry/example_project/app/modules/tenants/`

**Struktura modułu:**
```
tenants/
├── __init__.py
├── db_models.py          # SQLAlchemy models: Tenant, TenantUser
├── schemas.py            # Pydantic schemas: TenantCreate, TenantUpdate, TenantResponse, TenantUserResponse, etc.
├── router.py             # FastAPI routes
├── service.py            # Business logic
├── dependencies.py       # FastAPI dependencies (get_current_tenant, require_tenant_role)
├── exceptions.py         # Custom exceptions
├── repositories.py       # Database operations (async)
└── README.md
```

### Komponenty do implementacji

#### 1. Database Models (`db_models.py`)

```python
class TenantDB(Base):
    """Tenant (organization/workspace) model."""
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    business_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)  # taxId, vatId, NIP
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    members: Mapped[list["TenantUserDB"]] = relationship("TenantUserDB", back_populates="tenant", cascade="all, delete-orphan")


class TenantUserDB(Base):
    """Many-to-many relationship between users and tenants with role."""
    __tablename__ = "tenant_users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'owner', 'admin', 'member', 'viewer'
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # Relationships
    tenant: Mapped["TenantDB"] = relationship("TenantDB", back_populates="members")
    user: Mapped["UserDB"] = relationship("UserDB")  # From auth module
    
    # Unique constraint: user can only have one role per tenant
    __table_args__ = (UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user'),)
```

**Enum dla ról:**
```python
class TenantRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
```

#### 2. Pydantic Schemas (`schemas.py`)

```python
class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$')
    external_id: str | None = None
    business_identifier: str | None = None
    logo: str | None = None
    description: str | None = None

class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    pass

class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    name: str | None = None
    slug: str | None = None
    external_id: str | None = None
    business_identifier: str | None = None
    logo: str | None = None
    description: str | None = None
    is_active: bool | None = None

class TenantResponse(TenantBase):
    """Schema for tenant response."""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TenantUserResponse(BaseModel):
    """Schema for tenant membership response."""
    id: str
    tenant_id: str
    user_id: str
    role: str
    joined_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TenantMembershipResponse(BaseModel):
    """Schema for tenant membership with tenant details."""
    tenant: TenantResponse
    role: str
    permissions: list[str] = []

class SwitchTenantResponse(BaseModel):
    """Response for switch tenant endpoint."""
    token: str  # New JWT with tenant context
    tenant: TenantResponse
```

#### 3. Router (`router.py`)

**Endpoints:**
- `GET /api/v1/tenants` - Lista tenantów użytkownika (wymaga autoryzacji)
- `GET /api/v1/tenants/{tenant_id}` - Szczegóły tenant (wymaga członkostwa)
- `POST /api/v1/tenants` - Utwórz nowy tenant (wymaga autoryzacji, użytkownik staje się OWNER)
- `PATCH /api/v1/tenants/{tenant_id}` - Aktualizuj tenant (wymaga roli ADMIN lub OWNER)
- `POST /api/v1/tenants/{tenant_id}/switch` - Przełącz tenant (wymaga członkostwa)
  - Zwraca nowy JWT token z `tid` i `trol` w payload
- `GET /api/v1/tenants/{tenant_id}/members` - Lista członków tenant (wymaga członkostwa)
- `POST /api/v1/tenants/{tenant_id}/members` - Dodaj członka (wymaga roli ADMIN lub OWNER)
- `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}` - Usuń członka (wymaga roli ADMIN lub OWNER)

#### 4. Service (`service.py`)

**Główne metody:**
- `get_user_tenants(user_id: str) -> list[TenantResponse]` - Pobierz tenanty użytkownika
- `get_tenant(tenant_id: str, user_id: str) -> TenantResponse` - Pobierz tenant z weryfikacją dostępu
- `create_tenant(data: TenantCreate, owner_id: str) -> TenantResponse` - Utwórz tenant (owner automatycznie dodany)
- `update_tenant(tenant_id: str, data: TenantUpdate, user_id: str) -> TenantResponse` - Aktualizuj tenant
- `switch_tenant(tenant_id: str, user_id: str) -> SwitchTenantResponse` - Przełącz tenant i zwróć nowy JWT
- `get_tenant_members(tenant_id: str, user_id: str) -> list[TenantUserResponse]` - Lista członków
- `add_tenant_member(tenant_id: str, user_id: str, role: TenantRole, requester_id: str) -> TenantUserResponse` - Dodaj członka
- `remove_tenant_member(tenant_id: str, member_user_id: str, requester_id: str) -> None` - Usuń członka

#### 5. Dependencies (`dependencies.py`)

```python
async def get_current_tenant(
    current_user: User = Depends(get_current_user),  # From auth module
    db: AsyncSession = Depends(get_db)
) -> TenantDB:
    """Get current tenant from JWT token (tid claim)."""
    # Decode JWT to get tenant_id
    # Verify user has access to tenant
    # Return TenantDB

async def require_tenant_role(
    required_role: TenantRole,
    current_tenant: TenantDB = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TenantDB:
    """Verify user has required role in tenant."""
    # Check user role in tenant
    # Raise Forbidden if insufficient permissions
    # Return TenantDB
```

#### 6. Integracja z Auth Module

**Modyfikacje w `auth/auth_utils.py`:**
- Rozszerzyć `create_access_token()` aby akceptował `tenant_id` i `tenant_role`
- Dodać `tid` (tenant_id) i `trol` (tenant_role) do JWT payload
- Rozszerzyć `JWTPayload` w `types/jwt.py`:

```python
class JWTPayload(TypedDict, total=False):
    sub: str                    # userId
    email: str                 # user email (optional)
    tid: str                   # tenantId (optional - only if tenant selected)
    trol: str                  # tenantRole (optional - only if tenant selected)
    exp: int
    iat: int
    type: str                  # "access", "refresh", "reset"
```

**Modyfikacje w `auth/service.py`:**
- `login()` - domyślnie bez tenant context (może zwrócić pierwszy tenant jeśli użytkownik ma tylko jeden)
- Opcjonalnie: `login_with_tenant()` - login z wybranym tenantem

**Nowy endpoint w `auth/router.py`:**
- `POST /api/v1/auth/switch-tenant` - Przełącz tenant (alternatywa dla `/tenants/{id}/switch`)

### Zależności

**Module dependencies:**
- `module_dependencies: ["auth"]` - wymaga auth module

**Python dependencies:**
- Brak dodatkowych (używa SQLAlchemy, Pydantic z auth module)

**Environment variables:**
- Brak dodatkowych (może opcjonalnie: `DEFAULT_TENANT_ROLE`)

### Migracje Alembic

**Należy utworzyć migrację:**
- Tabela `tenants` z wszystkimi polami
- Tabela `tenant_users` z relacjami
- Indexy na `tenant_id`, `user_id`, `slug`, `external_id`
- Unique constraint na `(tenant_id, user_id)`

### Uwagi implementacyjne

1. **Row-Level Security (RLS):**
   - Wszystkie query powinny filtrować przez `tenant_id` z JWT
   - Middleware/dependency do ekstrakcji `tid` z JWT
   - Service layer automatycznie dodaje `tenant_id` do query

2. **Tenant Context w JWT:**
   - `tid` i `trol` dodawane tylko gdy użytkownik wybrał tenant
   - Przy switch tenant - nowy token z aktualnym tenant context
   - Refresh token może być bez tenant context (user może wybrać tenant przy odświeżeniu)

3. **Slug generation:**
   - Automatyczna generacja slug z `name` (lowercase, replace spaces with hyphens)
   - Walidacja unikalności slug
   - Slug używany w URL dla SEO/user experience (opcjonalnie)

4. **Default tenant:**
   - Przy rejestracji użytkownika można automatycznie utworzyć osobisty tenant
   - Lub użytkownik musi utworzyć/dołączyć do tenant ręcznie

---

## 🔑 OAuth

### Opis
Integracja z OAuth 2.0 / OpenID Connect dla logowania przez zewnętrzne serwisy (Google, GitHub).

### Nowy moduł: `oauth`

**Lokalizacja:** `fastapi_registry/example_project/app/modules/oauth/`

**Struktura modułu:**
```
oauth/
├── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py          # Base OAuth provider interface
│   ├── google.py        # Google OAuth provider (P0 - pierwszy)
│   ├── github.py        # GitHub OAuth provider (P0 - drugi)
│   └── types.py         # OAuthProvider enum
├── schemas.py           # Pydantic schemas
├── router.py            # FastAPI routes
├── service.py           # Business logic
├── dependencies.py      # FastAPI dependencies
├── exceptions.py        # Custom exceptions
├── db_models.py         # OAuthAccount model (optional - link OAuth to User)
└── README.md
```

### Priorytety implementacji providerów
1. **Google OAuth** (P0 - pierwszy priorytet)
2. **GitHub OAuth** (P0 - drugi priorytet)
3. **Microsoft, Apple** (P2 - opcjonalnie)

### Komponenty do implementacji

#### 1. Base Provider Interface (`providers/base.py`)

```python
from abc import ABC, abstractmethod

class OAuthProvider(ABC):
    """Base class for OAuth providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'google', 'github')."""
        pass
    
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generate OAuth authorization URL."""
        pass
    
    @abstractmethod
    async def get_token(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from provider."""
        pass
    
    def generate_state(self) -> str:
        """Generate random state for CSRF protection."""
        # Use secrets.token_urlsafe() or similar
        pass
```

#### 2. Google Provider (`providers/google.py`)

```python
from .base import OAuthProvider

class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",  # For refresh token
            "prompt": "consent"
        }
        return f"{self.authorization_url}?{urlencode(params)}"
    
    async def get_token(self, code: str, redirect_uri: str) -> dict[str, Any]:
        # Use httpx or aiohttp for async HTTP requests
        # Exchange code for access token
        pass
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        # Fetch user info from Google API
        # Returns: {id, email, name, picture}
        pass
```

#### 3. GitHub Provider (`providers/github.py`)

```python
class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"
    
    # Similar implementation to Google
```

#### 4. Database Model (opcjonalnie - `db_models.py`)

```python
class OAuthAccountDB(Base):
    """Link OAuth accounts to users."""
    __tablename__ = "oauth_accounts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'google', 'github'
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)  # User ID from provider
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)  # Encrypted
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)  # Encrypted
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # Unique constraint: one OAuth account per provider per user
    __table_args__ = (UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),)
```

#### 5. Router (`router.py`)

**Endpoints:**
- `GET /api/v1/auth/oauth/{provider}` - Inicjuj OAuth flow (redirect do provider)
  - Generuje state i PKCE code_verifier
  - Zapisuje state w session/cache (dla weryfikacji callback)
  - Redirect do provider authorization URL
  
- `GET /api/v1/auth/oauth/{provider}/callback` - OAuth callback handler
  - Weryfikuje state
  - Wymienia code na access token
  - Pobiera user info z providera
  - Tworzy/łączy użytkownika z OAuth account
  - Zwraca JWT token (jak w normalnym login)

**Provider values:**
- `google` - Google OAuth
- `github` - GitHub OAuth

#### 6. Service (`service.py`)

**Główne metody:**
- `initiate_oauth_flow(provider: str, redirect_uri: str) -> str` - Zwraca authorization URL
- `handle_oauth_callback(provider: str, code: str, state: str, redirect_uri: str) -> dict[str, Any]` - Obsługuje callback
  - Zwraca: `{access_token: str, refresh_token: str, user: User}` (kompatybilne z login response)

#### 7. Schemas (`schemas.py`)

```python
class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"

class OAuthInitiateResponse(BaseModel):
    """Response for OAuth initiation."""
    authorization_url: str
    state: str  # For verification in callback

class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback (same as login response)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse  # From auth module
```

### Zależności

**Module dependencies:**
- `module_dependencies: ["auth"]` - wymaga auth module

**Python dependencies:**
- `httpx>=0.27.0` - dla async HTTP requests do OAuth providers
- `cryptography>=42.0.0` - dla PKCE (code_verifier generation)

**Environment variables:**
```python
# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/google/callback

# GitHub OAuth
GITHUB_OAUTH_CLIENT_ID=your-github-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-client-secret
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/github/callback
```

### Uwagi implementacyjne

1. **PKCE Flow:**
   - Wymagane dla Google OAuth (SPA security)
   - Generowanie `code_verifier` i `code_challenge`
   - Przechowywanie `code_verifier` w session/cache (keyed by state)

2. **State verification:**
   - Random state dla CSRF protection
   - Przechowywanie w Redis/cache z TTL (5 minut)
   - Weryfikacja w callback

3. **User creation/linking:**
   - Jeśli OAuth account istnieje → login
   - Jeśli user istnieje (by email) → link OAuth account do user
   - Jeśli user nie istnieje → utwórz nowy user z OAuth data

4. **Token storage:**
   - OAuth tokens (access_token, refresh_token) mogą być opcjonalnie przechowywane w bazie (encrypted)
   - Używane do refresh token lub odwołania tokenu

5. **Error handling:**
   - Invalid state
   - Invalid code
   - Provider API errors
   - User denied access

---

## 👨‍💼 Admin Panel

### Opis
Panel administracyjny do zarządzania użytkownikami, tenantami oraz ogólnymi ustawieniami systemu.

### Nowy moduł: `admin`

**Lokalizacja:** `fastapi_registry/example_project/app/modules/admin/`

**Struktura modułu:**
```
admin/
├── __init__.py
├── schemas.py           # Pydantic schemas: AdminUserList, AdminTenantList, etc.
├── router.py            # FastAPI routes
├── service.py           # Business logic
├── dependencies.py      # FastAPI dependencies (require_admin)
├── exceptions.py        # Custom exceptions
└── README.md
```

### Komponenty do implementacji

#### 1. Dependencies (`dependencies.py`)

```python
async def require_admin(
    current_user: User = Depends(get_current_user)  # From auth module
) -> User:
    """Require user to be admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

#### 2. Schemas (`schemas.py`)

```python
from app.modules.auth.models import User  # Pydantic model from auth
from app.modules.tenants.schemas import TenantResponse  # From tenants module

class AdminUserList(User):
    """Extended user schema for admin list view."""
    last_login_at: datetime | None = None  # Optional - if tracking last login
    
    model_config = ConfigDict(from_attributes=True)

class AdminUserUpdate(BaseModel):
    """Schema for admin user update."""
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None

class AdminTenantList(TenantResponse):
    """Extended tenant schema for admin list view."""
    owner_id: str
    member_count: int
    
    model_config = ConfigDict(from_attributes=True)

class AdminTenantUpdate(BaseModel):
    """Schema for admin tenant update."""
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None
```

#### 3. Router (`router.py`)

**User Management Endpoints:**
- `GET /api/v1/admin/users` - Lista wszystkich użytkowników (paginacja, filtrowanie)
  - Query params: `page`, `limit`, `search`, `is_active`, `is_admin`
- `GET /api/v1/admin/users/{user_id}` - Szczegóły użytkownika
- `PATCH /api/v1/admin/users/{user_id}` - Aktualizuj użytkownika
- `DELETE /api/v1/admin/users/{user_id}` - Usuń użytkownika (soft delete lub hard delete)
- `POST /api/v1/admin/users/{user_id}/activate` - Ustaw `is_active = true`
- `POST /api/v1/admin/users/{user_id}/deactivate` - Ustaw `is_active = false`
- `POST /api/v1/admin/users/{user_id}/grant-admin` - Ustaw `is_admin = true`
- `POST /api/v1/admin/users/{user_id}/revoke-admin` - Ustaw `is_admin = false`

**Tenant Management Endpoints** (wymaga `tenants` module):
- `GET /api/v1/admin/tenants` - Lista wszystkich tenantów (paginacja, filtrowanie)
  - Query params: `page`, `limit`, `search`, `is_active`
- `GET /api/v1/admin/tenants/{tenant_id}` - Szczegóły tenant
- `PATCH /api/v1/admin/tenants/{tenant_id}` - Aktualizuj tenant
- `DELETE /api/v1/admin/tenants/{tenant_id}` - Usuń tenant
- `POST /api/v1/admin/tenants/{tenant_id}/activate` - Ustaw `is_active = true`
- `POST /api/v1/admin/tenants/{tenant_id}/deactivate` - Ustaw `is_active = false`

#### 4. Service (`service.py`)

**User Management:**
- `get_users(filters: dict, page: int, limit: int) -> PaginatedResponse[AdminUserList]`
- `get_user(user_id: str) -> User`
- `update_user(user_id: str, data: AdminUserUpdate) -> User`
- `delete_user(user_id: str) -> None`
- `set_user_active(user_id: str, is_active: bool) -> User`
- `set_user_admin(user_id: str, is_admin: bool) -> User`

**Tenant Management** (wymaga `tenants` module):
- `get_tenants(filters: dict, page: int, limit: int) -> PaginatedResponse[AdminTenantList]`
- `get_tenant(tenant_id: str) -> TenantResponse`
- `update_tenant(tenant_id: str, data: AdminTenantUpdate) -> TenantResponse`
- `delete_tenant(tenant_id: str) -> None`
- `set_tenant_active(tenant_id: str, is_active: bool) -> TenantResponse`

### Zależności

**Module dependencies:**
- `module_dependencies: ["auth"]` - wymaga auth module
- `module_dependencies: ["tenants"]` - opcjonalnie (tylko dla tenant management)

**Python dependencies:**
- Brak dodatkowych (używa istniejących modułów)

**Environment variables:**
- Brak dodatkowych

### Uwagi implementacyjne

1. **Authorization:**
   - Wszystkie endpoints wymagają `is_admin = true`
   - Używać `require_admin` dependency w routerze

2. **Paginacja:**
   - Wspólny pattern paginacji (może być w `app/core/pagination.py`)
   - Query params: `page` (default: 1), `limit` (default: 20, max: 100)

3. **Filtrowanie i wyszukiwanie:**
   - Search w `name` i `email` dla users
   - Search w `name` i `slug` dla tenants
   - Filtry: `is_active`, `is_admin` (dla users)

4. **Audit logging (P2):**
   - Opcjonalnie logować wszystkie akcje admin
   - Używać `logs` module jeśli dostępny

5. **Soft delete:**
   - Rozważyć soft delete zamiast hard delete (dla users i tenants)
   - Dodanie `deleted_at` do modeli

6. **Rate limiting:**
   - Rate limiting dla admin endpoints (np. 100 req/min)
   - Używać SlowAPI lub podobne

---

## 🔗 Zależności między modułami

```
admin
├── auth (wymagane)
└── tenants (opcjonalne - tylko dla tenant management)

oauth
└── auth (wymagane)

tenants
└── auth (wymagane)
```

---

## 📋 Priorytetyzacja implementacji

### P0 - Wysoki priorytet
1. **Multi-Tenancy (`tenants` module)**
   - Kluczowa funkcja dla SaaS aplikacji
   - Podstawa dla innych funkcji

2. **OAuth (`oauth` module)**
   - Najpierw Google OAuth
   - Potem GitHub OAuth

### P1 - Średni priorytet
3. **Admin Panel (`admin` module)**
   - User management (wymaga auth)
   - Tenant management (wymaga auth + tenants)

### P2 - Niski priorytet
- Dodatkowe OAuth providers (Microsoft, Apple)
- Audit logging dla admin panel
- Zaawansowane filtry i wyszukiwanie
- Bulk operations
- Export danych (CSV, Excel)

---

## 📝 Uwagi techniczne

### Migracje Alembic
- Każdy moduł powinien mieć własne migracje
- Migracje w `alembic/versions/` z prefiksem modułu (np. `001_tenants_initial.py`)

### Testy
- Każdy moduł powinien mieć testy w `tests/modules/<module_name>/`
- Testy jednostkowe dla service layer
- Testy integracyjne dla router endpoints

### Dokumentacja
- Każdy moduł powinien mieć `README.md` z:
  - Opisem funkcjonalności
  - Przykładami użycia
  - Konfiguracją environment variables
  - Przykładami API requests

### Registry.json
- Każdy moduł musi być dodany do `registry.json`
- Określić zależności modułów i Python packages
- Określić environment variables

---

## 🎯 Następne kroki

1. **Faza 1: Multi-Tenancy**
   - Implementacja `tenants` module
   - Modyfikacja `auth` module (JWT payload z `tid` i `trol`)
   - Testy i dokumentacja

2. **Faza 2: OAuth**
   - Implementacja `oauth` module z Google provider
   - Implementacja GitHub provider
   - Testy i dokumentacja

3. **Faza 3: Admin Panel**
   - Implementacja `admin` module (user management)
   - Integracja z `tenants` module (tenant management)
   - Testy i dokumentacja

---

_Last updated: 2025-01-XX_


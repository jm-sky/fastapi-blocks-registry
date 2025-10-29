# FastAPI Backend Application

This directory contains the core FastAPI backend application code.

## 📁 Directory Structure

```
app/
├── __init__.py           # Application package initialization
├── api/                  # API layer
│   ├── router.py        # Main API router (includes all module routers)
│   └── __init__.py
├── core/                 # Core application components
│   ├── config.py        # Application configuration (Pydantic Settings)
│   ├── database.py      # Database connection and session management
│   ├── deps.py          # Common FastAPI dependencies
│   └── __init__.py
├── exceptions/           # Global exception handlers
│   ├── handlers.py      # Exception handler implementations
│   └── __init__.py
└── modules/              # Feature modules
    └── <module_name>/   # Individual modules (auth, users, etc.)
        ├── __init__.py
        ├── models.py    # Data models (SQLAlchemy/Pydantic)
        ├── schemas.py   # Request/response schemas
        ├── router.py    # Module endpoints
        ├── service.py   # Business logic
        ├── dependencies.py  # Module-specific dependencies
        └── exceptions.py    # Module-specific exceptions
```

## 🧩 Module Structure

Each module in `app/modules/` follows a consistent layered architecture:

### Layer Responsibilities

1. **`router.py`** - API Layer
   - Defines HTTP endpoints
   - Handles request/response
   - Minimal business logic
   - Uses dependencies for auth, validation, etc.

2. **`schemas.py`** - Validation Layer
   - Request schemas (data from client)
   - Response schemas (data to client)
   - Uses Pydantic for validation
   - Data transformation/serialization

3. **`service.py`** - Business Logic Layer
   - Core business logic
   - Orchestrates operations
   - Independent of HTTP/REST
   - Reusable across different interfaces

4. **`models.py`** - Data Layer
   - Database models (SQLAlchemy)
   - Domain models (Pydantic)
   - Data structures

5. **`dependencies.py`** - Dependency Injection
   - FastAPI dependencies
   - Authentication/authorization
   - Database sessions
   - Common validations

6. **`exceptions.py`** - Error Handling
   - Module-specific exceptions
   - Business rule violations
   - Domain errors

## 🔧 Core Components

### Configuration (`core/config.py`)

Application settings using Pydantic Settings:
- Environment-based configuration
- Type-safe settings
- Validation on startup
- `.env` file support

```python
from app.core.config import settings

# Access configuration
secret_key = settings.secret_key
debug_mode = settings.debug
```

### Database (`core/database.py`)

Database connection and session management:
- SQLAlchemy async engine
- Session factory
- Connection pooling

```python
from app.core.database import get_db

# Use in endpoints
@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### Dependencies (`core/deps.py`)

Common FastAPI dependencies:
- Database session injection
- Current user retrieval
- Authorization checks
- Common validations

```python
from app.core.deps import get_current_user

@router.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    return user
```

### Exception Handlers (`exceptions/handlers.py`)

Global exception handling:
- Converts exceptions to HTTP responses
- Standardized error format
- Logging
- Debug information

## 🛠️ Adding New Modules

### Using the CLI (Recommended)

```bash
# Add a pre-built module
fastapi-registry add auth
fastapi-registry add users
```

### Manual Creation

1. Create module directory: `mkdir app/modules/mymodule`
2. Create required files:
   ```bash
   touch app/modules/mymodule/__init__.py
   touch app/modules/mymodule/router.py
   touch app/modules/mymodule/schemas.py
   touch app/modules/mymodule/service.py
   ```

3. Implement the module following the structure above

4. Register router in `app/api/router.py`:
   ```python
   from app.modules.mymodule.router import router as mymodule_router
   
   api_router.include_router(
       mymodule_router,
       prefix="/mymodule",
       tags=["mymodule"]
   )
   ```

## 📝 Best Practices

### 1. Keep Routers Thin
```python
# ❌ Bad - business logic in router
@router.post("/users")
async def create_user(data: UserCreate, db: Session = Depends(get_db)):
    # Validate email
    # Hash password
    # Save to database
    # Send welcome email
    # etc...
    pass

# ✅ Good - delegate to service
@router.post("/users")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(data)
```

### 2. Use Type Hints
```python
# ✅ Good - full type hints
async def get_user(user_id: int, db: Session) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
```

### 3. Use Pydantic Schemas
```python
# ✅ Good - validated input/output
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str

@router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate):
    # Automatic validation + documentation
    pass
```

### 4. Handle Exceptions Properly
```python
# ✅ Good - specific exceptions
from app.modules.auth.exceptions import InvalidCredentialsError

async def login(email: str, password: str) -> User:
    user = await get_user_by_email(email)
    if not user or not verify_password(password, user.password):
        raise InvalidCredentialsError("Invalid email or password")
    return user
```

### 5. Use Dependencies for Reusable Logic
```python
# ✅ Good - reusable dependency
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Use in multiple endpoints
@router.get("/profile")
async def profile(user: User = Depends(get_current_active_user)):
    return user
```

## 🔒 Security Considerations

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use environment variables** for secrets
3. **Hash passwords** before storing (use bcrypt/passlib)
4. **Validate input** with Pydantic schemas
5. **Use dependencies** for authentication/authorization
6. **Enable CORS** carefully (configure allowed origins)
7. **Rate limiting** for public endpoints
8. **SQL injection protection** (use ORM, avoid raw SQL)

## 🧪 Testing

Structure tests to mirror the `app/` directory:

```
tests/
├── conftest.py           # Test fixtures
├── test_api/
│   └── test_router.py
├── test_core/
│   ├── test_config.py
│   └── test_database.py
└── test_modules/
    └── test_auth/
        ├── test_router.py
        ├── test_service.py
        └── test_schemas.py
```

Run tests:
```bash
pytest
pytest --cov=app  # With coverage
```

## 📚 Common Patterns

### Pagination
```python
from fastapi import Query

@router.get("/items")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    return service.get_items(skip=skip, limit=limit)
```

### Filtering
```python
@router.get("/items")
async def list_items(
    status: str | None = None,
    category: str | None = None
):
    return service.get_items(status=status, category=category)
```

### Async Operations
```python
# Use async/await for I/O operations
async def send_email(to: str, subject: str, body: str) -> None:
    async with aiohttp.ClientSession() as session:
        await session.post(email_service_url, json={...})
```

## 🔍 Debugging

Enable debug mode in `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
# Application logs
tail -f logs/app.log

# SQL queries (set DATABASE_ECHO=true)
# Requests/responses (DEBUG=true)
```

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## 🤝 Contributing

When adding new features:
1. Follow the module structure
2. Add type hints
3. Write tests
4. Update documentation
5. Follow code style (ruff/black)

---

Generated by [FastAPI Blocks Registry](https://github.com/jm-sky/fastapi-blocks-registry)


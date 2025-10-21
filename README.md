# 🧩 FastAPI Blocks Registry

A modular scaffolding system for FastAPI backends, inspired by **shadcn-vue**.
Add production-ready modules (like `auth`, `users`, `billing`) to your FastAPI project with a single CLI command.

## 🎯 Project Goal

FastAPI Blocks Registry allows you to quickly add complete, production-ready modules to your FastAPI projects. Each module includes models, schemas, routers, services, and all necessary configurations - just copy and customize.

Unlike traditional packages, modules are copied directly into your project, giving you full control to modify and adapt them to your needs.

## ✨ Features

- 📦 **Copy, not install** - Modules are copied into your project for full customization
- 🔧 **Auto-configuration** - Automatically updates `main.py`, `requirements.txt`, and `.env`
- 🎨 **Production-ready** - Each module follows best practices and includes proper error handling
- 🔒 **Type-safe** - Full type hints and Pydantic validation
- 📚 **Well-documented** - Clear code structure with docstrings
- 🚀 **Quick start** - Get authentication, user management, and more in seconds

## 🚀 Quick Start

### Installation

```bash
# Install from source (for development)
pip install -e .

# Or install from PyPI (when published)
pip install fastapi-blocks-registry
```

### Usage

```bash
# List available modules
fastapi-registry list

# Show module details
fastapi-registry info auth

# Add a module to your project
fastapi-registry add auth

# Remove a module
fastapi-registry remove auth
```

### What Gets Installed

When you add a module, the CLI automatically:
- ✅ Copies module files to `app/modules/<module>/`
- ✅ Updates `main.py` to register the router
- ✅ Adds dependencies to `requirements.txt`
- ✅ Adds environment variables to `.env`

## 📦 Available Modules

### Auth Module

Complete JWT-based authentication system with:
- User registration with password strength validation
- Login with JWT access and refresh tokens
- Password reset flow
- Password change for authenticated users
- Token blacklisting support

**Endpoints:**
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `POST /api/v1/auth/change-password` - Change password (authenticated)
- `GET /api/v1/auth/me` - Get current user info

**Technologies:**
- PyJWT for token management
- Passlib + bcrypt for password hashing
- Pydantic for validation
- In-memory user store (easily replaceable with database)

## 🏗️ Project Structure

```
fastapi-blocks-registry/
├── fastapi_registry/
│   ├── __init__.py
│   ├── cli.py                  # CLI implementation
│   ├── registry.json           # Module registry
│   ├── core/
│   │   ├── file_utils.py       # File operations
│   │   ├── installer.py        # Module installer
│   │   └── registry_manager.py # Registry management
│   └── modules/
│       └── auth/               # Auth module
│           ├── __init__.py
│           ├── models.py       # User model & store
│           ├── schemas.py      # Pydantic schemas
│           ├── router.py       # FastAPI routes
│           ├── service.py      # Business logic
│           ├── dependencies.py # FastAPI dependencies
│           ├── auth_utils.py   # JWT & password utils
│           └── exceptions.py   # Custom exceptions
├── tests/
├── docs/
├── CLAUDE.md                   # Development guidelines
├── README.md
└── pyproject.toml
```

## 🧠 Module Structure

Each module follows a consistent structure:

- **`models.py`** - Data models (Pydantic or SQLAlchemy)
- **`schemas.py`** - Request/response schemas with validation
- **`router.py`** - FastAPI route definitions
- **`service.py`** - Business logic layer
- **`dependencies.py`** - FastAPI dependency injection
- **`exceptions.py`** - Module-specific exceptions
- **`__init__.py`** - Module initialization

## 💻 Example Usage

### 1. Add the auth module to your project

```bash
cd your-fastapi-project
fastapi-registry add auth
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Edit your `.env` file:
```bash
SECRET_KEY=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=30
REFRESH_TOKEN_EXPIRES_DAYS=7
```

### 4. Start your server

```bash
uvicorn main:app --reload
```

### 5. Test the endpoints

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Test123!@#",
    "name": "Test User"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Test123!@#"
  }'
```

## 🔧 CLI Commands

### `fastapi-registry list`
Display all available modules from the registry

### `fastapi-registry info <module>`
Show detailed information about a specific module

### `fastapi-registry add <module>`
Add a module to your project:
- Copies module files to `app/modules/<module>/`
- Updates `main.py` with router registration
- Adds dependencies to `requirements.txt`
- Adds environment variables to `.env`

### `fastapi-registry remove <module>`
Remove a module from your project (manual cleanup required for dependencies)

### `fastapi-registry version`
Show version information

## 🛠️ Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/fastapi-blocks-registry
cd fastapi-blocks-registry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy fastapi_registry
```

## 🔮 Roadmap

- [x] CLI implementation with Typer
- [x] Auth module with JWT
- [x] Auto-configuration system
- [ ] Users module with RBAC
- [ ] Database integration (SQLAlchemy)
- [ ] Alembic migrations support
- [ ] Email module
- [ ] Billing/subscription module
- [ ] Projects/workspaces module
- [ ] Remote registry support (GitHub)
- [ ] PyPI publication
- [ ] Module templates generator
- [ ] Test generation for modules

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT

## 🙏 Inspiration

This project is inspired by:
- [shadcn-vue](https://github.com/shadcn-ui/ui) - Copy, don't install philosophy
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Typer](https://typer.tiangolo.com/) - CLI framework by the creator of FastAPI

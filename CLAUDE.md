# FastAPI Blocks Registry - Development Guidelines

## Project Overview

This is a modular scaffolding system for FastAPI backends, inspired by shadcn-vue. It allows developers to add complete, production-ready modules (like `auth`, `users`, `billing`) to their FastAPI projects with a single CLI command.

## Architecture Overview (Updated 2025-10-30)

This project uses a **Mirror Target Structure** approach where the registry structure mirrors the end-user project structure exactly. This enables:
- Full IDE support (syntax highlighting, type checking, autocomplete)
- Local testing of modules in example_project
- Direct file copying without complex transformations
- Clear understanding of where files will be placed

### Registry Structure

```
fastapi-blocks-registry/
├── fastapi_registry/
│   ├── example_project/      # Complete working FastAPI project
│   │   ├── main.py           # Real Python files (not templates!)
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── core/         # Core utilities (config, database, etc.)
│   │   │   ├── modules/      # Feature modules
│   │   │   │   ├── auth/     # ← Modules here (1:1 with target)
│   │   │   │   └── users/
│   │   │   ├── api/
│   │   │   └── exceptions/
│   │   └── tests/
│   ├── templates_j2/         # ONLY files with variables
│   │   ├── README.md.j2      # Has {project_name}
│   │   ├── env.j2            # Has {secret_key}
│   │   └── config.py.j2      # Has {project_name}
│   ├── core/                 # CLI logic
│   │   ├── installer.py
│   │   ├── project_initializer.py
│   │   └── registry_manager.py
│   ├── cli.py
│   └── registry.json
```

**Key Insight:** ~85% of files don't need templating! Only use `.j2` templates for files that truly need variable substitution.

## Architecture Principles

### 1. Module Structure
Each module follows a consistent structure based on proven patterns from the saas-fastapi-react-boilerplate:

```
example_project/app/modules/auth/
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas (request/response DTOs)
├── router.py          # FastAPI route handlers
├── service.py         # Business logic layer
├── dependencies.py    # FastAPI dependencies (DI)
├── exceptions.py      # Module-specific exceptions
└── __init__.py        # Module initialization
```

**Location in registry:** `fastapi_registry/example_project/app/modules/auth/`
**Location in user project:** `{user_project}/app/modules/auth/` (1:1 match!)

### 2. Core Design Patterns

**Factory Pattern for App Creation**
- Use factory functions to create and configure FastAPI app instances
- Allow modules to register middleware, exception handlers, and event handlers
- Enable modular app composition

**Service Layer Architecture**
- Keep business logic in service classes/functions
- API routes should be thin, delegating to services
- Services handle validation, business rules, and orchestration

**Dependency Injection**
- Leverage FastAPI's DI system extensively
- Create type aliases for common dependencies (e.g., `CurrentUser`, `DBSession`)
- Centralize dependency definitions in `dependencies.py`

**Configuration Management**
- Use Pydantic Settings with nested configuration classes
- Support environment variables with proper validation
- Each module defines its own settings class that can be merged into main config

**Exception Hierarchy**
- Custom exceptions inherit from base exceptions
- Map exceptions to HTTP status codes globally
- Provide consistent error response format

### 3. Code Quality Standards

**Type Hints**
- All functions and methods must have complete type hints
- Use modern Python typing features (Python 3.11+)
- Leverage Pydantic for runtime validation

**Async/Await**
- Use async endpoints for I/O operations
- Keep blocking operations in background tasks or thread pools
- Be thread-safe when using shared state

**Documentation**
- Docstrings for all public functions, classes, and modules
- Use FastAPI's automatic documentation features
- Include examples in docstrings

**Testing**
- Write pytest tests for all modules
- Test happy paths and error cases
- Use async test support (`pytest-asyncio`)

### 4. Module Independence

Each module must be:
- **Self-contained**: Can be copied into a project and work immediately
- **Configurable**: Settings exposed via environment variables
- **Documented**: Clear README with setup instructions
- **Tested**: Include test files and examples
- **Dependency-explicit**: List all required packages in module.json

### 5. Security Best Practices

**Authentication & Authorization**
- Use JWT tokens with reasonable expiration times
- Implement refresh token rotation
- Hash passwords with bcrypt (min cost factor 12)
- Validate password strength

**Rate Limiting**
- Apply rate limits to sensitive endpoints
- Use SlowAPI or similar middleware
- Configure per-endpoint limits

**Input Validation**
- Validate all inputs with Pydantic schemas
- Sanitize user inputs
- Use proper HTTP status codes for validation errors

**Secret Management**
- Never commit secrets to git
- Use environment variables for sensitive config
- Validate secret key strength (min 32 chars, high entropy)

### 6. Database Patterns

**ORM Usage**
- Use SQLAlchemy 2.0+ with async support
- Define models with proper relationships
- Use Alembic for migrations

**Model Organization**
- One model per file or grouped by domain
- Use mixins for common fields (id, created_at, updated_at)
- Define proper indexes and constraints

**Query Optimization**
- Use eager loading for relationships when needed
- Add database indexes for frequently queried fields
- Use pagination for list endpoints

### 7. API Design Standards

**RESTful Conventions**
- Use standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Proper status codes (200, 201, 204, 400, 401, 403, 404, 409, 422, 500)
- Consistent URL patterns (`/api/v1/resource`)

**Request/Response Format**
- Use Pydantic schemas for all requests and responses
- Support camelCase for frontend compatibility (configurable)
- Include metadata in list responses (total, page, limit)

**Versioning**
- Use URL path versioning (`/api/v1/`)
- Maintain backward compatibility when possible
- Document breaking changes

### 8. CLI Development

**Typer Framework**
- Use Typer for CLI commands
- Provide helpful error messages
- Support dry-run mode for destructive operations

**Commands to Implement**
- `list` - Show available modules
- `add <module>` - Install a module
- `remove <module>` - Uninstall a module
- `info <module>` - Show module details
- `init` - Initialize a new FastAPI project structure

**User Experience**
- Colorful output with rich/typer
- Progress indicators for long operations
- Confirmation prompts for destructive actions
- Detailed logs in verbose mode

### 9. Module Registry Format

**registry.json Structure**
```json
{
  "module_name": {
    "name": "Human-readable Name",
    "description": "What this module does",
    "version": "1.0.0",
    "path": "modules/module_name",
    "dependencies": ["package1", "package2"],
    "python_version": ">=3.11",
    "env": {
      "VAR_NAME": "default_value"
    },
    "settings_class": "ModuleSettings",
    "router_prefix": "/api/v1/prefix",
    "tags": ["tag1", "tag2"]
  }
}
```

### 10. File Operations

**Safe File Manipulation**
- Always check if files exist before writing
- Create backups before modifying existing files
- Use pathlib for cross-platform path handling
- Validate directory structure before operations

**Project Integration**
- Detect existing FastAPI project structure
- Update main.py safely (AST manipulation or markers)
- Merge requirements.txt without duplicates
- Update .env without overwriting existing values

## Development Workflow

### Local CLI Development & Testing

To run the CLI locally during development without publishing to PyPI:

```bash
source .venv/bin/activate
pip install -e .
fastapi-registry --help
fastapi-registry list
```

Changes to the code are immediately reflected without reinstalling. For testing guide see [docs/LOCAL_TESTING.md](docs/LOCAL_TESTING.md).

### Module Development Workflow

1. **Module Development**
   - Create module in `fastapi_registry/example_project/app/modules/`
   - Follow the standard module structure
   - Add tests in module directory
   - Test the module locally in example_project (can import and run!)

2. **Registry Update**
   - Add module metadata to `registry.json`
   - Update `path` to point to `example_project/app/modules/your_module`
   - Specify all dependencies and environment variables
   - Set appropriate version

3. **CLI Testing**
   - Test `add` command on a sample project
   - Verify all files are copied correctly
   - Check that dependencies are installed
   - Ensure environment variables are documented

4. **Documentation**
   - Update main README with new module
   - Add usage examples
   - Document configuration options

## Technology Stack

### Core
- Python 3.12+
- FastAPI 0.118+
- Pydantic 2.11+
- SQLAlchemy 2.0+
- Typer (CLI framework)

### Authentication
- PyJWT
- Passlib + bcrypt
- python-jose

### Database
- Alembic (migrations)
- asyncpg (PostgreSQL async)
- aiosqlite (SQLite async)

### Development
- pytest + pytest-asyncio
- black (code formatting)
- ruff (linting)
- mypy (type checking)

## Project Structure

```
fastapi-blocks-registry/
├── fastapi_registry/           # Main package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── registry.json           # Module registry
│   ├── modules/                # Module templates
│   │   ├── auth/
│   │   ├── users/
│   │   └── ...
│   ├── core/                   # Core utilities
│   │   ├── installer.py        # Module installation logic
│   │   ├── registry_manager.py # Registry operations
│   │   └── file_utils.py       # File manipulation helpers
│   └── templates/              # Project templates
│       └── fastapi_project/    # Base FastAPI project template
├── tests/                      # Test suite
├── docs/                       # Documentation
├── examples/                   # Example projects
├── requirements.txt            # Package dependencies
├── pyproject.toml             # Package configuration
├── README.md
└── CLAUDE.md                  # This file
```

## Contributing Guidelines

1. Follow PEP 8 style guide
2. Write comprehensive docstrings
3. Add tests for new features
4. Update documentation
5. Use type hints everywhere
6. Keep modules independent
7. Ensure backward compatibility

## Useful Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [shadcn-vue](https://github.com/shadcn-ui/ui) - Inspiration for this project
- Zapamiętaj aby aktywować Pythons virtual environment z katalogu .venv
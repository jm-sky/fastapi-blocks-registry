# Django-like Management Commands for FastAPI Projects

## Overview

This document describes the implementation of Django-inspired management commands for FastAPI projects initialized with `fastapi-registry`. The goal is to provide a `cli.py` file in the user's project that offers convenient management commands similar to Django's `manage.py`.

## Architecture

### User Experience

When a user initializes a new FastAPI project with:
```bash
fastapi-registry init
```

They will receive a modular CLI package with two entry points:

**Option 1: Wrapper script (recommended)**
```bash
python cli.py --help
python cli.py users create
python cli.py users list
```

**Option 2: Module execution**
```bash
python -m cli --help
python -m cli users create
python -m cli users list
```

Both methods are equivalent - use whichever you prefer!

### Project Structure

```
user-project/
├── cli.py                    # ← Wrapper script (python cli.py)
├── cli/                      # ← CLI package (modular structure)
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Module entry point (python -m cli)
│   ├── main.py              # Main Typer app configuration
│   ├── utils.py             # Validators, formatters, helpers
│   └── commands/            # Command groups
│       ├── __init__.py
│       └── users.py         # User management commands
├── main.py                  # FastAPI application entry point
├── app/
│   ├── core/
│   │   ├── database.py      # Database connection & session
│   │   └── config.py
│   ├── modules/
│   │   ├── auth/            # Installed via: fastapi-registry add auth
│   │   │   ├── models.py    # User model with isAdmin field
│   │   │   ├── db_models.py # SQLAlchemy UserDB with is_admin
│   │   │   ├── repositories.py
│   │   │   └── ...
│   │   └── users/           # Optional
│   └── ...
├── requirements.txt
└── .env
```

## CLI Architecture

The CLI is built with a modular architecture for scalability and maintainability:

### Module Structure

```
cli/
├── __init__.py              # Package initialization, register commands
├── __main__.py              # Entry point for: python -m cli
├── main.py                  # Main Typer app configuration
├── utils.py                 # Shared utilities (validators, formatters)
└── commands/                # Command groups
    ├── __init__.py          # Export command apps
    └── users.py             # User management commands
```

### Design Principles

1. **Separation of Concerns**: Each command group in its own module
2. **Reusable Utilities**: Validators and formatters in `utils.py`
3. **Easy Extension**: Add new command groups by creating new files in `commands/`
4. **Two Entry Points**:
   - `python cli.py` (wrapper - simple and direct)
   - `python -m cli` (module execution - Pythonic)

### Adding New Commands

To add a new command group (e.g., `db` commands):

1. Create `cli/commands/db.py`:
```python
import typer

db_app = typer.Typer(name="db", help="Database operations")

@db_app.command("migrate")
def db_migrate():
    """Run database migrations."""
    # Implementation
```

2. Export in `cli/commands/__init__.py`:
```python
from .users import users_app
from .db import db_app  # Add this

__all__ = ["users_app", "db_app"]  # Add to exports
```

3. Register in `cli/__init__.py`:
```python
from .commands import users_app, db_app  # Import

app.add_typer(users_app, name="users")
app.add_typer(db_app, name="db")  # Register
```

## Command Categories

### 1. User Management Commands

#### `users create`
Create a new user interactively with rich prompts and validation.

**Usage:**
```bash
python cli.py users create
python cli.py users create --email admin@example.com --name "Admin User" --admin
python cli.py users create --no-input --email test@example.com --name "Test" --password "SecurePass123!"
```

**Features:**
- Interactive prompts with validation
- Hidden password input
- Password strength validation (min 8 chars, uppercase, lowercase, digit)
- Email format validation
- Admin privilege selection
- Confirmation before creation
- Rich UI with panels and colored output
- Spinner during database operations

**Options:**
- `--email, -e`: User email address
- `--name, -n`: User full name
- `--password`: User password (prompts if not provided, more secure)
- `--admin, -a`: Create as administrator
- `--no-input`: Skip interactive prompts (requires all options)

#### `users list`
List all users in a beautiful table with filters.

**Usage:**
```bash
python cli.py users list
python cli.py users list --admins         # Show only administrators
python cli.py users list --users          # Show only regular users
python cli.py users list --active         # Show only active users
python cli.py users list --inactive       # Show only inactive users
python cli.py users list --limit 10       # Limit to 10 users
```

**Features:**
- Beautiful Rich table with colors
- Columns: ID (truncated), Email, Name, Role, Status, Created
- Color-coded roles (Admin in yellow, User in dim)
- Color-coded status (Active in green, Inactive in red)
- Filters for admin/user status
- Filters for active/inactive status
- Limit option for large datasets
- Spinner during data loading

**Options:**
- `--admins`: Show only administrators
- `--users`: Show only regular users
- `--active`: Show only active users
- `--inactive`: Show only inactive users
- `--limit, -l`: Maximum number of users to show

#### `users delete`
Delete a user by email or ID with confirmation.

**Usage:**
```bash
python cli.py users delete
python cli.py users delete user@example.com
python cli.py users delete <user-id>
python cli.py users delete user@example.com --yes    # Skip confirmation
```

**Features:**
- Search by email or ID
- Display user details before deletion
- Confirmation prompt with warning
- Cannot undo warning
- Spinner during deletion
- Graceful error handling if user not found

**Options:**
- `identifier`: User email or ID to delete (can be prompted)
- `--yes, -y`: Skip confirmation prompt

#### `users set-admin` (Future)
Set or remove admin privileges for a user.

**Usage:**
```bash
python cli.py users set-admin user@example.com --admin
python cli.py users set-admin user@example.com --no-admin
```

### 2. Database Commands (Future)

#### `db init`
Initialize database tables.

```bash
python cli.py db init
```

#### `db migrate`
Run database migrations (if Alembic is set up).

```bash
python cli.py db migrate
python cli.py db migrate --message "Add user role field"
```

#### `db reset`
Reset database (drop all tables and recreate).

```bash
python cli.py db reset
python cli.py db reset --yes    # Skip confirmation
```

### 3. Development Commands (Future)

#### `shell`
Start an interactive Python shell with application context.

```bash
python cli.py shell
```

Provides access to:
- Database session
- All models
- Repositories
- Config

#### `check`
Check project configuration and dependencies.

```bash
python cli.py check
```

Validates:
- Database connection
- Environment variables
- Required modules
- Dependencies

## Technical Implementation

### Technology Stack

**CLI Framework:**
- **Typer** (v0.20.0+): CLI framework with type hints
- **Rich** (v14.2.0+): Beautiful terminal output

**Features:**
- Colored output
- Progress spinners
- Tables and panels
- Interactive prompts (with Typer + Rich integration)
- Hidden password input

### Design Patterns

#### 1. Modular Command Groups
Commands are organized into groups using Typer sub-apps:

```python
# cli/commands/users.py
users_app = typer.Typer(name="users", help="User management")

@users_app.command("create")
def users_create(...):
    """Create a new user."""
    asyncio.run(_users_create_async(...))
```

#### 2. Async/Sync Separation
Public commands are sync, implementation is async:

```python
# Public API (sync for Typer)
@users_app.command("create")
def users_create(email: str, ...):
    asyncio.run(_users_create_async(email, ...))

# Implementation (async for database)
async def _users_create_async(email: str, ...):
    async for db in get_db():
        repo = UserRepository(db)
        await repo.create_user(...)
```

#### 3. Repository Pattern
Commands use the project's existing repository layer:

```python
from app.modules.auth.repositories import UserRepository
from app.core.database import get_db

async for db in get_db():
    repo = UserRepository(db)
    users = await repo.get_all_users()
```

#### 4. Shared Utilities
Reusable functions in `utils.py`:

```python
# cli/utils.py
def validate_email(email: str) -> bool:
    """Validate email format."""
    ...

def format_user_role(is_admin: bool) -> str:
    """Format role with color."""
    return "[yellow]Admin[/yellow]" if is_admin else "[dim]User[/dim]"
```

### Project Integration

#### During `fastapi-registry init`

The `cli.py` file is created with:
- Typer app configuration
- Import of Rich console
- Subcommands structure (users, db, etc.)
- Basic error handling
- Help text

#### During `fastapi-registry add auth`

The auth module installation:
1. Adds User model with `isAdmin` field
2. Adds UserDB SQLAlchemy model with `is_admin` column
3. Updates repository to support `is_admin` parameter
4. CLI commands automatically work with the installed module

### File Structure

**Registry structure:**
```
fastapi_registry/
├── example_project/
│   ├── cli.py               # ← Wrapper script (copied to user projects)
│   ├── cli/                 # ← CLI package (copied to user projects)
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── main.py
│   │   ├── utils.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── users.py
│   ├── main.py
│   └── app/
│       └── modules/
│           └── auth/
│               ├── models.py          # User with isAdmin
│               ├── db_models.py       # UserDB with is_admin
│               └── repositories.py    # create_user(is_admin=False)
└── templates_j2/
    └── (no CLI templates needed - direct copy)
```

**User project after init:**
```
my-project/
├── cli.py                   # ← Wrapper script (copied)
├── cli/                     # ← Full CLI package (copied)
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py
│   ├── utils.py
│   └── commands/
│       ├── __init__.py
│       └── users.py
├── main.py
└── ...
```

## User Model Updates

### Pydantic Model (`models.py`)
```python
class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    hashedPassword: str
    isActive: bool = True
    isAdmin: bool = False      # ← NEW
    createdAt: datetime
    resetToken: str | None = None
    resetTokenExpiry: datetime | None = None
```

### SQLAlchemy Model (`db_models.py`)
```python
class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # ← NEW
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    reset_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    reset_token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Repository Update (`repositories.py`)
```python
async def create_user(
    self,
    email: str,
    password: str,
    full_name: str,
    is_admin: bool = False  # ← NEW parameter
) -> User:
    user_db = UserDB(
        id=user_id,
        email=normalized_email,
        name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_admin=is_admin,  # ← NEW
        created_at=datetime.now(UTC)
    )
    # ...
```

## Best Practices (2025)

### CLI Development
1. **Rich for UI**: Use Rich for all terminal output
   - Colors: `[red]`, `[green]`, `[yellow]`, `[cyan]`, `[dim]`
   - Tables: `Table` with custom styling
   - Panels: `Panel` for grouped information
   - Spinners: `console.status()` with various spinner styles

2. **Typer for Structure**: Use Typer's features
   - Subcommands with `typer.Typer()`
   - Options with type hints and validation
   - Help text with docstrings
   - Auto-completion support

3. **Interactive Prompts**: Use Rich's Prompt and Confirm
   - `Prompt.ask()` for text input
   - `Prompt.ask(password=True)` for hidden input
   - `Confirm.ask()` for yes/no questions

4. **Error Handling**:
   - Try/except with helpful error messages
   - Exit codes: 0 for success, 1 for error, 130 for Ctrl+C
   - Graceful handling of missing modules
   - Clear validation error messages

5. **Async Support**:
   - Use `asyncio.run()` for async commands
   - Properly handle async database sessions
   - Clean up resources in finally blocks

### Security
1. **Password Handling**:
   - Never log passwords
   - Use hidden input for passwords
   - Validate password strength
   - Hash immediately after input

2. **Input Validation**:
   - Validate email format
   - Validate password strength (min 8 chars, complexity)
   - Sanitize user inputs
   - Use Pydantic for type validation

3. **Confirmation Prompts**:
   - Require confirmation for destructive operations
   - Show what will be affected
   - Provide `--yes` flag for automation

## Migration Guide

For users upgrading from previous versions:

1. **Add `is_admin` field to existing users table:**
   ```sql
   ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;
   ```

2. **Update Pydantic model** to include `isAdmin: bool = False`

3. **Update repository** to handle `is_admin` in create/update

4. **Add `cli.py`** to project root

## Examples

### Example Session: Creating Admin User

```bash
$ python cli.py users create

Create New User

Email address: admin@example.com
Full name: Admin User
Password: ********
Password (confirm): ********
Create as administrator? [y/N]: y

╭─── User Summary ────────────────────────────╮
│ Email: admin@example.com                     │
│ Name: Admin User                             │
│ Role: Administrator                          │
╰──────────────────────────────────────────────╯

Create this user? [Y/n]: y

⠋ Creating user...

✓ User created successfully!

╭─── User Details ─────────────────────────────╮
│ Email: admin@example.com                      │
│ Name: Admin User                              │
│ Role: Administrator                           │
│ Status: Active                                │
│ ID: 01HQXYZ123ABC456789DEFGH                  │
│ Created: 2025-11-03 14:30:00+00:00            │
╰───────────────────────────────────────────────╯
```

### Example Session: Listing Users

```bash
$ python cli.py users list

⠋ Loading users...

                    Users (3 total)
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ ID        ┃ Email             ┃ Name       ┃ Role    ┃ Status  ┃ Created          ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 01HQXY... │ admin@example.com │ Admin User │ Admin   │ Active  │ 2025-11-03 14:30 │
│ 01HQXZ... │ john@example.com  │ John Doe   │ User    │ Active  │ 2025-11-03 15:00 │
│ 01HQY0... │ jane@example.com  │ Jane Smith │ User    │ Active  │ 2025-11-03 15:15 │
└───────────┴───────────────────┴────────────┴─────────┴─────────┴──────────────────┘
```

### Example Session: Deleting User

```bash
$ python cli.py users delete john@example.com

⠋ Finding user...

User to delete:

╭────────────────────────────────────────────╮
│ ID: 01HQXZ123ABC456789DEFGH                │
│ Email: john@example.com                    │
│ Name: John Doe                             │
│ Role: User                                 │
│ Created: 2025-11-03 15:00:00+00:00         │
╰────────────────────────────────────────────╯

Warning: This action cannot be undone!

Are you sure you want to delete this user? [y/N]: y

⠋ Deleting user...

✓ User deleted successfully
```

## Testing Strategy

### Manual Testing
1. Test in a fresh project initialized with `fastapi-registry init`
2. Add auth module: `fastapi-registry add auth`
3. Test each command with various inputs
4. Test error cases (invalid email, weak password, etc.)
5. Test database persistence

### Automated Testing
1. Unit tests for command classes
2. Integration tests with test database
3. Mock tests for user interaction
4. Validation tests for input sanitization

## Future Enhancements

1. **User activation/deactivation**: `users activate`, `users deactivate`
2. **Password reset**: `users reset-password <email>`
3. **Role management**: `users set-role <email> <role>`
4. **Bulk operations**: `users import <csv>`, `users export`
5. **Search**: `users find <query>`
6. **Statistics**: `users stats`
7. **Alembic integration**: Automatic migrations
8. **Backup/restore**: Database backup commands
9. **Logs**: View application logs
10. **Config**: View/update configuration

## Dependencies

**Required in user project:**
```txt
typer[all]>=0.20.0
rich>=14.2.0
python-ulid>=2.7.0  # For user ID generation
```

These are included in the base project requirements when using `fastapi-registry init`.

## Conclusion

This Django-inspired management CLI provides a familiar and powerful interface for managing FastAPI projects. By leveraging modern Python CLI best practices (Typer, Rich, async support) and following the repository pattern already established in the project, it offers a seamless developer experience for common management tasks.

"""CLI package for FastAPI project management.

This package provides Django-inspired management commands for common
development and administration tasks.

Usage:
    python -m cli --help
    python -m cli users create
    python -m cli users list
    python -m cli users delete <email>

The CLI is organized into command groups:
- users: User management (create, list, delete)
- db: Database operations (future)
- shell: Interactive shell (future)
"""

from .main import app, main
from .commands import users_app

# Register command groups
app.add_typer(users_app, name="users")

__all__ = ["app", "main"]

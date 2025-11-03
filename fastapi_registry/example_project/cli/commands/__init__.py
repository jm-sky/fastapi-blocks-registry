"""CLI commands package.

This package contains all CLI command groups.
Each command group is defined in a separate module.
"""

from .users import users_app

__all__ = ["users_app"]

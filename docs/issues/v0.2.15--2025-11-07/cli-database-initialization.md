# CLI Database Initialization Issue

## Problem
When running CLI commands like `python -m cli users list`, the command fails with:
```
Error listing users: (sqlite3.OperationalError) unable to open database file
```
or
```
Error listing users: (sqlite3.OperationalError) no such table: users
```

## Root Causes

### 1. Missing Database Directory
The default SQLite database path is `./data/app.db`, but the `data/` directory may not exist, causing SQLite to fail when trying to create the database file.

### 2. Uninitialized Database Tables
Even if the database file exists, the tables may not be created. SQLAlchemy requires all models to be imported before calling `Base.metadata.create_all()`.

## Current Behavior
- CLI commands fail if database directory doesn't exist
- CLI commands fail if tables haven't been initialized
- No automatic database setup
- Users must manually create directory and initialize tables

## Recommendation

### Solution 1: Auto-create Database Directory (Recommended) ⭐

The CLI should automatically create the database directory if it doesn't exist.

**Implementation:**

In `backend/cli/commands/users.py` (or a shared utility):

```python
import os
from pathlib import Path
from app.core.config import settings

def ensure_database_directory() -> None:
    """Ensure database directory exists for SQLite."""
    db_url = settings.database.url
    
    # Check if using SQLite
    if db_url.startswith("sqlite"):
        # Extract path from SQLite URL (e.g., "sqlite+aiosqlite:///./data/app.db")
        if ":///" in db_url:
            # Absolute path
            db_path = Path(db_url.split(":///")[1])
        elif "://" in db_url:
            # Relative path
            db_path = Path(db_url.split("://")[1])
        else:
            db_path = Path(db_url)
        
        # Get directory
        db_dir = db_path.parent
        
        # Create directory if it doesn't exist
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created database directory:[/green] {db_dir}")
```

### Solution 2: Auto-initialize Database Tables

The CLI should automatically initialize database tables if they don't exist.

**Implementation:**

```python
import asyncio
from app.core.database import init_db, engine
from sqlalchemy import inspect

async def ensure_database_tables() -> None:
    """Ensure database tables exist, create them if missing."""
    # Import all models to register them with Base.metadata
    from app.modules.auth.db_models import UserDB
    from app.modules.logs.db_models import LogEntryDB
    # ... import other models as needed
    
    # Check if tables exist
    async with engine.begin() as conn:
        inspector = inspect(engine.sync_engine)
        existing_tables = inspector.get_table_names()
        
        # Check if users table exists (or any key table)
        if "users" not in existing_tables:
            # Initialize database
            await init_db()
            console.print("[green]Database tables initialized[/green]")
```

### Solution 3: Combined Helper Function

Create a utility function that handles both:

```python
# backend/cli/utils.py or backend/cli/commands/__init__.py

import asyncio
import os
from pathlib import Path
from app.core.config import settings
from app.core.database import init_db, engine
from sqlalchemy import inspect
from rich.console import Console

console = Console()

def ensure_database_setup() -> None:
    """Ensure database directory and tables exist."""
    # 1. Create database directory if needed
    db_url = settings.database.url
    if db_url.startswith("sqlite"):
        if ":///" in db_url:
            db_path = Path(db_url.split(":///")[1])
        elif "://" in db_url:
            db_path = Path(db_url.split("://")[1])
        else:
            db_path = Path(db_url)
        
        db_dir = db_path.parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[dim]Created database directory: {db_dir}[/dim]")
    
    # 2. Initialize tables if needed
    asyncio.run(_ensure_tables())

async def _ensure_tables() -> None:
    """Ensure database tables exist."""
    # Import all models to register them with Base.metadata
    # This is critical - all models must be imported before init_db()
    from app.modules.auth.db_models import UserDB
    from app.modules.logs.db_models import LogDB
    # Import other models as they are added to the project
    # from app.modules.two_factor.db_models import TotpConfigDB, PasskeyDB
    
    # Check if tables exist
    async with engine.begin() as conn:
        inspector = inspect(engine.sync_engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables or "users" not in existing_tables:
            await init_db()
            console.print("[dim]Database tables initialized[/dim]")
```

### Solution 4: CLI Command for Database Setup

Add a dedicated CLI command for database initialization:

```python
# backend/cli/commands/db.py

import typer
import asyncio
from rich.console import Console
from app.core.database import init_db
from app.modules.auth.db_models import UserDB
from app.modules.logs.db_models import LogEntryDB

db_app = typer.Typer(name="db", help="Database management commands")
console = Console()

@db_app.command("init")
def db_init() -> None:
    """Initialize database (create tables)."""
    asyncio.run(_db_init_async())

async def _db_init_async() -> None:
    """Async implementation of database initialization."""
    try:
        with console.status("[bold green]Initializing database...", spinner="dots"):
            await init_db()
        console.print("\n[bold green]✓[/bold green] Database initialized successfully\n")
    except Exception as e:
        console.print(f"\n[red]Error initializing database:[/red] {e}\n")
        raise typer.Exit(1)
```

Then call `ensure_database_setup()` at the start of CLI commands that need database access.

## Recommended Implementation

**Use Solution 3 (Combined Helper)** as the primary approach:

1. **Create utility function** `ensure_database_setup()` that:
   - Creates database directory if missing (for SQLite)
   - Imports all models
   - Checks if tables exist
   - Initializes tables if missing

2. **Call it at the start** of CLI commands that need database:
   ```python
   @users_app.command("list")
   def users_list(...):
       ensure_database_setup()  # ✅ Add this
       asyncio.run(_users_list_async(...))
   ```

3. **Optionally add CLI command** (Solution 4) for explicit initialization:
   ```bash
   python -m cli db init
   ```

## Complete Example

```python
# backend/cli/utils.py

import asyncio
import os
from pathlib import Path
from app.core.config import settings
from app.core.database import init_db, engine
from sqlalchemy import inspect
from rich.console import Console

console = Console()

def ensure_database_setup() -> None:
    """
    Ensure database is ready for use.
    
    - Creates database directory if missing (SQLite)
    - Initializes tables if they don't exist
    """
    # Create directory for SQLite
    db_url = settings.database.url
    if db_url.startswith("sqlite"):
        if ":///" in db_url:
            db_path = Path(db_url.split(":///")[1])
        elif "://" in db_url:
            db_path = Path(db_url.split("://")[1])
        else:
            db_path = Path(db_url)
        
        db_dir = db_path.parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize tables if needed
    asyncio.run(_ensure_tables())

async def _ensure_tables() -> None:
    """Ensure database tables exist."""
    # Import all models to register them with Base.metadata
    from app.modules.auth.db_models import UserDB
    from app.modules.logs.db_models import LogEntryDB
    # Import other models as they are added
    
    # Check if tables exist
    async with engine.begin() as conn:
        inspector = inspect(engine.sync_engine)
        existing_tables = inspector.get_table_names()
        
        # If no tables or key table missing, initialize
        if not existing_tables or "users" not in existing_tables:
            await init_db()
```

Then in `backend/cli/commands/users.py`:

```python
from ..utils import ensure_database_setup

@users_app.command("list")
def users_list(...):
    ensure_database_setup()  # ✅ Add this
    asyncio.run(_users_list_async(...))
```

## Impact
- ✅ CLI commands work out of the box
- ✅ No manual database setup required
- ✅ Better developer experience
- ✅ Automatic database initialization
- ✅ Works for both SQLite and PostgreSQL

## Testing

After implementation, verify:
1. `python -m cli users list` → Works without manual setup
2. Database directory is created automatically
3. Tables are created automatically
4. Works on fresh project setup

## Notes

- For PostgreSQL, directory creation is not needed (only SQLite)
- Table initialization should check if tables exist before creating (idempotent)
- All models must be imported before `init_db()` is called
- Consider adding a `python -m cli db init` command for explicit initialization


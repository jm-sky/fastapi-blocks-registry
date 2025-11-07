# CLI Should Show Help When No Arguments Provided

## Problem
When running `python -m cli` without any arguments, the CLI shows an error message instead of helpful information:

```
Usage: python -m cli [OPTIONS] COMMAND [ARGS]...
Try 'python -m cli --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ Missing command.                                                             │
╰──────────────────────────────────────────────────────────────────────────────╘
```

This is not user-friendly. Users expect to see help information when running a command without arguments, similar to how most CLI tools work (e.g., `git`, `docker`, `npm`).

## Current Behavior
- `python -m cli` → Shows error "Missing command"
- `python -m cli --help` → Shows help (correct)

## Expected Behavior
- `python -m cli` → Should show help automatically (same as `--help`)
- `python -m cli --help` → Shows help (unchanged)

## Recommendation

### Solution 1: Use `no_args_is_help=True` (Recommended) ⭐

Typer supports a `no_args_is_help` parameter that automatically shows help when no arguments are provided.

**Implementation:**

In `backend/cli/main.py` (or `backend/cli/app.py`):

```python
import typer
from rich.console import Console

# Initialize Typer app
app = typer.Typer(
    name="cli",
    help="Management CLI for FastAPI project - Django-inspired commands",
    add_completion=True,
    no_args_is_help=True,  # ✅ Add this - shows help when no args provided
)

# Initialize Rich console (shared across commands)
console = Console()

def main() -> None:
    """Main entry point for the CLI."""
    app()

if __name__ == "__main__":
    main()
```

### Solution 2: Custom Callback (Alternative)

If more control is needed, use a callback:

```python
import typer
from rich.console import Console
import sys

app = typer.Typer(
    name="cli",
    help="Management CLI for FastAPI project - Django-inspired commands",
    add_completion=True,
)

console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Main entry point for the CLI."""
    if ctx.invoked_subcommand is None:
        # No command provided, show help
        console.print(app.get_help(ctx))
        raise typer.Exit(0)

if __name__ == "__main__":
    app()
```

### Solution 3: Check Arguments in main() (Manual)

```python
import typer
import sys

app = typer.Typer(
    name="cli",
    help="Management CLI for FastAPI project - Django-inspired commands",
    add_completion=True,
)

def main() -> None:
    """Main entry point for the CLI."""
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        app(["--help"])
    else:
        app()

if __name__ == "__main__":
    main()
```

## Recommended Implementation

**Use Solution 1** (`no_args_is_help=True`) because:
- ✅ Simplest and cleanest solution
- ✅ Built-in Typer feature
- ✅ Consistent with Typer best practices
- ✅ No additional code needed
- ✅ Works automatically for all command groups

### Complete Example

```python
# backend/cli/main.py
"""Main CLI application.

This module configures the main Typer application and registers all command groups.
"""

import typer
from rich.console import Console

# Initialize Typer app
app = typer.Typer(
    name="cli",
    help="Management CLI for FastAPI project - Django-inspired commands",
    add_completion=True,
    no_args_is_help=True,  # Show help when no command provided
)

# Initialize Rich console (shared across commands)
console = Console()


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
```

## Impact
- ✅ Better user experience
- ✅ More intuitive CLI behavior
- ✅ Consistent with common CLI tools
- ✅ Reduces confusion for new users
- ✅ No breaking changes (existing commands still work)

## Testing

After implementation, verify:
1. `python -m cli` → Shows help (not error)
2. `python -m cli --help` → Shows help (unchanged)
3. `python -m cli users` → Shows help for users command (unchanged)
4. `python -m cli users create` → Works as before (unchanged)

## References
- Typer Documentation: https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-defaults
- The `no_args_is_help` parameter is a standard Typer feature


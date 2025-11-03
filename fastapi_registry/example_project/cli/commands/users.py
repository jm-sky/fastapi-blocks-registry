"""User management commands.

This module provides Django-like commands for creating, listing, and managing users.
"""

import asyncio
from typing import Any

import typer
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..utils import (
    format_user_role,
    format_user_status,
    truncate_id,
    validate_email,
    validate_password_strength,
)

# Create users subcommand app
users_app = typer.Typer(
    name="users",
    help="User management commands",
)


@users_app.command("create")
def users_create(
    email: str | None = typer.Option(None, "--email", "-e", help="User email address"),
    name: str | None = typer.Option(None, "--name", "-n", help="User full name"),
    password: str | None = typer.Option(
        None,
        "--password",
        help="User password (not recommended, will prompt if not provided)",
    ),
    admin: bool = typer.Option(False, "--admin", "-a", help="Create as administrator"),
    no_input: bool = typer.Option(
        False, "--no-input", help="Skip interactive prompts (requires all options)"
    ),
) -> None:
    """Create a new user interactively with rich prompts and validation.

    Examples:
        # Interactive mode (recommended)
        python -m cli users create

        # Create admin user
        python -m cli users create --admin

        # Non-interactive mode (for scripts)
        python -m cli users create --no-input \\
            --email admin@example.com \\
            --name "Admin User" \\
            --password "SecurePass123!" \\
            --admin
    """
    asyncio.run(_users_create_async(email, name, password, admin, no_input))


async def _users_create_async(
    email: str | None,
    name: str | None,
    password: str | None,
    admin: bool,
    no_input: bool,
) -> None:
    """Async implementation of user creation."""
    from rich.console import Console

    console = Console()
    console.print("\n[bold cyan]Create New User[/bold cyan]\n")

    # Get user details interactively if not provided
    email_value = await _get_email(console, email, no_input)
    name_value = await _get_name(console, name, no_input)
    password_value = await _get_password(console, password, no_input)
    is_admin = await _get_admin_status(console, admin, no_input)

    # Show summary
    _show_user_summary(console, email_value, name_value, is_admin)

    # Confirm creation
    if not no_input:
        if not Confirm.ask("\nCreate this user?", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Create user with spinner
    try:
        with console.status("[bold green]Creating user...", spinner="dots"):
            user = await _create_user_in_db(email_value, name_value, password_value, is_admin)

        # Show success message
        console.print("\n[bold green]✓[/bold green] User created successfully!\n")

        # Show user info panel
        user_info = f"""[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {'Administrator' if user['isAdmin'] else 'User'}
[bold]Status:[/bold] {'Active' if user['isActive'] else 'Inactive'}
[bold]ID:[/bold] {user['id']}
[bold]Created:[/bold] {user['createdAt']}"""

        panel = Panel(user_info, title="[bold]User Details[/bold]", border_style="green")
        console.print(panel)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error creating user:[/red] {e}\n")
        raise typer.Exit(1)


async def _get_email(console: Any, email: str | None, no_input: bool) -> str:
    """Get user email with validation."""
    if email and validate_email(email):
        return email

    if no_input:
        raise ValueError("Email is required when --no-input is used")

    while True:
        email_input = Prompt.ask("[cyan]Email address[/cyan]", default=email or "")

        if not email_input:
            console.print("[red]Email is required[/red]")
            continue

        if not validate_email(email_input):
            console.print("[red]Invalid email format[/red]")
            continue

        return email_input


async def _get_name(console: Any, name: str | None, no_input: bool) -> str:
    """Get user name."""
    if name:
        return name

    if no_input:
        raise ValueError("Name is required when --no-input is used")

    while True:
        name_input = Prompt.ask("[cyan]Full name[/cyan]", default=name or "")

        if not name_input:
            console.print("[red]Name is required[/red]")
            continue

        if len(name_input) < 2:
            console.print("[red]Name must be at least 2 characters[/red]")
            continue

        return name_input


async def _get_password(console: Any, password: str | None, no_input: bool) -> str:
    """Get user password with validation."""
    if password:
        # Validate provided password
        is_valid, error = validate_password_strength(password)
        if not is_valid:
            raise ValueError(f"Invalid password: {error}")
        return password

    if no_input:
        raise ValueError("Password is required when --no-input is used")

    while True:
        password_input = Prompt.ask("[cyan]Password[/cyan]", password=True)

        if not password_input:
            console.print("[red]Password is required[/red]")
            continue

        # Validate password strength
        is_valid, error = validate_password_strength(password_input)
        if not is_valid:
            console.print(f"[red]{error}[/red]")
            continue

        # Confirm password
        password_confirm = Prompt.ask("[cyan]Password (confirm)[/cyan]", password=True)

        if password_input != password_confirm:
            console.print("[red]Passwords do not match[/red]")
            continue

        return password_input


async def _get_admin_status(console: Any, admin: bool, no_input: bool) -> bool:
    """Get admin status."""
    if no_input:
        return admin

    return Confirm.ask("[cyan]Create as administrator?[/cyan]", default=admin)


def _show_user_summary(console: Any, email: str, name: str, is_admin: bool) -> None:
    """Show user creation summary."""
    summary = f"""[bold]Email:[/bold] {email}
[bold]Name:[/bold] {name}
[bold]Role:[/bold] {'Administrator' if is_admin else 'User'}"""

    panel = Panel(summary, title="[bold]User Summary[/bold]", border_style="cyan")
    console.print(panel)


async def _create_user_in_db(
    email: str, name: str, password: str, is_admin: bool
) -> dict[str, Any]:
    """Create user in database.

    Args:
        email: User email
        name: User name
        password: User password (will be hashed)
        is_admin: Whether user is admin

    Returns:
        dict: Created user data
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    # Get database session
    async for db in get_db():
        repo = UserRepository(db)

        try:
            # Create user
            user = await repo.create_user(
                email=email, password=password, full_name=name, is_admin=is_admin
            )

            # Convert to dict for display
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "isActive": user.isActive,
                "isAdmin": user.isAdmin,
                "createdAt": user.createdAt,
            }

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Failed to create user: {e}") from e


@users_app.command("list")
def users_list(
    admins_only: bool = typer.Option(False, "--admins", help="Show only administrators"),
    users_only: bool = typer.Option(False, "--users", help="Show only regular users"),
    active_only: bool = typer.Option(False, "--active", help="Show only active users"),
    inactive_only: bool = typer.Option(
        False, "--inactive", help="Show only inactive users"
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-l", help="Maximum number of users to show"
    ),
) -> None:
    """List all users in a beautiful table with filters.

    Examples:
        # List all users
        python -m cli users list

        # List only administrators
        python -m cli users list --admins

        # List first 10 active users
        python -m cli users list --active --limit 10
    """
    asyncio.run(
        _users_list_async(admins_only, users_only, active_only, inactive_only, limit)
    )


async def _users_list_async(
    admins_only: bool,
    users_only: bool,
    active_only: bool,
    inactive_only: bool,
    limit: int | None,
) -> None:
    """Async implementation of user listing."""
    from rich.console import Console

    console = Console()

    try:
        # Get users with spinner
        with console.status("[bold green]Loading users...", spinner="dots"):
            users = await _get_users_from_db()

        if not users:
            console.print("\n[yellow]No users found[/yellow]\n")
            return

        # Apply filters
        if admins_only:
            users = [u for u in users if u["isAdmin"]]
        elif users_only:
            users = [u for u in users if not u["isAdmin"]]

        if active_only:
            users = [u for u in users if u["isActive"]]
        elif inactive_only:
            users = [u for u in users if not u["isActive"]]

        # Apply limit
        if limit:
            users = users[:limit]

        if not users:
            console.print("\n[yellow]No users match the filters[/yellow]\n")
            return

        # Create table
        table = Table(
            title=f"[bold cyan]Users[/bold cyan] [dim]({len(users)} total)[/dim]",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Email", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Role", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Created", style="dim")

        for user in users:
            # Format date
            created = user["createdAt"].strftime("%Y-%m-%d %H:%M")

            table.add_row(
                truncate_id(user["id"]),
                user["email"],
                user["name"],
                format_user_role(user["isAdmin"]),
                format_user_status(user["isActive"]),
                created,
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error listing users:[/red] {e}\n")
        raise typer.Exit(1)


async def _get_users_from_db() -> list[dict[str, Any]]:
    """Get users from database.

    Returns:
        list[dict]: List of user data
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)
        users = await repo.get_all_users()

        # Convert to dict for display
        return [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "isActive": user.isActive,
                "isAdmin": user.isAdmin,
                "createdAt": user.createdAt,
            }
            for user in users
        ]

    return []


@users_app.command("delete")
def users_delete(
    identifier: str | None = typer.Argument(None, help="User email or ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a user by email or ID with confirmation.

    Examples:
        # Interactive mode (will prompt for email/ID)
        python -m cli users delete

        # Delete by email
        python -m cli users delete user@example.com

        # Delete by ID without confirmation
        python -m cli users delete 01HQX... --yes
    """
    asyncio.run(_users_delete_async(identifier, yes))


async def _users_delete_async(identifier: str | None, yes: bool) -> None:
    """Async implementation of user deletion."""
    from rich.console import Console

    console = Console()

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Show user info
        console.print("\n[bold yellow]User to delete:[/bold yellow]\n")

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {'Administrator' if user['isAdmin'] else 'User'}
[bold]Created:[/bold] {user['createdAt']}"""

        panel = Panel(user_info, border_style="yellow")
        console.print(panel)

        # Confirm deletion
        if not yes:
            console.print(
                "\n[bold red]Warning:[/bold red] This action cannot be undone!\n"
            )

            if not Confirm.ask(
                "Are you sure you want to delete this user?", default=False
            ):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete user
        with console.status("[bold red]Deleting user...", spinner="dots"):
            await _delete_user_from_db(user["id"])

        console.print("\n[bold green]✓[/bold green] User deleted successfully\n")

    except Exception as e:
        console.print(f"\n[red]Error deleting user:[/red] {e}\n")
        raise typer.Exit(1)


async def _find_user(identifier: str) -> dict[str, Any] | None:
    """Find user by email or ID.

    Args:
        identifier: User email or ID

    Returns:
        dict | None: User data if found, None otherwise
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        # Try to find by email first
        if "@" in identifier:
            user = await repo.get_user_by_email(identifier)
        else:
            # Try to find by ID
            user = await repo.get_user_by_id(identifier)

        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "isActive": user.isActive,
                "isAdmin": user.isAdmin,
                "createdAt": user.createdAt,
            }

    return None


async def _delete_user_from_db(user_id: str) -> None:
    """Delete user from database.

    Args:
        user_id: User ID to delete
    """
    from app.core.database import get_db
    from app.modules.auth.db_models import UserDB
    from sqlalchemy import select

    async for db in get_db():
        # Find user
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            raise ValueError(f"User with id {user_id} not found")

        # Delete user
        await db.delete(user_db)
        await db.commit()

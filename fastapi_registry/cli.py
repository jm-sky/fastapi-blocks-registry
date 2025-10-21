"""CLI for FastAPI Blocks Registry."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from fastapi_registry.core.registry_manager import RegistryManager
from fastapi_registry.core.installer import ModuleInstaller

# Initialize Typer app
app = typer.Typer(
    name="fastapi-registry",
    help="FastAPI Blocks Registry - Modular scaffolding system for FastAPI backends",
    add_completion=True,
)

# Initialize Rich console
console = Console()

# Get the path to the registry.json file
REGISTRY_PATH = Path(__file__).parent / "registry.json"


@app.command()
def list(
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search modules by name or description"
    )
) -> None:
    """List all available modules in the registry."""
    try:
        registry = RegistryManager(REGISTRY_PATH)

        if search:
            modules = registry.search_modules(search)
            if not modules:
                console.print(f"[yellow]No modules found matching '{search}'[/yellow]")
                return
            console.print(f"\n[bold]Modules matching '{search}':[/bold]\n")
        else:
            modules = registry.list_modules()
            console.print("\n[bold]Available modules:[/bold]\n")

        # Create a table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Module", style="green", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Description")
        table.add_column("Version", justify="center", style="yellow")

        for module_name, metadata in modules.items():
            table.add_row(
                module_name,
                metadata.name,
                metadata.description,
                metadata.version
            )

        console.print(table)
        console.print(
            f"\n[dim]Total: {len(modules)} module(s)[/dim]\n"
        )

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(module_name: str) -> None:
    """Show detailed information about a module."""
    try:
        registry = RegistryManager(REGISTRY_PATH)
        module = registry.get_module(module_name)

        if not module:
            console.print(f"[red]Module '{module_name}' not found in registry.[/red]")
            console.print("\n[dim]Run 'fastapi-registry list' to see available modules.[/dim]")
            raise typer.Exit(1)

        # Create info panel
        info_text = f"""[bold cyan]{module.name}[/bold cyan]
[dim]Version:[/dim] {module.version}

[bold]Description:[/bold]
{module.description}

[bold]Details:[/bold]
• Python Version: {module.python_version}
• Router Prefix: {module.router_prefix}
• Tags: {', '.join(module.tags)}

[bold]Dependencies:[/bold]"""

        if module.dependencies:
            for dep in module.dependencies:
                info_text += f"\n  • {dep}"
        else:
            info_text += "\n  [dim]No additional dependencies[/dim]"

        if module.env:
            info_text += "\n\n[bold]Environment Variables:[/bold]"
            for key, value in module.env.items():
                info_text += f"\n  • {key}={value}"

        if module.author:
            info_text += f"\n\n[dim]Author: {module.author}[/dim]"

        if module.repository:
            info_text += f"\n[dim]Repository: {module.repository}[/dim]"

        panel = Panel(
            info_text,
            title=f"[bold]Module: {module_name}[/bold]",
            border_style="cyan"
        )

        console.print("\n")
        console.print(panel)
        console.print("\n")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add(
    module_name: str,
    project_path: Optional[Path] = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Path to FastAPI project (defaults to current directory)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts"
    )
) -> None:
    """Add a module to your FastAPI project."""
    try:
        registry = RegistryManager(REGISTRY_PATH)
        module = registry.get_module(module_name)

        if not module:
            console.print(f"[red]Module '{module_name}' not found in registry.[/red]")
            console.print("\n[dim]Run 'fastapi-registry list' to see available modules.[/dim]")
            raise typer.Exit(1)

        # Determine project path
        if project_path is None:
            project_path = Path.cwd()

        # Show module info
        console.print(f"\n[bold cyan]Adding module:[/bold cyan] {module.name}")
        console.print(f"[dim]{module.description}[/dim]\n")

        # Ask for confirmation
        if not yes:
            confirm = typer.confirm(
                f"Add '{module_name}' to project at {project_path}?",
                default=True
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        # Install module
        installer = ModuleInstaller(registry, REGISTRY_PATH.parent)

        with console.status(f"[bold green]Installing module '{module_name}'...", spinner="dots"):
            installer.install_module(module_name, project_path)

        console.print(f"\n[bold green]✓[/bold green] Module '{module_name}' installed successfully!\n")

        # Show next steps
        console.print("[bold]Next steps:[/bold]")
        console.print(f"  1. Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")

        if module.env:
            console.print(f"  2. Configure environment variables in [cyan].env[/cyan]")
            console.print(f"     (check the newly added variables)")

        console.print(f"  3. Run database migrations if needed")
        console.print(f"  4. Start your FastAPI server: [cyan]uvicorn main:app --reload[/cyan]\n")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def remove(
    module_name: str,
    project_path: Optional[Path] = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Path to FastAPI project (defaults to current directory)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts"
    )
) -> None:
    """Remove a module from your FastAPI project."""
    try:
        # Determine project path
        if project_path is None:
            project_path = Path.cwd()

        module_path = project_path / "app" / "modules" / module_name

        if not module_path.exists():
            console.print(f"[red]Module '{module_name}' not found in project.[/red]")
            raise typer.Exit(1)

        # Ask for confirmation
        if not yes:
            console.print(f"[yellow]Warning:[/yellow] This will remove the module directory and its contents.")
            console.print(f"[dim]Path: {module_path}[/dim]\n")
            confirm = typer.confirm(
                f"Remove module '{module_name}'?",
                default=False
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        console.print(f"\n[yellow]Note:[/yellow] This command only removes the module files.")
        console.print("You'll need to manually:")
        console.print("  • Remove router registration from main.py")
        console.print("  • Remove dependencies from requirements.txt (if not used elsewhere)")
        console.print("  • Remove environment variables from .env\n")

        import shutil
        shutil.rmtree(module_path)

        console.print(f"[bold green]✓[/bold green] Module '{module_name}' removed successfully!\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    project_path: Optional[Path] = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Path to create FastAPI project (defaults to current directory)"
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Project name"
    )
) -> None:
    """Initialize a new FastAPI project structure."""
    console.print("[yellow]'init' command is not yet implemented.[/yellow]")
    console.print("[dim]This will create a basic FastAPI project structure in a future version.[/dim]")
    raise typer.Exit(0)


@app.command()
def version() -> None:
    """Show version information."""
    from fastapi_registry import __version__, __description__

    rprint(f"\n[bold cyan]FastAPI Blocks Registry[/bold cyan]")
    rprint(f"[dim]{__description__}[/dim]")
    rprint(f"\nVersion: [yellow]{__version__}[/yellow]\n")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

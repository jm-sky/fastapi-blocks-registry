"""CLI for FastAPI Blocks Registry."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from fastapi_registry.core.registry_manager import RegistryManager
from fastapi_registry.core.installer import ModuleInstaller
from fastapi_registry.core.project_initializer import ProjectInitializer
from fastapi_registry import __version__

# Initialize Typer app
app = typer.Typer(
    name="fastapi-registry",
    help="FastAPI Blocks Registry - Modular scaffolding system for FastAPI backends",
    add_completion=True,
)


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        from fastapi_registry import __description__
        rprint(f"\n[bold cyan]FastAPI Blocks Registry[/bold cyan] [yellow]v{__version__}[/yellow]")
        rprint(f"[dim]{__description__}[/dim]\n")
        raise typer.Exit()

# Initialize Rich console
console = Console()

# Get the path to the registry.json file
REGISTRY_PATH = Path(__file__).parent / "registry.json"
TEMPLATES_PATH = Path(__file__).parent / "templates"


@app.callback()
def common_options(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information",
        callback=version_callback,
        is_eager=True,
    )
) -> None:
    """FastAPI Blocks Registry - Modular scaffolding system for FastAPI backends."""
    pass


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
        console.print("  1. Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")

        if module.env:
            console.print("  2. Configure environment variables in [cyan].env[/cyan]")
            console.print("     (check the newly added variables)")

        console.print("  3. Run database migrations if needed")
        console.print("  4. Start your FastAPI server: [cyan]uvicorn main:app --reload[/cyan]\n")

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
            console.print("[yellow]Warning:[/yellow] This will remove the module directory and its contents.")
            console.print(f"[dim]Path: {module_path}[/dim]\n")
            confirm = typer.confirm(
                f"Remove module '{module_name}'?",
                default=False
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        console.print("\n[yellow]Note:[/yellow] This command only removes the module files.")
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
        help="Project name (defaults to directory name)"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Project description"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Initialize even if directory is not empty"
    )
) -> None:
    """Initialize a new FastAPI project structure."""
    try:
        # Determine project path
        if project_path is None:
            project_path = Path.cwd()

        project_path = project_path.resolve()

        # Validate project name if provided
        initializer = ProjectInitializer(TEMPLATES_PATH)
        if name and not initializer.validate_project_name(name):
            console.print(
                "[red]Error:[/red] Invalid project name. "
                "Must start with a letter and contain only alphanumeric characters, underscores, or hyphens."
            )
            raise typer.Exit(1)

        # Show what will be created
        console.print("\n[bold cyan]Initializing FastAPI project[/bold cyan]")
        console.print(f"[dim]Location:[/dim] {project_path}")
        if name:
            console.print(f"[dim]Name:[/dim] {name}")
        console.print()

        # Check if directory is not empty
        if project_path.exists() and any(project_path.iterdir()) and not force:
            console.print("[yellow]Warning:[/yellow] Directory is not empty.")
            if not typer.confirm("Initialize anyway?", default=False):
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)
            force = True

        # Initialize project
        with console.status("[bold green]Creating project structure...", spinner="dots"):
            initializer.init_project(
                project_path=project_path,
                project_name=name,
                project_description=description,
                force=force,
            )

        console.print("[bold green]✓[/bold green] Project initialized successfully!\n")

        # Show project structure
        console.print("[bold]Created files:[/bold]")
        files = [
            "main.py",
            "requirements.txt",
            ".env",
            ".gitignore",
            ".flake8",
            ".pylintrc",
            "mypy.ini",
            "pyproject.toml",
            "README.md",
            "app/",
            "  __init__.py",
            "  core/",
            "    __init__.py",
            "    config.py",
            "    database.py",
            "  modules/",
            "    __init__.py",
            "tests/",
            "  __init__.py",
            "  conftest.py",
            "  test_main.py",
        ]
        for file in files:
            console.print(f"  [dim]•[/dim] {file}")

        # Show next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review and update [cyan].env[/cyan] with your configuration")
        console.print("  2. Create a virtual environment:")
        console.print("     [cyan]python -m venv venv[/cyan]")
        console.print("     [cyan]source venv/bin/activate[/cyan]  [dim]# On Windows: venv\\Scripts\\activate[/dim]")
        console.print("  3. Install dependencies:")
        console.print("     [cyan]pip install -r requirements.txt[/cyan]")
        console.print("  4. Add modules to your project:")
        console.print("     [cyan]fastapi-registry list[/cyan]")
        console.print("     [cyan]fastapi-registry add <module-name>[/cyan]")
        console.print("  5. Start the development server:")
        console.print("     [cyan]uvicorn main:app --reload[/cyan]")
        console.print()

    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from fastapi_registry import __version__, __description__

    rprint("\n[bold cyan]FastAPI Blocks Registry[/bold cyan]")
    rprint(f"[dim]{__description__}[/dim]")
    rprint(f"\nVersion: [yellow]{__version__}[/yellow]\n")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

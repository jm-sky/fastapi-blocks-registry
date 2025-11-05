"""CLI for FastAPI Blocks Registry."""

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fastapi_registry import __version__
from fastapi_registry.core.installer import ModuleInstaller
from fastapi_registry.core.project_initializer import ProjectInitializer
from fastapi_registry.core.registry_manager import RegistryManager

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
REGISTRY_BASE_PATH = Path(__file__).parent


@app.callback()
def common_options(
    version: bool | None = typer.Option(
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
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search modules by name or description"
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
            table.add_row(module_name, metadata.name, metadata.description, metadata.version)

        console.print(table)
        console.print(f"\n[dim]Total: {len(modules)} module(s)[/dim]\n")

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

        panel = Panel(info_text, title=f"[bold]Module: {module_name}[/bold]", border_style="cyan")

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
    project_path: Path | None = typer.Option(
        None, "--project-path", "-p", help="Path to FastAPI project (defaults to current directory)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
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
                f"Add '{module_name}' to project at {project_path}?", default=True
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        # Install module
        installer = ModuleInstaller(registry, REGISTRY_PATH.parent)

        with console.status(f"[bold green]Installing module '{module_name}'...", spinner="dots"):
            installer.install_module(module_name, project_path)

        console.print(
            f"\n[bold green]✓[/bold green] Module '{module_name}' installed successfully!\n"
        )

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
    project_path: Path | None = typer.Option(
        None, "--project-path", "-p", help="Path to FastAPI project (defaults to current directory)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
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
            console.print(
                "[yellow]Warning:[/yellow] This will remove the module directory and its contents."
            )
            console.print(f"[dim]Path: {module_path}[/dim]\n")
            confirm = typer.confirm(f"Remove module '{module_name}'?", default=False)
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


def _install_all_modules(project_path: Path) -> None:
    """
    Install all available modules from registry to the project.

    Args:
        project_path: Path to the FastAPI project
    """
    console.print("\n[bold cyan]Installing all available modules...[/bold cyan]\n")

    registry = RegistryManager(REGISTRY_PATH)
    installer = ModuleInstaller(registry, REGISTRY_BASE_PATH)

    # Sort modules by dependencies
    sorted_modules = _sort_modules_by_dependencies(registry)
    total_modules = len(sorted_modules)

    console.print(f"[dim]Found {total_modules} module(s) to install[/dim]\n")

    installed_count = 0
    failed_modules: list[str] = []

    for i, module_name in enumerate(sorted_modules, 1):
        module = registry.get_module(module_name)
        if not module:
            console.print(f"[yellow]⚠[/yellow] Module '{module_name}' not found, skipping...")
            continue

        console.print(
            f"[bold cyan][{i}/{total_modules}][/bold cyan] Installing [green]{module_name}[/green]..."
        )
        console.print(f"[dim]{module.description}[/dim]")

        try:
            installer.install_module(module_name, project_path, create_backup=False)
            console.print(f"[bold green]✓[/bold green] {module_name} installed successfully\n")
            installed_count += 1
        except FileExistsError:
            console.print(
                f"[yellow]⚠[/yellow] Module '{module_name}' already exists, skipping...\n"
            )
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to install '{module_name}': {e}\n")
            failed_modules.append(module_name)

    # Summary
    console.print("\n[bold]Installation Summary:[/bold]")
    console.print(f"  [green]✓ Installed:[/green] {installed_count}/{total_modules}")
    if failed_modules:
        console.print(f"  [red]✗ Failed:[/red] {len(failed_modules)}")
        for failed_module in failed_modules:
            console.print(f"    • {failed_module}")

    console.print()


def _do_init_project(
    project_path: Path,
    name: str | None,
    description: str | None,
    force: bool,
    all_modules: bool,
) -> None:
    """
    Perform project initialization and optionally install all modules.

    Args:
        project_path: Path where to create the project
        name: Project name (defaults to directory name)
        description: Project description
        force: If True, overwrite existing files
        all_modules: If True, install all available modules after initialization
    """
    project_path = project_path.resolve()

    # Validate project name if provided
    initializer = ProjectInitializer(REGISTRY_BASE_PATH)
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
        "pyproject.toml",
        "README.md",
        "app/",
        "  __init__.py",
        "  core/",
        "    __init__.py",
        "    config.py",
        "    database.py",
        "    app_factory.py",
        "    middleware.py",
        "    limiter.py",
        "    static.py",
        "    logging_config.py",
        "  api/",
        "    __init__.py",
        "    router.py",
        "  exceptions/",
        "    __init__.py",
        "    custom_exceptions.py",
        "    exception_handler.py",
        "  modules/",
        "    __init__.py",
        "tests/",
        "  __init__.py",
        "  conftest.py",
        "  test_main.py",
    ]
    for file in files:
        console.print(f"  [dim]•[/dim] {file}")

    # Install all modules if --all flag is set
    if all_modules:
        _install_all_modules(project_path)

    # Show next steps
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review and update [cyan].env[/cyan] with your configuration")
    console.print("  2. Create a virtual environment:")
    console.print("     [cyan]python -m venv venv[/cyan]")
    console.print(
        "     [cyan]source venv/bin/activate[/cyan]  [dim]# On Windows: venv\\Scripts\\activate[/dim]"
    )
    console.print("  3. Install dependencies:")
    console.print("     [cyan]pip install -r requirements.txt[/cyan]")
    if not all_modules:
        console.print("  4. Add modules to your project:")
        console.print("     [cyan]fastapi-registry list[/cyan]")
        console.print("     [cyan]fastapi-registry add <module-name>[/cyan]")
        console.print("  5. Start the development server:")
    else:
        console.print("  4. Start the development server:")
    console.print("     [cyan]uvicorn main:app --reload[/cyan]")
    console.print()


def _sort_modules_by_dependencies(
    registry: RegistryManager,
) -> list[str]:
    """
    Sort modules by their dependencies (topological sort).

    Modules without dependencies come first, then modules that depend on them.

    Args:
        registry: Registry manager instance

    Returns:
        List of module names in dependency order
    """
    modules = registry.list_modules()
    # Build dependency graph: for each module, track which modules it depends on
    graph: dict[str, set[str]] = {}
    for module_name, metadata in modules.items():
        if metadata.module_dependencies:
            # Only include dependencies that exist in registry
            graph[module_name] = {
                dep for dep in metadata.module_dependencies if dep in modules
            }
        else:
            graph[module_name] = set()

    # Topological sort using Kahn's algorithm
    # Calculate in-degree: how many modules each module depends on
    in_degree: dict[str, int] = {name: 0 for name in modules.keys()}
    for module_name, deps in graph.items():
        in_degree[module_name] = len(deps)

    # Start with modules that have no dependencies
    queue: list[str] = [name for name, degree in in_degree.items() if degree == 0]
    result: list[str] = []

    while queue:
        module = queue.pop(0)
        result.append(module)

        # Find modules that depend on this module and reduce their in-degree
        for other_module, deps in graph.items():
            if module in deps:
                in_degree[other_module] -= 1
                if in_degree[other_module] == 0:
                    queue.append(other_module)

    # If we couldn't process all modules, there might be a circular dependency
    # or missing dependencies. Add remaining modules at the end.
    remaining = [name for name in modules.keys() if name not in result]
    if remaining:
        result.extend(remaining)

    return result


@app.command()
def init(
    project_path: Path | None = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Path to create FastAPI project (defaults to current directory)",
    ),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Project name (defaults to directory name)"
    ),
    description: str | None = typer.Option(None, "--description", "-d", help="Project description"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Initialize even if directory is not empty"
    ),
    all_modules: bool = typer.Option(
        False, "--all", "-a", help="Install all available modules after initialization"
    ),
) -> None:
    """Initialize a new FastAPI project structure."""
    try:
        # Determine project path
        if project_path is None:
            project_path = Path.cwd()

        _do_init_project(
            project_path=project_path,
            name=name,
            description=description,
            force=force,
            all_modules=all_modules,
        )

    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def setup(
    project_path: Path | None = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Path to create FastAPI project (defaults to current directory)",
    ),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Project name (defaults to directory name)"
    ),
    description: str | None = typer.Option(None, "--description", "-d", help="Project description"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Initialize even if directory is not empty"
    ),
    all_modules: bool = typer.Option(
        True, "--all", "-a", help="Install all available modules after initialization"
    ),
) -> None:
    """
    Initialize a new FastAPI project and install all available modules.

    This is equivalent to running 'init --all'. Use this command to quickly
    set up a complete FastAPI project with all modules from the registry.
    """
    try:
        # Determine project path
        if project_path is None:
            project_path = Path.cwd()

        _do_init_project(
            project_path=project_path,
            name=name,
            description=description,
            force=force,
            all_modules=all_modules,
        )

    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from fastapi_registry import __description__, __version__

    rprint("\n[bold cyan]FastAPI Blocks Registry[/bold cyan]")
    rprint(f"[dim]{__description__}[/dim]")
    rprint(f"\nVersion: [yellow]{__version__}[/yellow]\n")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

"""Project initialization utilities."""

import secrets
import shutil
from pathlib import Path


class ProjectInitializer:
    """Handles initialization of new FastAPI projects."""

    def __init__(self, base_path: Path):
        """
        Initialize project initializer.

        Args:
            base_path: Base path to fastapi_registry package directory
        """
        self.example_project_path = base_path / "example_project"
        self.templates_j2_path = base_path / "templates_j2"

    def init_project(
        self,
        project_path: Path,
        project_name: str | None = None,
        project_description: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Initialize a new FastAPI project.

        Args:
            project_path: Path where to create the project
            project_name: Name of the project (defaults to directory name)
            project_description: Project description
            force: If True, overwrite existing files

        Raises:
            FileExistsError: If project directory exists and force=False
            ValueError: If example_project not found
        """
        # Validate example_project exists
        if not self.example_project_path.exists():
            raise ValueError(
                f"Example project not found: {self.example_project_path}. "
                "Package may be corrupted."
            )

        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)

        # Check if directory is empty
        if any(project_path.iterdir()) and not force:
            raise FileExistsError(
                f"Directory {project_path} is not empty. " "Use --force to initialize anyway."
            )

        # Use directory name as project name if not provided
        if project_name is None:
            project_name = project_path.name

        if project_description is None:
            project_description = f"A FastAPI application: {project_name}"

        # Generate secure secret key
        secret_key = secrets.token_urlsafe(32)

        # Template variables
        template_vars = {
            "project_name": project_name,
            "project_description": project_description,
            "secret_key": secret_key,
        }

        # Copy example_project structure (excluding modules which user will add)
        self._copy_example_project(project_path, template_vars)

    def _copy_example_project(self, project_path: Path, template_vars: dict) -> None:
        """
        Copy example_project structure to destination.

        This copies all files from example_project/ except:
        - Files that should be processed as templates (.j2 equivalents exist)
        - Module directories (users add these with 'fastapi-registry add')

        Args:
            project_path: Destination path
            template_vars: Variables for template substitution
        """
        # Files that have .j2 template equivalents (will be processed separately)
        templated_files = {
            "README.md",  # -> templates_j2/README.md.j2
            ".env",  # -> templates_j2/env.j2
            "app/core/config.py",  # -> templates_j2/config.py.j2
        }

        # Directories to exclude (modules and common utils are added separately by users)
        exclude_dirs = {
            "app/modules",  # Modules are added with 'fastapi-registry add <module>'
            "app/common",   # Common utilities added as dependencies when needed
        }

        # Copy all files from example_project
        for item in self.example_project_path.rglob("*"):
            if not item.is_file():
                continue

            # Get relative path from example_project
            rel_path = item.relative_to(self.example_project_path)

            # Check if in excluded module directory
            is_excluded = False
            for exclude_dir in exclude_dirs:
                if str(rel_path).startswith(exclude_dir):
                    is_excluded = True
                    break

            if is_excluded:
                continue

            dest_path = project_path / rel_path

            # Skip if this file has a .j2 template version
            if str(rel_path) in templated_files:
                continue

            # Create parent directory
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Direct copy for non-template files
            shutil.copy2(item, dest_path)

        # Process .j2 templates
        self._process_j2_templates(project_path, template_vars)

        # Ensure empty modules directory exists
        (project_path / "app" / "modules").mkdir(parents=True, exist_ok=True)

        # Create __init__.py in modules if it doesn't exist
        modules_init = project_path / "app" / "modules" / "__init__.py"
        if not modules_init.exists():
            with open(modules_init, "w", encoding="utf-8") as f:
                f.write(
                    '"""FastAPI modules package.\n\n'
                    "This directory contains all application modules (features).\n"
                    "Each module is self-contained with its own:\n"
                    "- models.py (database models)\n"
                    "- schemas.py (Pydantic request/response schemas)\n"
                    "- router.py (API endpoints)\n"
                    "- service.py (business logic)\n"
                    "- dependencies.py (FastAPI dependencies)\n"
                    "- exceptions.py (module-specific exceptions)\n"
                    '"""\n'
                )

    def _process_j2_templates(self, project_path: Path, template_vars: dict) -> None:
        """
        Process .j2 template files and write to destination.

        Args:
            project_path: Destination path
            template_vars: Variables for substitution
        """
        # Map of template files to destination paths
        j2_templates = {
            "README.md.j2": project_path / "README.md",
            "env.j2": project_path / ".env",
            "config.py.j2": project_path / "app" / "core" / "config.py",
        }

        for template_name, dest_path in j2_templates.items():
            template_path = self.templates_j2_path / template_name

            if not template_path.exists():
                # Skip if template doesn't exist (optional templates)
                continue

            # Read template content
            with open(template_path, encoding="utf-8") as f:
                content = f.read()

            # Replace variables in content
            for key, value in template_vars.items():
                content = content.replace(f"{{{key}}}", value)

            # Write to destination
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)

    def validate_project_name(self, name: str) -> bool:
        """
        Validate project name is a valid Python package name.

        Args:
            name: Project name to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        # Allow alphanumeric, underscore, hyphen
        return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", name))

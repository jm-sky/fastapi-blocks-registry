"""Project initialization utilities."""

import secrets
from pathlib import Path
from typing import Optional


class ProjectInitializer:
    """Handles initialization of new FastAPI projects."""

    def __init__(self, templates_path: Path):
        """
        Initialize project initializer.

        Args:
            templates_path: Path to the templates directory
        """
        self.templates_path = templates_path / "fastapi_project"

    def init_project(
        self,
        project_path: Path,
        project_name: Optional[str] = None,
        project_description: Optional[str] = None,
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
            ValueError: If templates not found
        """
        # Validate templates exist
        if not self.templates_path.exists():
            raise ValueError(
                f"Templates directory not found: {self.templates_path}. "
                "Package may be corrupted."
            )

        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)

        # Check if directory is empty
        if any(project_path.iterdir()) and not force:
            raise FileExistsError(
                f"Directory {project_path} is not empty. "
                "Use --force to initialize anyway."
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

        # Create project structure
        self._create_structure(project_path)

        # Copy and process template files
        self._copy_templates(project_path, template_vars)

    def _create_structure(self, project_path: Path) -> None:
        """
        Create basic project directory structure.

        Args:
            project_path: Root project path
        """
        directories = [
            project_path / "app",
            project_path / "app" / "core",
            project_path / "app" / "modules",
            project_path / "app" / "api",
            project_path / "app" / "exceptions",
            project_path / "tests",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _copy_templates(self, project_path: Path, template_vars: dict) -> None:
        """
        Copy template files to project directory and process variables.

        Args:
            project_path: Root project path
            template_vars: Dictionary of template variables for substitution
        """
        # Get the base templates path (parent of fastapi_project)
        core_templates_path = self.templates_path.parent / "core"
        
        # Map of template files to destination paths
        templates = {
            "main.py.template": project_path / "main.py",
            "requirements.txt.template": project_path / "requirements.txt",
            "env.template": project_path / ".env",
            ".gitignore.template": project_path / ".gitignore",
            ".flake8.template": project_path / ".flake8",
            ".pylintrc.template": project_path / ".pylintrc",
            "mypy.ini.template": project_path / "mypy.ini",
            "pyproject.toml.template": project_path / "pyproject.toml",
            "README.md.template": project_path / "README.md",
            # App structure
            "app/__init__.py.template": project_path / "app" / "__init__.py",
            "app/README.md.template": project_path / "app" / "README.md",
            # API
            "app/api/__init__.py.template": project_path / "app" / "api" / "__init__.py",
            "app/api/router.py.template": project_path / "app" / "api" / "router.py",
            # Exceptions
            "app/exceptions/__init__.py.template": project_path / "app" / "exceptions" / "__init__.py",
            "app/exceptions/custom_exceptions.py.template": project_path / "app" / "exceptions" / "custom_exceptions.py",
            "app/exceptions/exception_handler.py.template": project_path / "app" / "exceptions" / "exception_handler.py",
            # Modules
            "app/modules/__init__.py.template": project_path / "app" / "modules" / "__init__.py",
            # Tests
            "tests/__init__.py.template": project_path / "tests" / "__init__.py",
            "tests/conftest.py.template": project_path / "tests" / "conftest.py",
            "tests/test_main.py.template": project_path / "tests" / "test_main.py",
        }
        
        # Core templates from shared templates/core/ directory
        core_templates = {
            "__init__.py.template": project_path / "app" / "core" / "__init__.py",
            "config.py.template": project_path / "app" / "core" / "config.py",
            "database.py.template": project_path / "app" / "core" / "database.py",
            "app_factory.py.template": project_path / "app" / "core" / "app_factory.py",
            "middleware.py.template": project_path / "app" / "core" / "middleware.py",
            "limiter.py.template": project_path / "app" / "core" / "limiter.py",
            "static.py.template": project_path / "app" / "core" / "static.py",
            "logging_config.py.template": project_path / "app" / "core" / "logging_config.py",
        }

        # Copy templates from fastapi_project directory
        for template_name, dest_path in templates.items():
            template_path = self.templates_path / template_name

            if not template_path.exists():
                # Skip if template doesn't exist (optional templates)
                continue

            # Read template content
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace variables in content
            for key, value in template_vars.items():
                content = content.replace(f"{{{key}}}", value)

            # Write to destination
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        # Copy core templates from shared templates/core/ directory
        for template_name, dest_path in core_templates.items():
            template_path = core_templates_path / template_name

            if not template_path.exists():
                # Skip if template doesn't exist (optional templates)
                continue

            # Read template content
            with open(template_path, "r", encoding="utf-8") as f:
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

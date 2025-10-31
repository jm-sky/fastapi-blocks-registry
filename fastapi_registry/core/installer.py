"""Module installer for adding modules to FastAPI projects."""

from pathlib import Path
from typing import Optional

from fastapi_registry.core.registry_manager import RegistryManager
from fastapi_registry.core import file_utils


class ModuleInstaller:
    """Handles installation of modules into FastAPI projects."""

    def __init__(self, registry: RegistryManager, registry_base_path: Path):
        """
        Initialize module installer.

        Args:
            registry: Registry manager instance
            registry_base_path: Base path where registry and modules are located
        """
        self.registry = registry
        self.registry_base_path = registry_base_path

    def install_module(
        self,
        module_name: str,
        project_path: Path,
        create_backup: bool = True
    ) -> None:
        """
        Install a module to a FastAPI project.

        Args:
            module_name: Name of the module to install
            project_path: Path to the FastAPI project
            create_backup: If True, create backups of modified files

        Raises:
            ValueError: If module not found or project structure invalid
            FileExistsError: If module already exists in project
        """
        # Get module metadata
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not found in registry")

        # Validate project structure
        self._validate_project_structure(project_path)

        # Get source and destination paths
        src_path = self.registry_base_path / module.path
        dst_path = project_path / "app" / "modules" / module_name

        # Check if module already exists
        if dst_path.exists():
            raise FileExistsError(
                f"Module '{module_name}' already exists at {dst_path}. "
                "Remove it first if you want to reinstall."
            )

        # Verify source module exists
        if not src_path.exists():
            raise ValueError(
                f"Module source not found at {src_path}. "
                "Registry may be corrupted."
            )

        # Copy module files
        file_utils.copy_directory(src_path, dst_path)

        # Copy common dependencies if needed
        if module.common_dependencies:
            self._install_common_dependencies(module.common_dependencies, project_path)

        # Update requirements.txt
        requirements_path = project_path / "requirements.txt"
        if module.dependencies:
            file_utils.update_requirements(
                requirements_path,
                module.dependencies,
                create_if_missing=True
            )

        # Update .env file
        env_path = project_path / ".env"
        if module.env:
            file_utils.update_env_file(
                env_path,
                module.env,
                create_if_missing=True
            )

        # Update app/api/router.py to register the module router
        router_py_path = project_path / "app" / "api" / "router.py"
        if router_py_path.exists():
            if create_backup:
                file_utils.create_backup(router_py_path)

            file_utils.add_router_to_api_router(
                router_py_path,
                module_name,
                module.router_prefix,
                module.tags
            )
        else:
            # If router.py not found, try legacy main.py approach
            main_py_path = file_utils.find_main_py(project_path)
            if main_py_path:
                if create_backup:
                    file_utils.create_backup(main_py_path)

                file_utils.add_router_to_main(
                    main_py_path,
                    module_name,
                    module.router_prefix,
                    module.tags
                )

    def _install_common_dependencies(
        self, common_deps: list[str], project_path: Path
    ) -> None:
        """
        Install common utility dependencies.

        Args:
            common_deps: List of common dependency names (e.g., ['pagination', 'search'])
            project_path: Path to the project
        """
        for common_dep in common_deps:
            # Source path in registry
            src_path = self.registry_base_path / "example_project" / "app" / "common" / f"{common_dep}.py"

            # Destination path in project
            common_dir = project_path / "app" / "common"
            dst_path = common_dir / f"{common_dep}.py"

            # Skip if already exists
            if dst_path.exists():
                continue

            # Ensure common directory exists
            file_utils.ensure_directory_exists(common_dir)

            # Create __init__.py in common if it doesn't exist
            common_init = common_dir / "__init__.py"
            if not common_init.exists():
                # Copy the __init__.py from example_project
                src_init = self.registry_base_path / "example_project" / "app" / "common" / "__init__.py"
                if src_init.exists():
                    file_utils.copy_file(src_init, common_init)
                else:
                    file_utils.write_file(common_init, '"""Common utilities."""\n')

            # Verify source file exists
            if not src_path.exists():
                raise ValueError(
                    f"Common dependency '{common_dep}' not found at {src_path}. "
                    "Registry may be corrupted."
                )

            # Copy the file
            file_utils.copy_file(src_path, dst_path)

    def _validate_project_structure(self, project_path: Path) -> None:
        """
        Validate that the project has a proper FastAPI structure.

        Args:
            project_path: Path to the project

        Raises:
            ValueError: If project structure is invalid
        """
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Create app/modules directory if it doesn't exist
        modules_path = project_path / "app" / "modules"
        file_utils.ensure_directory_exists(modules_path)

        # Create __init__.py in app if it doesn't exist
        app_init = project_path / "app" / "__init__.py"
        if not app_init.exists():
            file_utils.write_file(app_init, '"""FastAPI application package."""\n')

        # Create __init__.py in modules if it doesn't exist
        modules_init = modules_path / "__init__.py"
        if not modules_init.exists():
            file_utils.write_file(modules_init, '"""FastAPI modules package."""\n')

    def uninstall_module(
        self,
        module_name: str,
        project_path: Path,
        remove_dependencies: bool = False
    ) -> None:
        """
        Uninstall a module from a FastAPI project.

        Note: This only removes the module directory. Router registration,
        dependencies, and environment variables must be removed manually.

        Args:
            module_name: Name of the module to uninstall
            project_path: Path to the FastAPI project
            remove_dependencies: If True, attempt to remove dependencies
                                (not implemented yet - requires dependency analysis)

        Raises:
            ValueError: If module not found in project
        """
        module_path = project_path / "app" / "modules" / module_name

        if not module_path.exists():
            raise ValueError(f"Module '{module_name}' not found in project")

        import shutil
        shutil.rmtree(module_path)

        # Note: We don't automatically remove dependencies or router registration
        # because they might be used by other modules or custom code

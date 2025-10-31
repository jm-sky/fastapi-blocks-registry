"""Registry manager for handling module metadata."""

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModuleMetadata(BaseModel):
    """Metadata for a FastAPI module."""

    name: str = Field(description="Human-readable module name")
    description: str = Field(description="Module description")
    version: str = Field(default="1.0.0", description="Module version")
    path: str = Field(description="Relative path to module directory")
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of Python package dependencies"
    )
    module_dependencies: list[str] = Field(
        default_factory=list,
        description="List of other modules this module depends on"
    )
    common_dependencies: list[str] = Field(
        default_factory=list,
        description="List of common utility modules (e.g., ['pagination', 'search'])"
    )
    python_version: str = Field(
        default=">=3.12",
        description="Required Python version"
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables with default values"
    )
    settings_class: Optional[str] = Field(
        default=None,
        description="Name of the settings class in the module"
    )
    router_prefix: str = Field(
        default="/api/v1",
        description="URL prefix for the router"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="OpenAPI tags for the router"
    )
    author: Optional[str] = Field(default=None, description="Module author")
    repository: Optional[str] = Field(default=None, description="Module repository URL")


class RegistryManager:
    """Manages the module registry."""

    def __init__(self, registry_path: Path):
        """
        Initialize registry manager.

        Args:
            registry_path: Path to registry.json file
        """
        self.registry_path = registry_path
        self._registry: dict[str, ModuleMetadata] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from JSON file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {self.registry_path}")

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse each module metadata
        for module_name, module_data in data.items():
            self._registry[module_name] = ModuleMetadata(**module_data)

    def get_module(self, module_name: str) -> Optional[ModuleMetadata]:
        """
        Get module metadata by name.

        Args:
            module_name: Name of the module

        Returns:
            ModuleMetadata or None if not found
        """
        return self._registry.get(module_name)

    def list_modules(self) -> dict[str, ModuleMetadata]:
        """
        List all available modules.

        Returns:
            Dictionary of module names to metadata
        """
        return self._registry.copy()

    def module_exists(self, module_name: str) -> bool:
        """
        Check if a module exists in the registry.

        Args:
            module_name: Name of the module

        Returns:
            True if module exists, False otherwise
        """
        return module_name in self._registry

    def get_module_path(self, module_name: str, base_path: Optional[Path] = None) -> Path:
        """
        Get absolute path to module directory.

        Args:
            module_name: Name of the module
            base_path: Base path for resolving relative paths (defaults to registry directory)

        Returns:
            Absolute path to module directory

        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not found in registry")

        if base_path is None:
            base_path = self.registry_path.parent

        return base_path / module.path

    def search_modules(self, query: str) -> dict[str, ModuleMetadata]:
        """
        Search modules by name or description.

        Args:
            query: Search query (case-insensitive)

        Returns:
            Dictionary of matching modules
        """
        query_lower = query.lower()
        results = {}

        for module_name, metadata in self._registry.items():
            if (
                query_lower in module_name.lower()
                or query_lower in metadata.name.lower()
                or query_lower in metadata.description.lower()
            ):
                results[module_name] = metadata

        return results

    def add_module(
        self,
        module_name: str,
        metadata: ModuleMetadata,
        save: bool = True
    ) -> None:
        """
        Add a new module to the registry.

        Args:
            module_name: Name of the module
            metadata: Module metadata
            save: If True, save registry to file

        Raises:
            ValueError: If module already exists
        """
        if self.module_exists(module_name):
            raise ValueError(f"Module '{module_name}' already exists in registry")

        self._registry[module_name] = metadata

        if save:
            self._save_registry()

    def update_module(
        self,
        module_name: str,
        metadata: ModuleMetadata,
        save: bool = True
    ) -> None:
        """
        Update existing module metadata.

        Args:
            module_name: Name of the module
            metadata: Updated module metadata
            save: If True, save registry to file

        Raises:
            ValueError: If module doesn't exist
        """
        if not self.module_exists(module_name):
            raise ValueError(f"Module '{module_name}' not found in registry")

        self._registry[module_name] = metadata

        if save:
            self._save_registry()

    def remove_module(self, module_name: str, save: bool = True) -> None:
        """
        Remove a module from the registry.

        Args:
            module_name: Name of the module
            save: If True, save registry to file

        Raises:
            ValueError: If module doesn't exist
        """
        if not self.module_exists(module_name):
            raise ValueError(f"Module '{module_name}' not found in registry")

        del self._registry[module_name]

        if save:
            self._save_registry()

    def _save_registry(self) -> None:
        """Save registry to JSON file."""
        data = {
            module_name: metadata.model_dump(exclude_none=True)
            for module_name, metadata in self._registry.items()
        }

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_total_dependencies(self, module_name: str) -> list[str]:
        """
        Get all dependencies for a module (including transitive dependencies).

        Note: This is a simple implementation that only gets direct dependencies.
        For transitive dependencies, you would need to resolve them from the
        actual package metadata.

        Args:
            module_name: Name of the module

        Returns:
            List of dependency strings

        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not found in registry")

        return module.dependencies.copy()

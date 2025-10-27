"""Core utilities for fastapi-registry."""

from fastapi_registry.core.file_utils import (
    copy_directory,
    ensure_directory_exists,
    read_file,
    write_file,
    append_to_file,
    update_requirements,
    update_env_file,
    find_main_py,
    add_router_to_main,
    create_backup,
)
from fastapi_registry.core.installer import ModuleInstaller
from fastapi_registry.core.project_initializer import ProjectInitializer
from fastapi_registry.core.registry_manager import RegistryManager

__all__ = [
    "copy_directory",
    "ensure_directory_exists",
    "read_file",
    "write_file",
    "append_to_file",
    "update_requirements",
    "update_env_file",
    "find_main_py",
    "add_router_to_main",
    "create_backup",
    "ModuleInstaller",
    "ProjectInitializer",
    "RegistryManager",
]


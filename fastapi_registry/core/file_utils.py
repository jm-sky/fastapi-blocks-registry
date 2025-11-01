"""File manipulation utilities for module installation."""

import re
import shutil
from pathlib import Path
from typing import List, Optional


def copy_directory(src: Path, dst: Path, exist_ok: bool = True) -> None:
    """
    Copy directory from src to dst.

    Args:
        src: Source directory path
        dst: Destination directory path
        exist_ok: If True, don't raise error if destination exists
    """
    if dst.exists() and not exist_ok:
        raise FileExistsError(f"Destination directory already exists: {dst}")

    shutil.copytree(src, dst, dirs_exist_ok=exist_ok)


def copy_file(src: Path, dst: Path) -> None:
    """
    Copy a single file from src to dst.

    Args:
        src: Source file path
        dst: Destination file path
    """
    ensure_directory_exists(dst.parent)
    shutil.copy2(src, dst)


def ensure_directory_exists(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def read_file(file_path: Path) -> str:
    """Read file content as string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(file_path: Path, content: str) -> None:
    """Write content to file."""
    ensure_directory_exists(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def append_to_file(file_path: Path, content: str) -> None:
    """Append content to file."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)


def update_requirements(
    requirements_path: Path,
    new_dependencies: List[str],
    create_if_missing: bool = True
) -> None:
    """
    Add new dependencies to requirements.txt without duplicates.

    Args:
        requirements_path: Path to requirements.txt
        new_dependencies: List of dependency strings to add
        create_if_missing: Create file if it doesn't exist
    """
    if not requirements_path.exists():
        if create_if_missing:
            write_file(requirements_path, "")
        else:
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

    # Read existing dependencies
    existing_content = read_file(requirements_path)
    existing_deps = {
        line.split("==")[0].split(">=")[0].split("<=")[0].strip()
        for line in existing_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    # Filter out dependencies that already exist
    deps_to_add = [
        dep for dep in new_dependencies
        if dep.split("==")[0].split(">=")[0].split("<=")[0].strip() not in existing_deps
    ]

    if deps_to_add:
        # Add newline if file doesn't end with one
        if existing_content and not existing_content.endswith("\n"):
            append_to_file(requirements_path, "\n")

        # Add new dependencies
        append_to_file(requirements_path, "\n".join(deps_to_add) + "\n")


def update_env_file(
    env_path: Path,
    new_vars: dict[str, str],
    create_if_missing: bool = True
) -> None:
    """
    Add new environment variables to .env file without overwriting existing ones.

    Args:
        env_path: Path to .env file
        new_vars: Dictionary of environment variables to add
        create_if_missing: Create file if it doesn't exist
    """
    if not env_path.exists():
        if create_if_missing:
            write_file(env_path, "")
        else:
            raise FileNotFoundError(f"Environment file not found: {env_path}")

    # Read existing variables
    existing_content = read_file(env_path)
    existing_vars = {
        line.split("=")[0].strip()
        for line in existing_content.splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }

    # Filter out variables that already exist
    vars_to_add = {
        key: value for key, value in new_vars.items()
        if key not in existing_vars
    }

    if vars_to_add:
        # Add newline if file doesn't end with one
        if existing_content and not existing_content.endswith("\n"):
            append_to_file(env_path, "\n")

        # Add comment header
        append_to_file(env_path, "\n# Variables added by fastapi-registry\n")

        # Add new variables
        for key, value in vars_to_add.items():
            append_to_file(env_path, f"{key}={value}\n")


def find_main_py(project_path: Path) -> Optional[Path]:
    """
    Find main.py in the project.

    Searches in common locations:
    - project_path/main.py
    - project_path/app/main.py
    - project_path/src/main.py

    Returns:
        Path to main.py or None if not found
    """
    possible_locations = [
        project_path / "main.py",
        project_path / "app" / "main.py",
        project_path / "src" / "main.py",
    ]

    for location in possible_locations:
        if location.exists():
            return location

    return None


def add_router_to_main(
    main_py_path: Path,
    module_name: str,
    router_prefix: str,
    tags: List[str]
) -> None:
    """
    Add router import and registration to main.py.

    Uses marker comments to identify where to add imports and router registrations.
    If markers don't exist, appends to the end of the file.

    Args:
        main_py_path: Path to main.py
        module_name: Name of the module
        router_prefix: URL prefix for the router
        tags: Tags for the router
    """
    content = read_file(main_py_path)

    # Prepare import and router registration
    import_line = f"from app.modules.{module_name}.router import router as {module_name}_router"
    router_line = f'app.include_router({module_name}_router, prefix="{router_prefix}", tags={tags})'

    # Check if already added
    if import_line in content:
        return  # Already added

    # Try to find import section marker
    import_marker = "# fastapi-registry imports"
    router_marker = "# fastapi-registry routers"

    if import_marker in content:
        # Add import after marker
        content = content.replace(
            import_marker,
            f"{import_marker}\n{import_line}"
        )
    else:
        # Add marker and import at the beginning (after existing imports)
        import_section_end = find_last_import_line(content)
        if import_section_end is not None:
            lines = content.splitlines(keepends=True)
            lines.insert(import_section_end + 1, f"\n{import_marker}\n{import_line}\n")
            content = "".join(lines)
        else:
            # No imports found, add at the beginning
            content = f"{import_marker}\n{import_line}\n\n{content}"

    if router_marker in content:
        # Add router after marker
        content = content.replace(
            router_marker,
            f"{router_marker}\n{router_line}"
        )
    else:
        # Try to find app = FastAPI() or similar
        app_pattern = re.compile(r"app\s*=\s*(?:FastAPI|create_app)\(")
        match = app_pattern.search(content)

        if match:
            # Find the end of the app creation (next line after the statement)
            start_pos = match.start()
            lines_before = content[:start_pos].count("\n")
            lines = content.splitlines(keepends=True)

            # Find the line where app is created
            for i in range(lines_before, len(lines)):
                if ")" in lines[i]:
                    # Insert router registration after this line
                    lines.insert(i + 1, f"\n{router_marker}\n{router_line}\n")
                    content = "".join(lines)
                    break
        else:
            # Fallback: append at the end
            content += f"\n{router_marker}\n{router_line}\n"

    write_file(main_py_path, content)


def find_last_import_line(content: str) -> Optional[int]:
    """
    Find the line number of the last import statement in the file.

    Returns:
        Line number (0-indexed) or None if no imports found
    """
    lines = content.splitlines()
    last_import_line = None

    import_pattern = re.compile(r"^\s*(?:from|import)\s+")

    for i, line in enumerate(lines):
        if import_pattern.match(line):
            last_import_line = i

    return last_import_line


def add_router_to_api_router(
    router_py_path: Path,
    module_name: str,
    router_prefix: str,
    tags: List[str]
) -> None:
    """
    Add router import and registration to app/api/router.py.

    This is the preferred method for adding routes (vs add_router_to_main).
    Routes should be registered in app/api/router.py, not in main.py.

    Args:
        router_py_path: Path to app/api/router.py
        module_name: Name of the module
        router_prefix: URL prefix for the router (e.g., "/auth")
        tags: Tags for the router
    """
    content = read_file(router_py_path)

    # Prepare import and router registration strings
    import_line = f"from app.modules.{module_name}.router import router as {module_name}_router"
    router_line = f'api_router.include_router({module_name}_router, prefix="{router_prefix}", tags={tags})'

    lines = content.splitlines(keepends=True)

    # Check if import already exists (as an actual import, not in comments)
    import_exists = False
    for line in lines:
        stripped = line.strip()
        if stripped == import_line or stripped == import_line + '\n':
            import_exists = True
            break

    # Check if router registration already exists (as an actual call, not in comments)
    router_exists = False
    for line in lines:
        stripped = line.strip()
        if router_line in stripped and not stripped.startswith('#'):
            router_exists = True
            break

    # If both import and registration exist, nothing to do
    if import_exists and router_exists:
        return  # Already added

    # Step 1: Add import if not present
    if not import_exists:
        # Find last import line in the file
        last_import_idx = None
        for i, line in enumerate(lines):
            if re.match(r"^\s*(?:from|import)\s+", line):
                last_import_idx = i

        # Insert import after the last import
        if last_import_idx is not None:
            lines.insert(last_import_idx + 1, f"{import_line}\n")
        else:
            # No imports found, add after module docstring (line 2)
            lines.insert(2, f"\n{import_line}\n")

    # Step 2: Add router registration if not present
    if not router_exists:
        # Remove trailing empty lines for cleaner output
        while lines and lines[-1].strip() == "":
            lines.pop()

        # Add router registration at the end
        lines.append(f"\n{router_line}\n")

    # Write back to file
    new_content = "".join(lines)
    write_file(router_py_path, new_content)


def create_backup(file_path: Path) -> Path:
    """
    Create a backup of a file.

    Returns:
        Path to backup file
    """
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    return backup_path

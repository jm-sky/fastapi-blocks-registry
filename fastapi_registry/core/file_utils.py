"""File manipulation utilities for module installation."""

import re
import shutil
from pathlib import Path


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
    with open(file_path, encoding="utf-8") as f:
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


def update_requirements(requirements_path: Path, new_dependencies: list[str], create_if_missing: bool = True) -> None:
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
    existing_deps = {line.split("==")[0].split(">=")[0].split("<=")[0].strip() for line in existing_content.splitlines() if line.strip() and not line.strip().startswith("#")}

    # Filter out dependencies that already exist
    deps_to_add = [dep for dep in new_dependencies if dep.split("==")[0].split(">=")[0].split("<=")[0].strip() not in existing_deps]

    if deps_to_add:
        # Add newline if file doesn't end with one
        if existing_content and not existing_content.endswith("\n"):
            append_to_file(requirements_path, "\n")

        # Add new dependencies
        append_to_file(requirements_path, "\n".join(deps_to_add) + "\n")


def update_env_file(env_path: Path, new_vars: dict[str, str], create_if_missing: bool = True) -> None:
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
    existing_vars = {line.split("=")[0].strip() for line in existing_content.splitlines() if line.strip() and not line.strip().startswith("#") and "=" in line}

    # Filter out variables that already exist
    vars_to_add = {key: value for key, value in new_vars.items() if key not in existing_vars}

    if vars_to_add:
        # Add newline if file doesn't end with one
        if existing_content and not existing_content.endswith("\n"):
            append_to_file(env_path, "\n")

        # Add comment header
        append_to_file(env_path, "\n# Variables added by fastapi-registry\n")

        # Add new variables
        for key, value in vars_to_add.items():
            append_to_file(env_path, f"{key}={value}\n")


def find_main_py(project_path: Path) -> Path | None:
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


def add_router_to_main(main_py_path: Path, module_name: str, router_prefix: str, tags: list[str]) -> None:
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
        content = content.replace(import_marker, f"{import_marker}\n{import_line}")
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
        content = content.replace(router_marker, f"{router_marker}\n{router_line}")
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


def find_last_import_line(content: str) -> int | None:
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


def add_router_to_api_router(router_py_path: Path, module_name: str, router_prefix: str, tags: list[str]) -> None:
    """
    Add router import and registration to app/api/router.py.

    This is the preferred method for adding routes (vs add_router_to_main).
    Routes should be registered in app/api/router.py, not in main.py.

    Optional modules (like 'two_factor') are added in try-except blocks with ImportError.

    Args:
        router_py_path: Path to app/api/router.py
        module_name: Name of the module
        router_prefix: URL prefix for the router (e.g., "/auth")
        tags: Tags for the router
    """
    content = read_file(router_py_path)

    # List of optional modules that should be in try-except blocks
    optional_modules = {"two_factor"}

    # Prepare import and router registration strings
    import_line = f"from app.modules.{module_name}.router import router as {module_name}_router"
    router_line = f'api_router.include_router({module_name}_router, prefix="{router_prefix}", tags={tags})'

    lines = content.splitlines(keepends=True)

    # Check if import already exists (as an actual import, not in comments)
    import_exists = False
    for line in lines:
        stripped = line.strip()
        if stripped == import_line or stripped == import_line + "\n":
            import_exists = True
            break

    # Check if router registration already exists (as an actual call, not in comments)
    router_exists = False
    for line in lines:
        stripped = line.strip()
        if router_line in stripped and not stripped.startswith("#"):
            router_exists = True
            break

    # If both import and registration exist, nothing to do
    if import_exists and router_exists:
        return  # Already added

    is_optional = module_name in optional_modules

    # Step 1: Add import if not present
    if not import_exists:
        if is_optional:
            # For optional modules, import is added inside try-except block
            # We'll handle this in Step 2
            pass
        else:
            # Find last TOP-LEVEL import line (not inside try-except blocks)
            # We track indentation level to avoid imports inside try-except
            last_toplevel_import_idx = None
            inside_block = False
            indent_stack = []

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Track try/except/if blocks by indentation
                if stripped.startswith(("try:", "except", "if ", "else:", "elif ", "for ", "while ", "with ")):
                    inside_block = True
                    indent_stack.append(len(line) - len(line.lstrip()))
                elif inside_block and indent_stack:
                    # Check if we've exited the block (dedented)
                    current_indent = len(line) - len(line.lstrip())
                    if stripped and current_indent <= indent_stack[-1]:
                        inside_block = False
                        indent_stack = []

                # Only match top-level imports (no indentation or minimal indentation)
                if re.match(r"^(?:from|import)\s+", line) and not inside_block:
                    last_toplevel_import_idx = i

            # Insert import after the last top-level import
            if last_toplevel_import_idx is not None:
                lines.insert(last_toplevel_import_idx + 1, f"{import_line}\n")
            else:
                # No imports found, add after module docstring (line 2)
                # Find first non-comment, non-docstring line
                insert_idx = 0
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('"""') and not stripped.startswith("'''") and not stripped.startswith("#"):
                        insert_idx = i
                        break
                lines.insert(insert_idx, f"\n{import_line}\n")

    # Step 2: Add router registration if not present
    if not router_exists:
        # Remove trailing empty lines for cleaner output
        while lines and lines[-1].strip() == "":
            lines.pop()

        if is_optional:
            # Check if there's already a try-except block for this module
            # Look for try block that contains import for this module
            existing_try_block_idx = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("try:"):
                    # Check next few lines to see if this try block imports our module
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if import_line in lines[j]:
                            existing_try_block_idx = i
                            break
                    if existing_try_block_idx is not None:
                        break

            if existing_try_block_idx is not None:
                # Try-except exists, add router registration inside it
                # Find the line with except ImportError
                for i in range(existing_try_block_idx + 1, len(lines)):
                    stripped = lines[i].strip()
                    if stripped.startswith("except ImportError:"):
                        # Insert router before except block
                        indent = "    "  # 4 spaces for try block
                        lines.insert(i, f"{indent}{router_line}\n")
                        break
            else:
                # No try-except exists, create one
                # Add import and router in try-except block
                try_block = f"\n# Register {module_name.replace('_', ' ').title()} module (optional, added during development)\n"
                try_block += "try:\n"
                try_block += f"    {import_line}\n"
                try_block += f"    {router_line}\n"
                try_block += "except ImportError:\n"
                try_block += "    # Module may be absent in some builds; ignore if not present\n"
                try_block += "    pass\n"
                lines.append(try_block)
        else:
            # Regular module - add router registration at the end
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


def add_email_settings_to_config(config_py_path: Path, create_if_missing: bool = False) -> None:
    """
    Add EmailSettings class and email field to Settings class in config.py.

    This is called when installing modules that require email functionality (e.g., auth, two_factor).

    Args:
        config_py_path: Path to app/core/config.py
        create_if_missing: If False, raise error if config.py doesn't exist
    """
    if not config_py_path.exists():
        if create_if_missing:
            # Create basic config.py structure (shouldn't happen in practice)
            return
        raise FileNotFoundError(f"Config file not found: {config_py_path}")

    content = read_file(config_py_path)

    # Check if EmailSettings already exists
    if "class EmailSettings" in content:
        return  # Already added

    # Check if Literal is imported (needed for EmailSettings.adapter)
    # Check if there's a typing import that includes Literal
    has_literal_import = False
    if "from typing import" in content:
        # Check if Literal is in any typing import line
        for line in content.splitlines():
            if "from typing import" in line and "Literal" in line:
                has_literal_import = True
                break
    needs_literal_import = not has_literal_import

    # Find where to insert EmailSettings (after RecaptchaSettings, before Settings class)
    recaptcha_settings_end = None
    settings_class_start = None

    lines = content.splitlines(keepends=True)

    # Add Literal import if needed
    if needs_literal_import:
        # Find typing import line
        typing_import_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("from typing import"):
                typing_import_idx = i
                # Check if Literal is already in the import
                if "Literal" in line:
                    needs_literal_import = False
                break

        if needs_literal_import and typing_import_idx is not None:
            # Add Literal to existing typing import
            line = lines[typing_import_idx]
            if "Literal" not in line:
                # Add Literal to the import
                if line.strip().endswith(")"):
                    # Multi-line import
                    lines[typing_import_idx] = line.replace(")", ", Literal)")
                else:
                    # Single-line import
                    lines[typing_import_idx] = line.rstrip() + ", Literal\n"
        elif needs_literal_import:
            # No typing import found, add it after other imports
            last_import_idx = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(("from ", "import ")):
                    last_import_idx = i
            if last_import_idx is not None:
                lines.insert(last_import_idx + 1, "from typing import Literal\n")
            else:
                # No imports at all, add at the beginning
                lines.insert(2, "from typing import Literal\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Find end of RecaptchaSettings class
        if stripped.startswith("class RecaptchaSettings"):
            # Find the closing of this class (next class definition or Settings)
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("class "):
                    recaptcha_settings_end = j
                    break
        # Find Settings class
        if stripped.startswith("class Settings"):
            settings_class_start = i
            break

    if recaptcha_settings_end is None or settings_class_start is None:
        # Fallback: insert before Settings class
        for i, line in enumerate(lines):
            if line.strip().startswith("class Settings"):
                settings_class_start = i
                recaptcha_settings_end = i
                break

    # Prepare EmailSettings class definition
    email_settings_class = """class EmailSettings(BaseSettings):
    \"\"\"Email service configuration.\"\"\"

    model_config = _base_config

    enabled: bool = Field(default=True, validation_alias="EMAIL_ENABLED", description="Enable email service")
    adapter: Literal["file", "smtp"] = Field(default="file", validation_alias="EMAIL_ADAPTER", description="Email adapter type (file or smtp)")
    file_path: str = Field(default="./emails", validation_alias="EMAIL_FILE_PATH", description="Path for file email adapter")
    smtp_host: str = Field(default="localhost", validation_alias="SMTP_HOST", description="SMTP server host")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT", description="SMTP server port")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER", description="SMTP username")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD", description="SMTP password")
    smtp_from: str = Field(default="noreply@example.com", validation_alias="SMTP_FROM", description="Default from email address")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS", description="Use TLS for SMTP connection")


"""

    # Insert EmailSettings class
    lines.insert(recaptcha_settings_end, email_settings_class)

    # Now add email field to Settings class
    # Find where to insert (after recaptcha field, before legacy compatibility comment)
    email_field_added = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check if email field already exists
        if "email: EmailSettings" in line:
            email_field_added = True
            break
        # Find recaptcha field in Settings class
        if stripped.startswith("recaptcha: RecaptchaSettings"):
            # Insert email field after recaptcha
            indent = len(line) - len(line.lstrip())
            email_field = f"{' ' * indent}email: EmailSettings = Field(default_factory=EmailSettings)\n"
            lines.insert(i + 1, email_field)
            email_field_added = True
            break
        # Fallback: find legacy compatibility comment
        if stripped.startswith("# Legacy compatibility"):
            # Insert before legacy comment
            indent = len(line) - len(line.lstrip())
            email_field = f"{' ' * indent}email: EmailSettings = Field(default_factory=EmailSettings)\n"
            lines.insert(i, email_field)
            email_field_added = True
            break

    if not email_field_added:
        # Last resort: add at the end of nested settings (before legacy comment)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("# Legacy compatibility"):
                indent = len(lines[i]) - len(lines[i].lstrip())
                email_field = f"{' ' * indent}email: EmailSettings = Field(default_factory=EmailSettings)\n"
                lines.insert(i, email_field)
                break

    # Write back to file
    new_content = "".join(lines)
    write_file(config_py_path, new_content)

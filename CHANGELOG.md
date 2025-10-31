# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-31

### Changed - Major Architecture Refactor

This release introduces the **Mirror Target Structure** architecture - a fundamental redesign of how modules and templates are organized in the registry.

#### Breaking Changes
- **New folder structure**: Modules moved from `fastapi_registry/modules/` to `fastapi_registry/example_project/app/modules/`
- **Template system redesigned**:
  - Most files are now real Python files (not templates)
  - Only files requiring variable substitution use `.j2` Jinja2 templates (in `templates_j2/`)
  - Reduced from ~100% templates to ~15% templates

#### What Changed
- **Registry structure now mirrors target project structure 1:1**
  - `example_project/` contains a complete, runnable FastAPI application
  - Files in `example_project/` are copied directly to user projects
  - Full IDE support: syntax highlighting, type checking, autocomplete work natively

- **New `example_project/` directory structure**:
  ```
  fastapi_registry/example_project/
  ├── main.py                    # Real Python file (not template)
  ├── requirements.txt
  ├── app/
  │   ├── core/                 # Core utilities
  │   ├── modules/              # Feature modules (auth, users)
  │   ├── api/                  # API routing
  │   └── exceptions/           # Exception handling
  └── tests/
  ```

- **Simplified template system**:
  - Created `templates_j2/` for Jinja2 templates (only ~3 files need templating)
  - Files with variables: `README.md.j2`, `env.j2`, `config.py.j2`
  - All other files are regular Python files

#### Benefits
- **Better Developer Experience**: Can now test modules locally in `example_project`
- **No Complex Transformations**: Direct file copying without string replacements
- **Clear Intent**: Easy to understand where files will be placed in user projects
- **Production-Ready**: `example_project` is a real, working FastAPI application

#### Technical Changes
- Refactored `cli.py` to work with new structure
- Updated `project_initializer.py` for Mirror Target approach
- Changed `registry.json` paths to point to `example_project/app/modules/`
- Updated package data paths in `pyproject.toml`

### Added
- Complete working example project in `fastapi_registry/example_project/`
- Architecture analysis document (`docs/ARCHITECTURE_ANALYSIS.md`)
- Local testing guide and automated test script (`docs/LOCAL_TESTING.md`, `test-cli.sh`)
- Backend documentation template (`app/README.md`) included in initialized projects
- Code quality config files (`.flake8`, `.pylintrc`, `mypy.ini`)

### Documentation
- Updated `CLAUDE.md` with new architecture principles
- Added usage examples and documentation to test scripts
- Enhanced README with Mirror Target Structure explanation

### Migration Guide
If you have modules or customizations based on v0.1.x:
1. The new structure requires updating module paths
2. Templates are now in `templates_j2/` with `.j2` extension
3. Regular module files moved to `example_project/app/modules/`

## [0.1.7] - 2025-10-XX

### Added
- Backend documentation template in initialized projects
- Enhanced JWT configuration

### Changed
- Bumped version for feature additions

## [0.1.6] - 2025-10-XX

### Changed
- Enhanced project template structure
- Improved template inclusion

## [0.1.4] - 2025-10-XX

### Fixed
- Critical security issues addressed
- Code quality improvements

## [0.1.0] - 2025-10-XX

### Added
- Initial release
- CLI implementation with Typer
- Project initialization command (`init`)
- Module management commands (`list`, `info`, `add`, `remove`)
- Auth module with JWT authentication
- Auto-configuration system
- Template-based project scaffolding

### Features
- Copy-based module installation (not package dependencies)
- Automatic updates to `main.py`, `requirements.txt`, and `.env`
- Production-ready modules with type hints
- Full Pydantic validation

[0.2.0]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.1.7...v0.2.0
[0.1.7]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.1.4...v0.1.6
[0.1.4]: https://github.com/jm-sky/fastapi-blocks-registry/releases/tag/v0.1.4
[0.1.0]: https://github.com/jm-sky/fastapi-blocks-registry/releases/tag/v0.1.0

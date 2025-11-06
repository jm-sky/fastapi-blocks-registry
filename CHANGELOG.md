# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes yet._

## [0.2.10] - 2025-11-06

### Added
- **CLI `--all` option**: Added `--all` (or `-a`) flag to the `init` command to automatically install all available modules from the registry after project initialization
  - Modules are automatically sorted by dependencies (topological sort) to ensure correct installation order
  - Provides detailed installation progress and summary (installed/failed counts)
  - Skips modules that already exist in the project
  - Enables quick setup of a complete FastAPI project with all modules in a single command

## [0.2.9] - 2025-11-05

### Added
- **Two-Factor Authentication (2FA) module**: Complete implementation of TOTP and WebAuthn/Passkeys support
  - **TOTP (Time-based One-Time Password)**: Full support for authenticator apps (Google Authenticator, Authy, etc.)
    - Setup flow with QR code generation
    - Verification with time window support
    - Backup codes (10 single-use codes, hashed storage)
    - Regeneration and disable functionality
    - Per-user rate limiting and account lockout
  - **WebAuthn/Passkeys**: Support for hardware security keys and biometric authentication
    - YubiKey, Touch ID, Face ID, Windows Hello compatibility
    - Registration and authentication flows
    - Multiple passkeys per user
    - Credential management (list, rename, delete)
  - **Security features**:
    - Encrypted TOTP secrets and WebAuthn public keys (Fernet encryption)
    - Hashed backup codes (SHA256)
    - Per-user rate limiting (configurable max attempts and lockout)
    - Global rate limiting on all endpoints
    - Audit logging integration
  - **API endpoints** (8 total):
    - `POST /two-factor/totp/initiate` - Start TOTP setup
    - `POST /two-factor/totp/verify` - Verify TOTP setup
    - `GET /two-factor/totp/status` - Get TOTP status
    - `POST /two-factor/totp/regenerate-backup-codes` - Regenerate backup codes
    - `POST /two-factor/totp/disable` - Disable TOTP
    - `POST /two-factor/totp/verify-login` - Verify 2FA during login
    - `POST /two-factor/webauthn/register/initiate` - Start passkey registration
    - `POST /two-factor/webauthn/register/complete` - Complete passkey registration
  - **Integration with auth module**:
    - `AuthServiceWith2FA` for seamless 2FA integration
    - Backward compatible - works with existing auth module
    - Optional dependency injection pattern
- **Unified JWT payload schema**: Complete JWT payload structure matching frontend TypeScript interface
  - All tokens now include `email`, `tfaPending`, `tfaVerified`, `tfaMethod` fields
  - Support for tenant context (`tid`, `trol`) for future multi-tenant features
  - TypedDict for token creation options (`CreateAccessTokenOptions`, `CreateRefreshTokenOptions`)
  - Extended `TwoFactorTokenPayload` with complete 2FA status fields

### Changed
- **JWT token creation functions**: All token creation functions now use TypedDict instead of `dict[str, Any]`
- **Access tokens**: Now include `email`, `tid`, `trol`, `tfaPending`, `tfaVerified`, `tfaMethod` fields
- **Refresh tokens**: Now preserve 2FA state (`tfaVerified`, `tfaMethod`) across token refresh cycles
- **2FA verification flow**: `verify_totp_login()` now sets `tfaVerified: true` and `tfaMethod: "totp"` in access tokens
- **Login endpoints**: Both `AuthService.login_user()` and `AuthServiceWith2FA.login_user()` now include email and 2FA fields
- **CLI test script**: Extended to include tests for `two_factor` module installation

### Fixed
- **Security**: Added validation in `get_current_user()` to reject tokens with `tfaPending: true` (prevents use of unverified 2FA tokens)
- **Token timestamps**: Fixed `exp` and `iat` fields to use Unix timestamps (int) instead of datetime objects
- **2FA token payload**: Now includes `email` field for better frontend integration

### Documentation
- Added comprehensive JWT flow documentation (`docs/JWT_FLOW.md`) - Complete guide to JWT states, flows, and 2FA integration
- Added JWT compatibility analysis (`docs/JWT_COMPATIBILITY_ANALYSIS.md`) - Backend compatibility assessment
- Updated `2FA_MODULE_PLAN.md` with link to JWT flow documentation
- Updated type definitions with detailed docstrings linking to documentation

### Technical Details
- **Module structure**: Follows repository pattern, service layer, and dependency injection (consistent with `auth` module)
- **Database models**: SQLAlchemy ORM models for `totp_configs` and `passkeys` tables
- **Encryption**: Fernet (symmetric encryption) for TOTP secrets and WebAuthn keys
- **Hashing**: SHA256 for backup codes (one-way, non-reversible)
- All token creation functions now explicitly use TypedDict for type safety
- Backward compatible: Old tokens without new fields will still work
- Refresh token preserves 2FA verification state but does NOT preserve tenant context (tid/trol) for security
- Module added to `registry.json` with full configuration and dependencies

## [0.2.8] - 2025-11-01

### Chore
- Version bump only; no functional changes (release housekeeping)

## [0.2.7] - 2025-11-03

### Added
- **Docker development support**: `docker-compose.yml` and related setup for local development
- **Django-like management commands** for user management under `example_project/cli`
- **Logs module and search functionality** with repository pattern
- **Automated testing script** and improved local testing workflow
- **PostgreSQL support** in the example project and configuration

### Changed
- **Authentication module** refactor to use `AuthService` and in-memory user store
- **Database management moved** to core module with updated imports
- **Enhanced type safety** and organization in authentication and related modules
- **Updated mypy configuration** for stricter type checking
- **Updated dependencies** (Typer, Pydantic email support), Python version requirements, and CORS settings

### Fixed
- Improved error handling in module import tests
- Exclude modules/common dirs from init; add `common_dependencies` support

### Documentation
- Enhanced local development and testing documentation

### Chore
- Version bumps in `pyproject.toml`
- Updated configuration files and code quality checks

## [0.2.6] - 2025-11-01

### Chore
- Version bump only; no functional changes (release housekeeping)

## [0.2.5] - 2025-11-01

### Added
- **Logs module, search functionality, and repository pattern**
- **Automated testing script** and updated `.gitignore`

### Changed
- **Authentication module**: improved type safety and organization
- **mypy configuration**: stricter type checking settings
- **Pydantic dependency**: include email-related support

### Fixed
- Better error handling in module import tests
- Exclude modules/common dirs from init; add `common_dependencies` support

### Chore
- Updated configuration files and code quality checks

## [0.2.4] - 2025-10-31

### Added
- **Authentication module refactor** to `AuthService` with in-memory user store

### Changed
- **Database management moved** to core module with updated imports

### Chore
- Version bump and removal of obsolete documentation files

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
[0.2.4]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.1...v0.2.4
[0.2.5]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.4...v0.2.5
[0.2.6]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.5...v0.2.6
[0.2.7]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.6...v0.2.7
[0.2.8]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.7...v0.2.8
[0.2.9]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.8...v0.2.9
[Unreleased]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.2.9...HEAD
[0.1.7]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/jm-sky/fastapi-blocks-registry/compare/v0.1.4...v0.1.6
[0.1.4]: https://github.com/jm-sky/fastapi-blocks-registry/releases/tag/v0.1.4
[0.1.0]: https://github.com/jm-sky/fastapi-blocks-registry/releases/tag/v0.1.0

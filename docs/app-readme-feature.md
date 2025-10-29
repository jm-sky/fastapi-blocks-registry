# App README Feature

## Overview
Added a comprehensive backend-specific README.md that gets created in the `app/` folder when users run `fastapi-registry init`.

## Changes Made

### 1. Created Template File
**File**: `fastapi_registry/templates/fastapi_project/app/README.md.template`

A comprehensive documentation file covering:
- **Directory Structure** - Explains the app/ folder organization
- **Module Architecture** - Details the layered architecture (router → service → models)
- **Core Components** - Documents config, database, dependencies, exception handlers
- **Best Practices** - Code examples for routers, schemas, dependencies, error handling
- **Adding Modules** - Instructions for both CLI and manual module creation
- **Security Considerations** - Important security guidelines
- **Testing** - Test structure and commands
- **Common Patterns** - Pagination, filtering, async operations
- **Debugging** - Tips for debugging the backend
- **Additional Resources** - Links to FastAPI, Pydantic, SQLAlchemy docs

### 2. Updated Project Initializer
**File**: `fastapi_registry/core/project_initializer.py`
- Added `"app/README.md.template": project_path / "app" / "README.md"` to the templates dictionary
- Ensures the README is copied when `fastapi-registry init` is run

### 3. Updated Main README
**File**: `README.md`
- Added mention of `app/README.md` in the "What Gets Installed" section
- Updated the `init` command description to highlight the backend documentation
- Updated project structure diagram to show the template location

## Benefits

1. **Better Developer Experience**: New developers can understand the backend structure immediately
2. **Consistent Architecture**: Documents the layered architecture (router → service → models)
3. **Best Practices**: Provides code examples following FastAPI best practices
4. **Self-Documenting**: Each generated project has its own backend documentation
5. **Learning Resource**: Serves as a reference for FastAPI patterns and conventions

## Testing

Verified that:
- ✅ Template file exists and is properly formatted (8,587 bytes)
- ✅ File is correctly copied during `init` command
- ✅ Content is properly rendered (8,326 bytes after variable substitution)
- ✅ No linter errors in any modified files

## Usage

When developers run:
```bash
fastapi-registry init --name "My API"
```

They will now get:
```
my-api/
├── README.md              # Project-level README
├── app/
│   ├── README.md         # ← New! Backend-specific documentation
│   ├── api/
│   ├── core/
│   └── modules/
...
```

The `app/README.md` provides comprehensive documentation specifically for the FastAPI backend architecture.


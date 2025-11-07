# Docker Compose Double Braces Issue

## Problem
The `docker-compose.dev.yml` and `docker-compose.yml` files use incorrect syntax for environment variable substitution: `${{VARIABLE}}` (double braces) instead of the correct Docker Compose syntax.

## Details
Docker Compose uses `${VARIABLE}` or `$VARIABLE` syntax for environment variable substitution, not `${{VARIABLE}}`.

The double braces `${{}}` syntax is used in:
- GitHub Actions workflows
- Some CI/CD systems
- But **NOT** in Docker Compose

## Affected Files
- `backend/docker-compose.dev.yml`
- `backend/docker-compose.yml`

## Examples of Incorrect Syntax
```yaml
environment:
  - POSTGRES_DB=${{POSTGRES_DB:-backend}}  # ❌ WRONG - double braces
  - POSTGRES_USER=${{POSTGRES_USER:-backend}}  # ❌ WRONG
  - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD:-changeme}}  # ❌ WRONG
  - DATABASE_URL=postgresql+asyncpg://${{POSTGRES_USER:-backend}}:${{POSTGRES_PASSWORD:-changeme}}@db:5432/${{POSTGRES_DB:-backend}}  # ❌ WRONG
```

## Correct Syntax
Docker Compose supports two syntaxes:

1. **With default value** (using `${VARIABLE:-default}`):
```yaml
environment:
  - POSTGRES_DB=${POSTGRES_DB:-backend}  # ✅ CORRECT
  - POSTGRES_USER=${POSTGRES_USER:-backend}  # ✅ CORRECT
  - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}  # ✅ CORRECT
  - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-backend}:${POSTGRES_PASSWORD:-changeme}@db:5432/${POSTGRES_DB:-backend}  # ✅ CORRECT
```

2. **Simple substitution** (using `$VARIABLE`):
```yaml
environment:
  - POSTGRES_DB=$POSTGRES_DB  # ✅ CORRECT (if variable is always set)
```

## Impact
- Docker Compose will **not** substitute these variables correctly
- Variables will be treated as literal strings `${{POSTGRES_DB:-backend}}` instead of being evaluated
- This can cause:
  - Database connection failures
  - Incorrect configuration
  - Services failing to start with expected values

## Recommendation
Replace all instances of `${{VARIABLE}}` with `${VARIABLE}` in:
- `docker-compose.dev.yml`
- `docker-compose.yml`

The CLI should generate Docker Compose files with correct syntax: `${VARIABLE:-default}` instead of `${{VARIABLE:-default}}`.

## References
- Docker Compose variable substitution: https://docs.docker.com/compose/environment-variables/substitute-variables-in-compose-files/
- The `${VARIABLE:-default}` syntax is standard POSIX shell parameter expansion


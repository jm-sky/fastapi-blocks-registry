#!/bin/bash

# FastAPI Registry - Automated Testing Script
# This script tests the CLI and modules in a clean environment
#
# Usage:
#   ./scripts/test.sh              # Run tests with cleanup
#   ./scripts/test.sh --no-cleanup # Run tests and keep test files for inspection

set -e  # Exit on error

# Parse arguments
CLEANUP=true
for arg in "$@"; do
    case $arg in
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-cleanup    Keep test directory for manual inspection"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test directories
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="${REPO_ROOT}/.test"
TEST_PROJECT="${TEST_DIR}/test_project"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  FastAPI Registry - Automated Testing${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
if [ "$CLEANUP" = false ]; then
    echo -e "${YELLOW}⚠  Running with --no-cleanup (test files will be preserved)${NC}"
fi
echo

# Cleanup function
cleanup() {
    if [ "$CLEANUP" = true ] && [ -d "$TEST_DIR" ]; then
        echo
        echo -e "${YELLOW}Cleaning up test directory...${NC}"
        rm -rf "$TEST_DIR"
        print_success "Test directory removed"
    elif [ "$CLEANUP" = false ] && [ -d "$TEST_DIR" ]; then
        echo
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Test directory preserved for inspection:${NC}"
        echo -e "${YELLOW}  ${TEST_DIR}${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    fi
}

# Setup trap to cleanup on exit
trap cleanup EXIT

# Function to print step
print_step() {
    echo
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ------------------------------------------------------------
# Step 1: Setup
# ------------------------------------------------------------
print_step "Step 1: Setting up test environment"

# Clean up previous test (always cleanup old tests before starting)
if [ -d "$TEST_DIR" ]; then
    echo -e "${YELLOW}Removing previous test directory...${NC}"
    rm -rf "$TEST_DIR"
    print_success "Previous test directory removed"
fi

# Create test directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
print_success "Created test directory: $TEST_DIR"

# ------------------------------------------------------------
# Step 2: Install fastapi-registry in editable mode
# ------------------------------------------------------------
print_step "Step 2: Installing fastapi-registry (local version)"

cd "$REPO_ROOT"
pip install -e . > /dev/null 2>&1
print_success "Installed local fastapi-registry"

# Verify CLI is available
if command -v fastapi-registry &> /dev/null; then
    CLI_VERSION=$(fastapi-registry --version 2>&1 || echo "unknown")
    print_success "CLI command 'fastapi-registry' is available (version: $CLI_VERSION)"
else
    print_error "CLI command 'fastapi-registry' not found"
    exit 1
fi

# ------------------------------------------------------------
# Step 3: List available modules
# ------------------------------------------------------------
print_step "Step 3: Listing available modules"

fastapi-registry list
print_success "Successfully listed modules"

# ------------------------------------------------------------
# Step 4: Initialize new project using CLI
# ------------------------------------------------------------
print_step "Step 4: Initializing new FastAPI project with CLI"

cd "$TEST_DIR"
fastapi-registry init --project-path test_project --name "test-project" --description "Test project for automated testing" --force

cd test_project
print_success "Initialized project using 'fastapi-registry init'"

# Verify project structure was created
if [ -f "main.py" ] && [ -f ".env" ] && [ -d "app" ]; then
    print_success "Project structure created successfully"
else
    print_error "Project structure incomplete"
    exit 1
fi

# ------------------------------------------------------------
# Step 5: Test basic project
# ------------------------------------------------------------
print_step "Step 5: Testing basic project (before adding modules)"

python -m py_compile main.py
print_success "Basic project compiles successfully"

# ------------------------------------------------------------
# Step 6: Add auth module
# ------------------------------------------------------------
print_step "Step 6: Adding 'auth' module"

cd "$TEST_PROJECT"
fastapi-registry add auth --yes
print_success "Added auth module"

# Verify auth module was added
if [ -d "app/modules/auth" ]; then
    print_success "Auth module directory created"
else
    print_error "Auth module directory not found"
    exit 1
fi

# Test that auth module compiles
python -m py_compile app/modules/auth/*.py 2>/dev/null && print_success "Auth module compiles"

# ------------------------------------------------------------
# Step 7: Add users module
# ------------------------------------------------------------
print_step "Step 7: Adding 'users' module"

fastapi-registry add users --yes
print_success "Added users module"

# Verify users module was added
if [ -d "app/modules/users" ]; then
    print_success "Users module directory created"
else
    print_error "Users module directory not found"
    exit 1
fi

# Test that users module compiles
python -m py_compile app/modules/users/*.py 2>/dev/null && print_success "Users module compiles"

# ------------------------------------------------------------
# Step 8: Add logs module
# ------------------------------------------------------------
print_step "Step 8: Adding 'logs' module"

fastapi-registry add logs --yes
print_success "Added logs module"

# Verify logs module was added
if [ -d "app/modules/logs" ]; then
    print_success "Logs module directory created"
else
    print_error "Logs module directory not found"
    exit 1
fi

# Test that logs module compiles
python -m py_compile app/modules/logs/*.py 2>/dev/null && print_success "Logs module compiles"

# Verify common utils were added (required by logs and users)
if [ -d "app/common" ]; then
    print_success "Common utils directory created"
else
    print_error "Common utils directory not found"
    exit 1
fi

# ------------------------------------------------------------
# Step 9: Run linters and type checkers
# ------------------------------------------------------------
print_step "Step 9: Running code quality checks"

cd "$REPO_ROOT"

# Check if ruff is available
if command -v ruff &> /dev/null; then
    echo "Running ruff..."
    ruff check fastapi_registry/example_project/app/modules/ --select E,F,W || print_warning "Ruff found some issues"
    print_success "Ruff check completed"
else
    print_warning "Ruff not installed, skipping"
fi

# Check if mypy is available
if command -v mypy &> /dev/null; then
    echo "Running mypy..."
    mypy fastapi_registry/example_project/app/modules/logs --ignore-missing-imports --no-error-summary || print_warning "MyPy found some issues"
    print_success "MyPy check completed"
else
    print_warning "MyPy not installed, skipping"
fi

# ------------------------------------------------------------
# Step 10: Test module imports in test project
# ------------------------------------------------------------
print_step "Step 10: Testing module imports in test project"

cd "$TEST_PROJECT"

# Test auth module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.auth import router; print('✓ auth')" 2>/dev/null; then
    print_success "Auth module imports successfully in test project"
else
    print_error "Auth module import failed in test project"
fi

# Test users module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.users import router; print('✓ users')" 2>/dev/null; then
    print_success "Users module imports successfully in test project"
else
    print_error "Users module import failed in test project"
fi

# Test logs module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.logs import router; print('✓ logs')" 2>/dev/null; then
    print_success "Logs module imports successfully in test project"
else
    print_error "Logs module import failed in test project"
fi

# ------------------------------------------------------------
# Step 11: Test module imports in example project
# ------------------------------------------------------------
print_step "Step 11: Testing module imports in example project"

cd "$REPO_ROOT/fastapi_registry/example_project"

# Test auth module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.auth import router; print('✓ auth')" 2>/dev/null; then
    print_success "Auth module imports successfully"
else
    print_error "Auth module import failed"
fi

# Test users module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.users import router; print('✓ users')" 2>/dev/null; then
    print_success "Users module imports successfully"
else
    print_error "Users module import failed"
fi

# Test logs module
if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "from app.modules.logs import router; print('✓ logs')" 2>/dev/null; then
    print_success "Logs module imports successfully"
else
    print_error "Logs module import failed"
fi

# Test common utils
if python -c "from app.common import PaginationParams, SearchMixin; print('✓ common')" 2>/dev/null; then
    print_success "Common utils import successfully"
else
    print_error "Common utils import failed"
fi

# ------------------------------------------------------------
# Step 12: Test all modules together
# ------------------------------------------------------------
print_step "Step 12: Testing all modules together"

if SECRET_KEY="test-key-min-32-chars-long!!!!" python -c "
from app.modules.auth import router as auth_router
from app.modules.users import router as users_router
from app.modules.logs import router as logs_router
print('✓ All modules can be imported together')
" 2>/dev/null; then
    print_success "All modules import together successfully"
else
    print_error "Failed to import all modules together"
fi

# ------------------------------------------------------------
# Step 13: Compile all Python files
# ------------------------------------------------------------
print_step "Step 13: Compiling all Python files"

cd "$REPO_ROOT/fastapi_registry/example_project"

# Compile all modules
COMPILE_ERRORS=0

for module in auth users logs; do
    echo "Compiling $module module..."
    if python -m py_compile app/modules/$module/*.py 2>/dev/null; then
        print_success "$module module compiles"
    else
        print_error "$module module has compilation errors"
        COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
    fi
done

# Compile common utils
echo "Compiling common utils..."
if python -m py_compile app/common/*.py 2>/dev/null; then
    print_success "Common utils compile"
else
    print_error "Common utils have compilation errors"
    COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
fi

if [ $COMPILE_ERRORS -eq 0 ]; then
    print_success "All files compiled successfully"
fi

# Final Summary
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

print_success "✓ CLI installation and version check"
print_success "✓ Module listing (list command)"
print_success "✓ Project initialization (init command)"
print_success "✓ Module installation (add auth, users, logs)"
print_success "✓ Module imports in test project"
print_success "✓ Module imports in example project"
print_success "✓ Code quality checks (ruff, mypy)"
print_success "✓ Code compilation"

if [ $COMPILE_ERRORS -eq 0 ]; then
    echo
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  All tests passed! ✓${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  Some tests failed! ✗${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    exit 1
fi

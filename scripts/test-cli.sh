#!/bin/bash
# Test local installation of fastapi-blocks-registry
#
# This script performs a comprehensive test of the CLI by:
# - Creating a test virtual environment
# - Installing the package in editable mode
# - Testing all CLI commands (list, info, init, add)
# - Verifying project structure and file contents
# - Checking template variable substitution
# - Validating module installation
#
# Usage:
#   ./scripts/test-cli.sh
#
# Example:
#   cd /home/madeyskij/projects/private/fastapi-blocks-registry
#   ./scripts/test-cli.sh
#
# The script will:
# 1. Create temporary test environment
# 2. Run all tests
# 3. Clean up automatically on exit
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed

set -e  # Exit on error

echo "🧪 Testing fastapi-blocks-registry local installation"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    rm -rf /tmp/test-fastapi-registry-env /tmp/test-fastapi-project
}

# Trap cleanup on exit
trap cleanup EXIT

echo -e "\n${YELLOW}1. Creating test virtual environment...${NC}"
python -m venv /tmp/test-fastapi-registry-env
source /tmp/test-fastapi-registry-env/bin/activate

echo -e "\n${YELLOW}2. Installing package in editable mode...${NC}"
pip install -e . -q

echo -e "\n${YELLOW}3. Testing CLI availability...${NC}"
if ! command -v fastapi-registry &> /dev/null; then
    echo -e "${RED}❌ CLI not available!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ CLI available${NC}"

echo -e "\n${YELLOW}4. Testing --version...${NC}"
fastapi-registry --version

echo -e "\n${YELLOW}5. Testing list command...${NC}"
fastapi-registry list

echo -e "\n${YELLOW}6. Testing info command...${NC}"
fastapi-registry info auth

echo -e "\n${YELLOW}7. Testing init command...${NC}"
fastapi-registry init --project-path /tmp/test-fastapi-project --name "TestProject" --description "A test project" --force

if [ ! -d "/tmp/test-fastapi-project" ]; then
    echo -e "${RED}❌ Project not created!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Project created${NC}"

echo -e "\n${YELLOW}8. Checking project structure...${NC}"
required_files=(
    "/tmp/test-fastapi-project/main.py"
    "/tmp/test-fastapi-project/requirements.txt"
    "/tmp/test-fastapi-project/.env"
    "/tmp/test-fastapi-project/app/core/config.py"
    "/tmp/test-fastapi-project/app/modules/__init__.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Missing file: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required files present${NC}"

echo -e "\n${YELLOW}9. Testing template variable substitution...${NC}"
if grep -q "TestProject" /tmp/test-fastapi-project/README.md; then
    echo -e "${GREEN}✅ README.md variables substituted${NC}"
else
    echo -e "${RED}❌ README.md variables NOT substituted${NC}"
    exit 1
fi

if grep -q "TestProject" /tmp/test-fastapi-project/.env; then
    echo -e "${GREEN}✅ .env variables substituted${NC}"
else
    echo -e "${RED}❌ .env variables NOT substituted${NC}"
    exit 1
fi

echo -e "\n${YELLOW}10. Testing add module command...${NC}"
cd /tmp/test-fastapi-project
fastapi-registry add auth --yes

if [ ! -d "/tmp/test-fastapi-project/app/modules/auth" ]; then
    echo -e "${RED}❌ Auth module not added!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Auth module added${NC}"

echo -e "\n${YELLOW}11. Checking module files...${NC}"
module_files=(
    "/tmp/test-fastapi-project/app/modules/auth/models.py"
    "/tmp/test-fastapi-project/app/modules/auth/router.py"
    "/tmp/test-fastapi-project/app/modules/auth/schemas.py"
    "/tmp/test-fastapi-project/app/modules/auth/service.py"
)

for file in "${module_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Missing module file: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All module files present${NC}"

echo -e "\n${YELLOW}12. Checking dependencies...${NC}"
if grep -q "PyJWT" /tmp/test-fastapi-project/requirements.txt; then
    echo -e "${GREEN}✅ Dependencies added to requirements.txt${NC}"
else
    echo -e "${RED}❌ Dependencies NOT added${NC}"
    exit 1
fi

echo -e "\n${YELLOW}13. Checking environment variables...${NC}"
if grep -q "SECRET_KEY" /tmp/test-fastapi-project/.env; then
    echo -e "${GREEN}✅ Auth env variables added${NC}"
else
    echo -e "${RED}❌ Auth env variables NOT added${NC}"
    exit 1
fi

echo -e "\n${GREEN}=================================================="
echo -e "✅ ALL TESTS PASSED!"
echo -e "==================================================${NC}\n"

echo -e "${YELLOW}📦 Package is ready for publication!${NC}"
echo -e "\nNext steps:"
echo -e "  1. Bump version in pyproject.toml"
echo -e "  2. python -m build"
echo -e "  3. python -m twine upload dist/*"

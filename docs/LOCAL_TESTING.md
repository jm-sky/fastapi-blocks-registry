# Local Testing Guide

This guide explains how to test `fastapi-blocks-registry` locally before publishing to PyPI.

## Quick Test (Automated)

Run the automated test script:

```bash
./scripts/test-cli.sh
```

This script will:
- ✅ Create a test virtual environment
- ✅ Install the package in editable mode
- ✅ Test all CLI commands
- ✅ Verify project initialization
- ✅ Test module installation
- ✅ Check template variable substitution
- ✅ Verify dependencies and env variables

## Manual Testing Methods

### Method 1: Editable Install (Recommended for Development)

Best for active development - changes are immediately reflected:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Now test from anywhere
cd /tmp
fastapi-registry --help
fastapi-registry list
fastapi-registry init my-test-project --name "TestProject"
cd my-test-project
fastapi-registry add auth --yes
```

**Advantages:**
- Changes in code are immediately visible (no reinstall needed)
- Full CLI functionality
- Realistic testing environment

### Method 2: Build and Install from Wheel

Test exactly as end-users will experience it:

```bash
# 1. Build the package
source .venv/bin/activate
pip install build
python -m build

# This creates:
# - dist/fastapi_blocks_registry-0.1.7-py3-none-any.whl
# - dist/fastapi_blocks_registry-0.1.7.tar.gz

# 2. Create fresh test environment
cd /tmp
python -m venv test-env
source test-env/bin/activate

# 3. Install from built wheel
pip install /path/to/fastapi-blocks-registry/dist/fastapi_blocks_registry-0.1.7-py3-none-any.whl

# 4. Test
fastapi-registry --version
fastapi-registry init my-project
cd my-project
fastapi-registry add auth
```

**Advantages:**
- Tests the exact package that will be published
- Verifies packaging configuration
- Catches distribution issues early

### Method 3: Test with TestPyPI

Upload to TestPyPI before publishing to real PyPI:

```bash
# 1. Build package
python -m build

# 2. Upload to TestPyPI
pip install twine
python -m twine upload --repository testpypi dist/*

# You'll need TestPyPI credentials:
# Username: __token__
# Password: your-testpypi-token

# 3. Install from TestPyPI (in fresh environment)
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    fastapi-blocks-registry

# Note: --extra-index-url for dependencies not on TestPyPI

# 4. Test
fastapi-registry --help
```

**Advantages:**
- Tests the complete upload/download cycle
- Verifies package metadata
- Safe testing before real publication

## Test Checklist

Before publishing, verify:

### CLI Functionality
- [ ] `fastapi-registry --version` shows correct version
- [ ] `fastapi-registry list` displays all modules
- [ ] `fastapi-registry info <module>` shows detailed info
- [ ] `fastapi-registry init` creates project structure
- [ ] `fastapi-registry add <module>` installs modules
- [ ] `fastapi-registry remove <module>` removes modules

### Project Initialization
- [ ] All required files created (main.py, requirements.txt, .env, etc.)
- [ ] Directory structure matches expected layout
- [ ] Template variables substituted correctly:
  - [ ] `{project_name}` in README.md
  - [ ] `{project_name}` in .env
  - [ ] `{project_description}` in README.md and .env
  - [ ] `{secret_key}` in .env

### Module Installation
- [ ] Module files copied to correct location
- [ ] Dependencies added to requirements.txt (no duplicates)
- [ ] Environment variables added to .env (no overwrites)
- [ ] Router registered in app/api/router.py

### Edge Cases
- [ ] Init in non-empty directory (with --force)
- [ ] Adding module that already exists (should fail gracefully)
- [ ] Invalid project names (should validate)
- [ ] Missing registry.json (should error clearly)

## Example Test Session

```bash
# 1. Install locally
source .venv/bin/activate
pip install -e .

# 2. Create test project
cd /tmp
rm -rf my-test-app
fastapi-registry init my-test-app --name "MyTestApp" --description "Testing locally"
cd my-test-app

# 3. Verify files
ls -la
cat README.md | head -5
cat .env | head -5

# 4. Add modules
fastapi-registry add auth --yes
fastapi-registry add users --yes

# 5. Check structure
ls -la app/modules/
cat requirements.txt | grep -E "PyJWT|passlib"

# 6. Try to run (optional - requires deps installed)
pip install -r requirements.txt
python main.py
# Should show: Uvicorn running on http://0.0.0.0:8000
```

## Troubleshooting

### "Command not found: fastapi-registry"

```bash
# Check installation
pip list | grep fastapi-blocks-registry

# Reinstall
pip uninstall fastapi-blocks-registry -y
pip install -e .
```

### "Module not found" errors

```bash
# Check you're in correct environment
which python
which fastapi-registry

# Verify package structure
python -c "import fastapi_registry; print(fastapi_registry.__file__)"
```

### Template variables not substituted

```bash
# Check templates_j2 directory exists
ls -la fastapi_registry/templates_j2/

# Verify .j2 files have correct content
cat fastapi_registry/templates_j2/README.md.j2 | grep "{project_name}"
```

## Publishing Checklist

Before `twine upload`:

1. **Version bump**
   ```bash
   # Update version in pyproject.toml
   vim pyproject.toml
   ```

2. **Run tests**
   ```bash
   ./scripts/test-cli.sh
   ```

3. **Clean dist/**
   ```bash
   rm -rf dist/
   ```

4. **Build**
   ```bash
   python -m build
   ```

5. **Check distribution**
   ```bash
   python -m twine check dist/*
   ```

6. **Upload to TestPyPI first**
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

7. **Test install from TestPyPI**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       fastapi-blocks-registry
   ```

8. **Upload to PyPI**
   ```bash
   python -m twine upload dist/*
   ```

## Automated Testing in CI/CD

For GitHub Actions or similar:

```yaml
# .github/workflows/test.yml
name: Test CLI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install package
        run: pip install -e .
      - name: Run tests
        run: ./scripts/test-cli.sh
```

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [TestPyPI](https://test.pypi.org/)
- [pip install Documentation](https://pip.pypa.io/en/stable/cli/pip_install/)

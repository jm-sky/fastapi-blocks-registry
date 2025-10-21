# Publishing to PyPI

This guide explains how to publish `fastapi-blocks-registry` to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - TestPyPI: https://test.pypi.org/account/register/
   - PyPI: https://pypi.org/account/register/

2. **API Tokens**: Generate API tokens for uploading:
   - TestPyPI: https://test.pypi.org/manage/account/#api-tokens
   - PyPI: https://pypi.org/manage/account/token/

3. **Install Build Tools**: Already installed in your virtual environment
   ```bash
   pip install build twine
   ```

## Step 1: Build the Package

The package is already built! You can see the distribution files in `dist/`:
- `fastapi_blocks_registry-0.1.0-py3-none-any.whl` - Wheel distribution
- `fastapi_blocks_registry-0.1.0.tar.gz` - Source distribution

To rebuild:
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build new distributions
python -m build
```

## Step 2: Check Package with Twine

Verify the package is well-formed:
```bash
twine check dist/*
```

## Step 3: Upload to TestPyPI (Recommended First)

Test your package on TestPyPI before publishing to production:

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# You'll be prompted for:
# - Username: __token__
# - Password: <your TestPyPI API token>
```

## Step 4: Test Installation from TestPyPI

Create a new virtual environment and test installation:
```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  fastapi-blocks-registry

# Test the CLI
fastapi-registry --version
fastapi-registry list

# Clean up
deactivate
rm -rf test-env
```

## Step 5: Upload to Production PyPI

Once everything works on TestPyPI:

```bash
twine upload dist/*

# You'll be prompted for:
# - Username: __token__
# - Password: <your PyPI API token>
```

## Step 6: Verify Installation from PyPI

Test that users can install your package:
```bash
pip install fastapi-blocks-registry
fastapi-registry --version
```

## Using .pypirc for Authentication (Optional)

Create `~/.pypirc` to avoid entering credentials each time:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-<your-production-token>

[testpypi]
username = __token__
password = pypi-<your-test-token>
repository = https://test.pypi.org/legacy/
```

**Important**: Keep this file secure! Add to `.gitignore` if in project directory.

## Publishing New Versions

1. **Update Version Number**:
   Edit `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. **Update CHANGELOG** (create if needed):
   Document what changed

3. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Release v0.2.0"
   git tag v0.2.0
   git push && git push --tags
   ```

4. **Rebuild and Upload**:
   ```bash
   rm -rf dist/ build/ *.egg-info
   python -m build
   twine check dist/*
   twine upload dist/*
   ```

## Troubleshooting

### Package Already Exists
If you get "File already exists" error:
- You can't re-upload the same version
- Increment version number and rebuild

### Import Errors After Installation
- Check that `registry.json` is included
- Verify MANIFEST.in includes all necessary files
- Use `python -m zipfile -l dist/*.whl` to inspect wheel contents

### Module Not Found
- Ensure all `__init__.py` files exist
- Check package structure in `pyproject.toml`

## Automation with GitHub Actions (Future)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Current Status

✅ Package is built and ready to publish
✅ License file included (MIT)
✅ README with usage instructions
✅ All module files included
✅ CLI entry point configured

**Next Steps**:
1. Create PyPI and TestPyPI accounts
2. Generate API tokens
3. Upload to TestPyPI for testing
4. Upload to PyPI for production release

## Package Information

- **Name**: `fastapi-blocks-registry`
- **Current Version**: `0.1.0`
- **License**: MIT
- **Python Version**: >=3.12
- **Homepage**: https://github.com/jm-sky/fastapi-blocks-registry

## Useful Links

- PyPI Package URL (after publishing): https://pypi.org/project/fastapi-blocks-registry/
- TestPyPI URL: https://test.pypi.org/project/fastapi-blocks-registry/
- Documentation: https://github.com/jm-sky/fastapi-blocks-registry#readme

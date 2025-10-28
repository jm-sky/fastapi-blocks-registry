"""FastAPI Blocks Registry - Modular scaffolding system for FastAPI backends."""

from importlib.metadata import version

try:
    __version__ = version("fastapi-blocks-registry")
except Exception:
    # Fallback for development when package is not installed
    __version__ = "0.0.0+dev"

__author__ = "FastAPI Blocks Registry Contributors"
__description__ = "A modular scaffolding system for FastAPI backends, inspired by shadcn-vue"

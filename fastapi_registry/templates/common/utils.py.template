"""Common utility functions."""

from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_dict(obj: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """
    Convert object to dictionary.

    Args:
        obj: Object to convert
        exclude: Set of fields to exclude

    Returns:
        Dictionary representation
    """
    if hasattr(obj, "model_dump"):
        # Pydantic model
        return obj.model_dump(exclude=exclude or set())
    elif hasattr(obj, "dict"):
        # Pydantic v1
        return obj.dict(exclude=exclude or set())
    elif hasattr(obj, "__dict__"):
        # Regular object
        data = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        if exclude:
            data = {k: v for k, v in data.items() if k not in exclude}
        return data
    else:
        return {}

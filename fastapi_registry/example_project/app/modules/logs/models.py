"""Pydantic models for logging system.

This module provides Pydantic models for log entries used in API
validation and serialization.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .db_models import LogLevel


class Log(BaseModel):
    """Log entry model with camelCase fields for API responses.

    This model represents a log entry as it appears in the database
    and API responses.
    """

    id: str
    level: LogLevel
    message: str
    module: str | None = None
    function: str | None = None
    userId: str | None = Field(None, alias="user_id")
    requestId: str | None = Field(None, alias="request_id")
    traceback: str | None = None
    extraData: str | None = Field(None, alias="extra_data")
    createdAt: datetime = Field(alias="created_at")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

    def to_response(self) -> dict[str, Any]:
        """Convert to camelCase response format."""
        return {
            "id": self.id,
            "level": self.level.value,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "userId": self.userId,
            "requestId": self.requestId,
            "traceback": self.traceback,
            "extraData": self.extraData,
            "createdAt": self.createdAt
        }


class LogCreate(BaseModel):
    """Model for creating a new log entry.

    Used when manually creating logs through the API or service layer.
    """

    level: LogLevel
    message: str
    module: str | None = None
    function: str | None = None
    userId: str | None = None
    requestId: str | None = None
    traceback: str | None = None
    extraData: str | None = None

    model_config = {
        "populate_by_name": True
    }

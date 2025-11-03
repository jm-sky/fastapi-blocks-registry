"""Pydantic schemas for logs API.

This module provides request and response schemas for the logs API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .db_models import LogLevel


class LogResponse(BaseModel):
    """Response model for a single log entry."""

    id: str
    level: str
    message: str
    module: str | None = None
    function: str | None = None
    userId: str | None = None
    requestId: str | None = None
    traceback: str | None = None
    extraData: str | None = None
    createdAt: datetime

    model_config = {
        "from_attributes": True
    }


class LogCreateRequest(BaseModel):
    """Request model for creating a log entry."""

    level: LogLevel
    message: str = Field(..., min_length=1, max_length=10000)
    module: str | None = Field(None, max_length=255)
    function: str | None = Field(None, max_length=255)
    userId: str | None = Field(None, max_length=36)
    requestId: str | None = Field(None, max_length=100)
    traceback: str | None = None
    extraData: str | None = None


class LogListResponse(BaseModel):
    """Response model for paginated list of logs."""

    logs: list[LogResponse]
    total: int
    skip: int
    limit: int


class LogFilterParams(BaseModel):
    """Query parameters for filtering logs."""

    level: LogLevel | None = None
    userId: str | None = None
    requestId: str | None = None
    module: str | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class LogStatsResponse(BaseModel):
    """Response model for log statistics."""

    total: int
    byLevel: dict[str, int] = Field(default_factory=dict)
    recentErrors: int
    oldestLog: datetime | None = None
    newestLog: datetime | None = None

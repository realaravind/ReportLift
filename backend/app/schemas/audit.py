"""Audit log Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of auditable events."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ANALYSIS = "ANALYSIS"
    CONVERSION = "CONVERSION"
    CONFIG_CHANGE = "CONFIG_CHANGE"


class AuditStatus(str, Enum):
    """Status of the audited action."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry.

    Internal use only - not exposed via API.
    """

    event_type: EventType
    action: str = Field(..., max_length=255)
    status: AuditStatus
    user_id: int | None = None
    username: str | None = Field(None, max_length=255)
    resource_type: str | None = Field(None, max_length=50)
    resource_id: str | None = Field(None, max_length=255)
    details: dict[str, Any] | None = None
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = None


class AuditLogResponse(BaseModel):
    """Schema for audit log API responses.

    Excludes sensitive data and internal fields.
    """

    id: str
    timestamp: datetime
    event_type: EventType
    status: AuditStatus
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None

    model_config = {"from_attributes": True}


class AuditLogDetailResponse(BaseModel):
    """Schema for detailed audit log response including details JSON.

    Admin-only endpoint.
    """

    id: str
    timestamp: datetime
    event_type: EventType
    status: AuditStatus
    user_id: int | None = None
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs in queries."""

    # Date range filters
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Event filters
    event_type: EventType | None = None
    status: AuditStatus | None = None

    # User filters
    user_id: int | None = None
    username: str | None = None

    # Resource filters
    resource_type: str | None = None
    resource_id: str | None = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response."""

    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class AuditEventRequest(BaseModel):
    """Schema for manually logging an audit event (admin use)."""

    event_type: EventType
    action: str = Field(..., max_length=255)
    status: AuditStatus = AuditStatus.SUCCESS
    resource_type: str | None = Field(None, max_length=50)
    resource_id: str | None = Field(None, max_length=255)
    details: dict[str, Any] | None = None


class AuditSummary(BaseModel):
    """Schema for audit log summary statistics."""

    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_status: dict[str, int] = Field(default_factory=dict)
    events_today: int = 0
    events_this_week: int = 0
    unique_users: int = 0
    most_active_user: str | None = None

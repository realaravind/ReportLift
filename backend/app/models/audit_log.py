"""Audit log model for tracking user actions for compliance."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


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


class AuditLog(Base):
    """Audit log entry for tracking user actions.

    Stores all auditable events including:
    - Authentication events (login/logout)
    - Report analysis events
    - Report conversion events
    - Configuration changes

    Audit logs are retained until explicitly deleted by admin (NFR17).
    """

    __tablename__ = "audit_logs"

    # Primary key - UUID for audit trail portability
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Timestamp with timezone
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Event classification
    event_type = Column(String(20), nullable=False)  # LOGIN, LOGOUT, ANALYSIS, etc.
    status = Column(String(10), nullable=False)  # SUCCESS, FAILURE

    # User information (denormalized for historical reference)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(255), nullable=True)  # Stored for historical reference

    # Action details
    action = Column(String(255), nullable=False)  # Description of the action

    # Resource information
    resource_type = Column(String(50), nullable=True)  # report, connection, template
    resource_id = Column(String(255), nullable=True)  # ID of affected resource

    # Additional event data (JSON for flexibility)
    details = Column(JSON, nullable=True)  # Event-specific data

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="audit_logs")

    # Table-level indexes
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id[:8]}... {self.event_type} {self.status}>"

    @classmethod
    def create(
        cls,
        event_type: EventType,
        action: str,
        status: AuditStatus,
        user_id: int | None = None,
        username: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "AuditLog":
        """Factory method to create an audit log entry."""
        return cls(
            event_type=event_type.value,
            action=action,
            status=status.value,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

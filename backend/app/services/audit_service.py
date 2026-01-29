"""Audit Service - Handles audit logging for compliance.

Provides non-blocking audit logging with retry logic for failed writes.
Supports all auditable events: LOGIN, LOGOUT, ANALYSIS, CONVERSION, CONFIG_CHANGE.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditStatus, EventType
from app.schemas.audit import (
    AuditLogCreate,
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    AuditSummary,
)

logger = logging.getLogger(__name__)

# Keys that should be redacted from details
SENSITIVE_KEYS = frozenset({
    "password",
    "token",
    "secret",
    "credential",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "session_id",
    "auth",
    "authorization",
})


@dataclass
class AuditEntry:
    """Internal audit entry for queue processing."""

    event_type: EventType
    action: str
    status: AuditStatus
    user_id: int | None = None
    username: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditService:
    """Service for handling audit log operations.

    Provides both synchronous and asynchronous logging methods.
    Implements retry logic for failed database writes.
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds
    MAX_QUEUE_SIZE = 1000

    def __init__(self):
        """Initialize the audit service."""
        self._queue: asyncio.Queue[AuditEntry] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._processing = False
        self._failed_entries: list[AuditEntry] = []

    def sanitize_details(self, details: dict[str, Any] | None) -> dict[str, Any] | None:
        """Remove sensitive data from details dictionary.

        Args:
            details: Dictionary containing event-specific data

        Returns:
            Sanitized dictionary with sensitive values redacted
        """
        if not details:
            return None

        def redact_value(key: str, value: Any) -> Any:
            """Recursively redact sensitive values."""
            key_lower = key.lower()

            # Check if key contains any sensitive pattern
            if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                return "[REDACTED]"

            # Recursively handle nested dictionaries
            if isinstance(value, dict):
                return {k: redact_value(k, v) for k, v in value.items()}

            # Handle lists
            if isinstance(value, list):
                return [
                    redact_value(key, item) if isinstance(item, dict) else item
                    for item in value
                ]

            return value

        return {k: redact_value(k, v) for k, v in details.items()}

    def log_event_sync(
        self,
        db: Session,
        event_type: EventType,
        action: str,
        status: AuditStatus,
        user_id: int | None = None,
        username: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog | None:
        """Synchronously log an audit event.

        Use this when you need confirmation the log was written.

        Args:
            db: Database session
            event_type: Type of event (LOGIN, LOGOUT, etc.)
            action: Description of the action
            status: SUCCESS or FAILURE
            user_id: ID of the user (if known)
            username: Username for historical reference
            resource_type: Type of resource affected
            resource_id: ID of the resource
            details: Additional event-specific data
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry or None on failure
        """
        try:
            audit_log = AuditLog.create(
                event_type=event_type,
                action=action,
                status=status,
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                details=self.sanitize_details(details),
                ip_address=ip_address,
                user_agent=user_agent,
            )

            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)

            logger.debug(
                f"Audit log created: {event_type.value} - {action}",
                extra={
                    "audit_id": audit_log.id,
                    "event_type": event_type.value,
                    "status": status.value,
                },
            )

            return audit_log

        except Exception as e:
            logger.error(
                f"Failed to write audit log: {e}",
                extra={
                    "event_type": event_type.value,
                    "action": action,
                    "error": str(e),
                },
            )
            db.rollback()
            return None

    async def log_event(
        self,
        event_type: EventType,
        action: str,
        status: AuditStatus,
        user_id: int | None = None,
        username: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Asynchronously queue an audit event for logging.

        Non-blocking - returns immediately after queuing.

        Args:
            event_type: Type of event
            action: Description of the action
            status: SUCCESS or FAILURE
            user_id: ID of the user
            username: Username for historical reference
            resource_type: Type of resource affected
            resource_id: ID of the resource
            details: Additional event-specific data
            ip_address: Client IP address
            user_agent: Client user agent string
        """
        entry = AuditEntry(
            event_type=event_type,
            action=action,
            status=status,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=self.sanitize_details(details),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        try:
            self._queue.put_nowait(entry)
        except asyncio.QueueFull:
            logger.warning(
                "Audit queue full, dropping oldest entry",
                extra={"event_type": event_type.value, "action": action},
            )
            # Drop oldest and add new
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(entry)
            except asyncio.QueueEmpty:
                pass

    async def process_queue(self, db_factory) -> None:
        """Process queued audit entries with retry logic.

        Should be called periodically by a background task.

        Args:
            db_factory: Factory function that returns a database session
        """
        if self._processing:
            return

        self._processing = True
        try:
            # Process pending entries
            entries_processed = 0
            max_entries_per_batch = 100

            while not self._queue.empty() and entries_processed < max_entries_per_batch:
                try:
                    entry = self._queue.get_nowait()
                    success = await self._write_entry(entry, db_factory)

                    if not success and entry.retry_count < self.MAX_RETRIES:
                        entry.retry_count += 1
                        self._failed_entries.append(entry)

                    entries_processed += 1

                except asyncio.QueueEmpty:
                    break

            # Retry failed entries
            await self._retry_failed_entries(db_factory)

        finally:
            self._processing = False

    async def _write_entry(self, entry: AuditEntry, db_factory) -> bool:
        """Write a single audit entry to the database.

        Args:
            entry: Audit entry to write
            db_factory: Factory function that returns a database session

        Returns:
            True if successful, False otherwise
        """
        try:
            db = db_factory()
            try:
                audit_log = AuditLog.create(
                    event_type=entry.event_type,
                    action=entry.action,
                    status=entry.status,
                    user_id=entry.user_id,
                    username=entry.username,
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    details=entry.details,
                    ip_address=entry.ip_address,
                    user_agent=entry.user_agent,
                )
                # Use the original created_at timestamp
                audit_log.timestamp = entry.created_at

                db.add(audit_log)
                db.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to write audit entry: {e}")
                db.rollback()
                return False
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            return False

    async def _retry_failed_entries(self, db_factory) -> None:
        """Retry failed audit entries with exponential backoff.

        Args:
            db_factory: Factory function that returns a database session
        """
        if not self._failed_entries:
            return

        entries_to_retry = self._failed_entries.copy()
        self._failed_entries.clear()

        for entry in entries_to_retry:
            # Exponential backoff delay
            delay = self.RETRY_BASE_DELAY * (2 ** (entry.retry_count - 1))
            await asyncio.sleep(delay)

            success = await self._write_entry(entry, db_factory)

            if not success:
                if entry.retry_count < self.MAX_RETRIES:
                    entry.retry_count += 1
                    self._failed_entries.append(entry)
                else:
                    logger.error(
                        f"Audit entry dropped after {self.MAX_RETRIES} retries",
                        extra={
                            "event_type": entry.event_type.value,
                            "action": entry.action,
                        },
                    )

    # Convenience methods for specific event types

    def log_login(
        self,
        db: Session,
        username: str,
        success: bool,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log a login event.

        Args:
            db: Database session
            username: Username attempting login
            success: Whether login was successful
            user_id: User ID if known
            ip_address: Client IP
            user_agent: Client user agent
            details: Additional details

        Returns:
            Created AuditLog entry
        """
        return self.log_event_sync(
            db=db,
            event_type=EventType.LOGIN,
            action=f"User login {'succeeded' if success else 'failed'}",
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    def log_logout(
        self,
        db: Session,
        username: str,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog | None:
        """Log a logout event.

        Args:
            db: Database session
            username: Username logging out
            user_id: User ID
            ip_address: Client IP

        Returns:
            Created AuditLog entry
        """
        return self.log_event_sync(
            db=db,
            event_type=EventType.LOGOUT,
            action="User logged out",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
        )

    def log_analysis(
        self,
        db: Session,
        report_path: str,
        report_name: str,
        score: int | None,
        success: bool,
        user_id: int | None = None,
        username: str | None = None,
        analysis_id: int | None = None,
        duration_ms: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog | None:
        """Log a report analysis event.

        Args:
            db: Database session
            report_path: Path to the analyzed report
            report_name: Name of the report
            score: Analysis score
            success: Whether analysis succeeded
            user_id: User ID
            username: Username
            analysis_id: ID of the analysis record
            duration_ms: How long analysis took
            ip_address: Client IP

        Returns:
            Created AuditLog entry
        """
        return self.log_event_sync(
            db=db,
            event_type=EventType.ANALYSIS,
            action=f"Report analyzed: {report_name}",
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            user_id=user_id,
            username=username,
            resource_type="report",
            resource_id=report_path,
            details={
                "report_name": report_name,
                "score": score,
                "analysis_id": analysis_id,
                "duration_ms": duration_ms,
            },
            ip_address=ip_address,
        )

    def log_conversion(
        self,
        db: Session,
        report_path: str,
        report_name: str,
        success: bool,
        user_id: int | None = None,
        username: str | None = None,
        conversion_id: int | None = None,
        output_files: list[str] | None = None,
        duration_ms: int | None = None,
        ip_address: str | None = None,
        error_message: str | None = None,
    ) -> AuditLog | None:
        """Log a report conversion event.

        Args:
            db: Database session
            report_path: Path to the converted report
            report_name: Name of the report
            success: Whether conversion succeeded
            user_id: User ID
            username: Username
            conversion_id: ID of the conversion job
            output_files: List of generated output files
            duration_ms: How long conversion took
            ip_address: Client IP
            error_message: Error message if failed

        Returns:
            Created AuditLog entry
        """
        details = {
            "report_name": report_name,
            "conversion_id": conversion_id,
            "output_files": output_files,
            "duration_ms": duration_ms,
        }
        if error_message:
            details["error"] = error_message

        return self.log_event_sync(
            db=db,
            event_type=EventType.CONVERSION,
            action=f"Report converted: {report_name}",
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            user_id=user_id,
            username=username,
            resource_type="report",
            resource_id=report_path,
            details=details,
            ip_address=ip_address,
        )

    def log_config_change(
        self,
        db: Session,
        setting_name: str,
        old_value: Any,
        new_value: Any,
        user_id: int | None = None,
        username: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog | None:
        """Log a configuration change event.

        Args:
            db: Database session
            setting_name: Name of the setting changed
            old_value: Previous value (will be sanitized)
            new_value: New value (will be sanitized)
            user_id: User ID
            username: Username
            ip_address: Client IP

        Returns:
            Created AuditLog entry
        """
        return self.log_event_sync(
            db=db,
            event_type=EventType.CONFIG_CHANGE,
            action=f"Configuration changed: {setting_name}",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            username=username,
            resource_type="configuration",
            resource_id=setting_name,
            details={
                "setting_name": setting_name,
                "old_value": old_value,
                "new_value": new_value,
            },
            ip_address=ip_address,
        )


# Query functions for API routes

def get_audit_logs(
    db: Session,
    filters: AuditLogFilter,
) -> AuditLogListResponse:
    """Get paginated audit logs with filters.

    Args:
        db: Database session
        filters: Filter parameters

    Returns:
        Paginated list of audit logs
    """
    query = db.query(AuditLog)

    # Apply filters
    conditions = []

    if filters.start_date:
        conditions.append(AuditLog.timestamp >= filters.start_date)

    if filters.end_date:
        conditions.append(AuditLog.timestamp <= filters.end_date)

    if filters.event_type:
        conditions.append(AuditLog.event_type == filters.event_type.value)

    if filters.status:
        conditions.append(AuditLog.status == filters.status.value)

    if filters.user_id:
        conditions.append(AuditLog.user_id == filters.user_id)

    if filters.username:
        conditions.append(AuditLog.username.ilike(f"%{filters.username}%"))

    if filters.resource_type:
        conditions.append(AuditLog.resource_type == filters.resource_type)

    if filters.resource_id:
        conditions.append(AuditLog.resource_id == filters.resource_id)

    if conditions:
        query = query.filter(and_(*conditions))

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (filters.page - 1) * filters.page_size
    logs = (
        query.order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )

    # Calculate total pages
    total_pages = (total + filters.page_size - 1) // filters.page_size

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def get_audit_log_by_id(db: Session, log_id: str) -> AuditLog | None:
    """Get a single audit log by ID.

    Args:
        db: Database session
        log_id: UUID of the audit log

    Returns:
        AuditLog if found, None otherwise
    """
    return db.query(AuditLog).filter(AuditLog.id == log_id).first()


def get_audit_summary(db: Session, days: int = 7) -> AuditSummary:
    """Get audit log summary statistics.

    Args:
        db: Database session
        days: Number of days to include in summary

    Returns:
        Summary statistics
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    # Total events
    total_events = db.query(func.count(AuditLog.id)).scalar() or 0

    # Events by type
    type_counts = (
        db.query(AuditLog.event_type, func.count(AuditLog.id))
        .group_by(AuditLog.event_type)
        .all()
    )
    events_by_type = {t: c for t, c in type_counts}

    # Events by status
    status_counts = (
        db.query(AuditLog.status, func.count(AuditLog.id))
        .group_by(AuditLog.status)
        .all()
    )
    events_by_status = {s: c for s, c in status_counts}

    # Events today
    events_today = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= today)
        .scalar()
    ) or 0

    # Events this week
    events_this_week = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= week_ago)
        .scalar()
    ) or 0

    # Unique users
    unique_users = (
        db.query(func.count(func.distinct(AuditLog.user_id)))
        .filter(AuditLog.user_id.isnot(None))
        .scalar()
    ) or 0

    # Most active user
    most_active = (
        db.query(AuditLog.username, func.count(AuditLog.id).label("count"))
        .filter(AuditLog.username.isnot(None))
        .group_by(AuditLog.username)
        .order_by(func.count(AuditLog.id).desc())
        .first()
    )

    return AuditSummary(
        total_events=total_events,
        events_by_type=events_by_type,
        events_by_status=events_by_status,
        events_today=events_today,
        events_this_week=events_this_week,
        unique_users=unique_users,
        most_active_user=most_active[0] if most_active else None,
    )


# Singleton instance
_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """Get the singleton audit service instance.

    Returns:
        AuditService singleton instance
    """
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def reset_audit_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _audit_service
    _audit_service = None

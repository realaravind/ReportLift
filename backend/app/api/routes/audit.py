"""Audit API routes for accessing audit logs.

All audit log endpoints require authentication. Only admin users
can access the full audit log with details.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.middleware import get_client_ip, get_user_agent
from app.models.audit_log import EventType, AuditStatus
from app.schemas.auth import UserInfo
from app.schemas.audit import (
    AuditLogDetailResponse,
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    AuditSummary,
    AuditEventRequest,
    EventType as SchemaEventType,
    AuditStatus as SchemaAuditStatus,
)
from app.services.audit_service import (
    get_audit_logs,
    get_audit_log_by_id,
    get_audit_summary,
    get_audit_service,
)
from app.services.audit_export_service import (
    export_to_csv_string,
    export_to_json_string,
    export_to_pdf,
    get_export_estimate,
    generate_export_filename,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


# Response wrappers
class AuditLogListAPIResponse(BaseModel):
    """API response wrapper for audit log list."""

    data: AuditLogListResponse
    meta: dict = Field(default_factory=dict)


class AuditLogDetailAPIResponse(BaseModel):
    """API response wrapper for audit log detail."""

    data: AuditLogDetailResponse
    meta: dict = Field(default_factory=dict)


class AuditSummaryAPIResponse(BaseModel):
    """API response wrapper for audit summary."""

    data: AuditSummary
    meta: dict = Field(default_factory=dict)


@router.get(
    "/logs",
    response_model=AuditLogListAPIResponse,
    summary="List audit logs",
    description="Get paginated list of audit logs with filtering support.",
)
def list_audit_logs(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    # Filter parameters
    start_date: datetime | None = Query(None, description="Filter logs from this date"),
    end_date: datetime | None = Query(None, description="Filter logs until this date"),
    event_type: SchemaEventType | None = Query(None, description="Filter by event type"),
    audit_status: SchemaAuditStatus | None = Query(None, alias="status", description="Filter by status"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    username: str | None = Query(None, description="Filter by username (partial match)"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListAPIResponse:
    """Get paginated list of audit logs.

    Supports filtering by date range, event type, status, user, and resource.
    Results are sorted by timestamp descending (newest first).
    """
    filters = AuditLogFilter(
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        status=audit_status,
        user_id=user_id,
        username=username,
        resource_type=resource_type,
        resource_id=resource_id,
        page=page,
        page_size=page_size,
    )

    result = get_audit_logs(db, filters)

    return AuditLogListAPIResponse(
        data=result,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogDetailAPIResponse,
    summary="Get audit log detail",
    description="Get detailed information about a specific audit log entry.",
)
def get_audit_log_detail(
    log_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> AuditLogDetailAPIResponse:
    """Get detailed audit log entry by ID.

    Returns full audit log details including the details JSON field.
    """
    log = get_audit_log_by_id(db, log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AUDIT_LOG_NOT_FOUND", "message": f"Audit log {log_id} not found"},
        )

    return AuditLogDetailAPIResponse(
        data=AuditLogDetailResponse.model_validate(log),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get(
    "/summary",
    response_model=AuditSummaryAPIResponse,
    summary="Get audit summary",
    description="Get summary statistics for audit logs.",
)
def get_audit_log_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    days: int = Query(7, ge=1, le=365, description="Number of days to include in summary"),
) -> AuditSummaryAPIResponse:
    """Get audit log summary statistics.

    Returns counts by event type, status, and user activity metrics.
    """
    summary = get_audit_summary(db, days)

    return AuditSummaryAPIResponse(
        data=summary,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.post(
    "/logs",
    response_model=AuditLogDetailAPIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create audit log",
    description="Manually create an audit log entry (admin use).",
)
def create_audit_log(
    request: Request,
    event_request: AuditEventRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> AuditLogDetailAPIResponse:
    """Manually create an audit log entry.

    This endpoint is for administrative use to manually log events
    that aren't captured automatically.
    """
    # Get user info from database
    from app.models.user import User

    user = db.query(User).filter(User.full_identity == current_user.identity).first()
    user_id = user.id if user else None

    # Get request context
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    audit_service = get_audit_service()
    log = audit_service.log_event_sync(
        db=db,
        event_type=EventType(event_request.event_type.value),
        action=event_request.action,
        status=AuditStatus(event_request.status.value),
        user_id=user_id,
        username=current_user.identity,
        resource_type=event_request.resource_type,
        resource_id=event_request.resource_id,
        details=event_request.details,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AUDIT_LOG_FAILED", "message": "Failed to create audit log entry"},
        )

    return AuditLogDetailAPIResponse(
        data=AuditLogDetailResponse.model_validate(log),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get(
    "/my-activity",
    response_model=AuditLogListAPIResponse,
    summary="Get my activity",
    description="Get audit logs for the current user.",
)
def get_my_activity(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListAPIResponse:
    """Get audit logs for the current authenticated user.

    Returns only logs for the current user's activity.
    """
    filters = AuditLogFilter(
        username=current_user.identity,
        page=page,
        page_size=page_size,
    )

    result = get_audit_logs(db, filters)

    return AuditLogListAPIResponse(
        data=result,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


# Export format enum
class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


# Export request schema
class ExportRequest(BaseModel):
    """Request schema for audit log export."""

    date_from: datetime | None = Field(None, description="Start date for export")
    date_to: datetime | None = Field(None, description="End date for export")
    event_types: list[SchemaEventType] | None = Field(None, description="Filter by event types")
    format: ExportFormat = Field(ExportFormat.CSV, description="Export format")


# Export estimate response
class ExportEstimateResponse(BaseModel):
    """Response schema for export estimate."""

    data: dict
    meta: dict = Field(default_factory=dict)


@router.get(
    "/export/estimate",
    response_model=ExportEstimateResponse,
    summary="Estimate export size",
    description="Get an estimate of export size before generating.",
)
def estimate_export(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    date_from: datetime | None = Query(None, description="Start date"),
    date_to: datetime | None = Query(None, description="End date"),
    event_type: SchemaEventType | None = Query(None, description="Filter by event type"),
) -> ExportEstimateResponse:
    """Get an estimate of export size.

    Returns estimated row count and file size to help users
    decide whether to proceed with export.
    """
    filters = AuditLogFilter(
        start_date=date_from,
        end_date=date_to,
        event_type=event_type,
    )

    estimate = get_export_estimate(db, filters)

    return ExportEstimateResponse(
        data=estimate,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.post(
    "/export",
    summary="Export audit logs",
    description="Export audit logs in CSV, JSON, or PDF format.",
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/json": {},
                "application/pdf": {},
            },
            "description": "Export file download",
        },
    },
)
def export_audit_logs(
    request: Request,
    export_request: ExportRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> Response:
    """Export audit logs to the specified format.

    Generates and returns the export file for download.
    For large exports (>10,000 rows), consider using the estimate
    endpoint first to check the size.
    """
    # Build filters
    filters = AuditLogFilter(
        start_date=export_request.date_from,
        end_date=export_request.date_to,
        event_type=export_request.event_types[0] if export_request.event_types else None,
    )

    # Generate filename
    filename = generate_export_filename(
        export_request.format.value,
        export_request.date_from,
        export_request.date_to,
    )

    # Get user info for audit logging
    from app.models.user import User

    user = db.query(User).filter(User.full_identity == current_user.identity).first()
    user_id = user.id if user else None

    # Generate export based on format
    if export_request.format == ExportFormat.CSV:
        content = export_to_csv_string(db, filters)
        media_type = "text/csv"
        row_count = content.count("\n") - 1  # Subtract header row
    elif export_request.format == ExportFormat.JSON:
        content = export_to_json_string(db, filters)
        media_type = "application/json"
        # Parse to get row count
        import json
        data = json.loads(content)
        row_count = data.get("export_metadata", {}).get("total_records", 0)
    elif export_request.format == ExportFormat.PDF:
        buffer = export_to_pdf(db, filters)
        content = buffer.getvalue()
        media_type = "application/pdf"
        # Estimate row count from filters
        estimate = get_export_estimate(db, filters)
        row_count = estimate.get("estimated_rows", 0)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FORMAT", "message": f"Unsupported format: {export_request.format}"},
        )

    # Log the export action
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONFIG_CHANGE,
            action="Audit logs exported",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            username=current_user.identity,
            resource_type="audit_export",
            details={
                "date_range": {
                    "from": export_request.date_from.isoformat() if export_request.date_from else None,
                    "to": export_request.date_to.isoformat() if export_request.date_to else None,
                },
                "format": export_request.format.value,
                "event_types_filter": [et.value for et in export_request.event_types] if export_request.event_types else None,
                "row_count": row_count,
                "file_size_bytes": len(content) if isinstance(content, (str, bytes)) else 0,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log export audit event: %s", audit_error)

    # Return response with appropriate content type
    if isinstance(content, str):
        content = content.encode("utf-8")

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

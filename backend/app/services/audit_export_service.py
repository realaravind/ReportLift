"""Audit Export Service - Handles exporting audit logs to various formats.

Supports CSV, JSON, and PDF export formats with streaming for large datasets.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Iterator

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditStatus, EventType
from app.schemas.audit import AuditLogFilter

logger = logging.getLogger(__name__)

# CSV column headers
CSV_HEADERS = [
    "Timestamp",
    "User",
    "Event Type",
    "Action",
    "Resource Type",
    "Resource ID",
    "Status",
    "IP Address",
    "Details",
]


def _build_export_query(db: Session, filters: AuditLogFilter):
    """Build the query for export based on filters.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        SQLAlchemy query object
    """
    query = db.query(AuditLog)

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

    return query.order_by(AuditLog.timestamp.desc())


def get_export_estimate(db: Session, filters: AuditLogFilter) -> dict:
    """Get an estimate of the export size.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        Dictionary with estimated row count and size
    """
    query = _build_export_query(db, filters)
    count = query.count()

    # Rough estimate: ~200 bytes per row for CSV, ~400 for JSON
    estimated_csv_size = count * 200
    estimated_json_size = count * 400

    return {
        "estimated_rows": count,
        "estimated_csv_size_bytes": estimated_csv_size,
        "estimated_json_size_bytes": estimated_json_size,
        "requires_async": count > 10000,
    }


def export_to_csv(db: Session, filters: AuditLogFilter) -> Iterator[str]:
    """Generate CSV export as a streaming iterator.

    Args:
        db: Database session
        filters: Export filter parameters

    Yields:
        CSV content as strings
    """
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Write header
    writer.writerow(CSV_HEADERS)
    yield output.getvalue()
    output.seek(0)
    output.truncate()

    # Stream data in batches
    query = _build_export_query(db, filters)
    batch_size = 1000
    offset = 0

    while True:
        batch = query.offset(offset).limit(batch_size).all()
        if not batch:
            break

        for log in batch:
            writer.writerow([
                log.timestamp.isoformat() if log.timestamp else "",
                log.username or "",
                log.event_type if log.event_type else "",
                log.action or "",
                log.resource_type or "",
                log.resource_id or "",
                log.status if log.status else "",
                log.ip_address or "",
                json.dumps(log.details) if log.details else "",
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate()

        offset += batch_size


def export_to_csv_string(db: Session, filters: AuditLogFilter) -> str:
    """Generate complete CSV export as a string.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        Complete CSV content as a string
    """
    return "".join(export_to_csv(db, filters))


def export_to_json(db: Session, filters: AuditLogFilter) -> dict:
    """Generate JSON export.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        Dictionary containing export metadata and logs
    """
    query = _build_export_query(db, filters)
    logs = query.all()

    # Build logs list
    logs_data = []
    for log in logs:
        logs_data.append({
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "event_type": log.event_type,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status": log.status,
        })

    return {
        "export_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date_range": {
                "from": filters.start_date.isoformat() if filters.start_date else None,
                "to": filters.end_date.isoformat() if filters.end_date else None,
            },
            "filters_applied": {
                "event_type": filters.event_type.value if filters.event_type else None,
                "status": filters.status.value if filters.status else None,
                "username": filters.username,
                "resource_type": filters.resource_type,
            },
            "total_records": len(logs_data),
        },
        "logs": logs_data,
    }


def export_to_json_string(db: Session, filters: AuditLogFilter, indent: int = 2) -> str:
    """Generate JSON export as a formatted string.

    Args:
        db: Database session
        filters: Export filter parameters
        indent: JSON indentation level

    Returns:
        Formatted JSON string
    """
    data = export_to_json(db, filters)
    return json.dumps(data, indent=indent, default=str)


def export_to_pdf(db: Session, filters: AuditLogFilter) -> BytesIO:
    """Generate PDF export.

    Creates a formatted PDF report with header, summary, and log table.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        BytesIO buffer containing PDF content
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
    except ImportError:
        logger.warning("reportlab not installed, falling back to simple text PDF")
        return _export_to_simple_pdf(db, filters)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    elements.append(Paragraph("ReportLift Audit Log Report", title_style))
    elements.append(Spacer(1, 12))

    # Export metadata
    meta_style = styles["Normal"]
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p %Z")
    elements.append(Paragraph(f"Generated: {generated_at}", meta_style))

    if filters.start_date or filters.end_date:
        date_from = filters.start_date.strftime("%B %d, %Y") if filters.start_date else "Beginning"
        date_to = filters.end_date.strftime("%B %d, %Y") if filters.end_date else "Now"
        elements.append(Paragraph(f"Date Range: {date_from} - {date_to}", meta_style))

    if filters.event_type:
        elements.append(Paragraph(f"Event Type Filter: {filters.event_type.value}", meta_style))

    elements.append(Spacer(1, 20))

    # Get summary statistics
    query = _build_export_query(db, filters)
    logs = query.all()
    total_count = len(logs)

    # Count by type
    type_counts = {}
    status_counts = {"SUCCESS": 0, "FAILURE": 0}
    for log in logs:
        event_type = log.event_type or "UNKNOWN"
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
        if log.status == "SUCCESS":
            status_counts["SUCCESS"] += 1
        else:
            status_counts["FAILURE"] += 1

    # Summary section
    elements.append(Paragraph("Summary Statistics", styles["Heading2"]))
    elements.append(Paragraph(f"Total Events: {total_count}", meta_style))

    if type_counts:
        type_summary = ", ".join([f"{k}: {v}" for k, v in sorted(type_counts.items())])
        elements.append(Paragraph(f"By Type: {type_summary}", meta_style))

    status_summary = f"Success: {status_counts['SUCCESS']}, Failure: {status_counts['FAILURE']}"
    elements.append(Paragraph(f"By Status: {status_summary}", meta_style))
    elements.append(Spacer(1, 20))

    # Logs table
    elements.append(Paragraph("Audit Log Entries", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    # Table data
    table_data = [["Timestamp", "User", "Type", "Action", "Status"]]

    for log in logs[:500]:  # Limit to 500 rows for PDF
        timestamp = log.timestamp.strftime("%m/%d %H:%M") if log.timestamp else ""
        table_data.append([
            timestamp,
            (log.username or "-")[:15],
            (log.event_type or "-")[:12],
            (log.action or "-")[:40],
            log.status or "-",
        ])

    if len(logs) > 500:
        table_data.append(["...", "...", "...", f"... and {len(logs) - 500} more rows", "..."])

    # Create table
    table = Table(table_data, colWidths=[1 * inch, 1.2 * inch, 1 * inch, 4 * inch, 0.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    elements.append(table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def _export_to_simple_pdf(db: Session, filters: AuditLogFilter) -> BytesIO:
    """Generate a simple text-based PDF when reportlab is not available.

    Args:
        db: Database session
        filters: Export filter parameters

    Returns:
        BytesIO buffer containing simple text content
    """
    # Fallback: return a text file if reportlab is not available
    buffer = BytesIO()

    query = _build_export_query(db, filters)
    logs = query.all()

    lines = []
    lines.append("=" * 60)
    lines.append("ReportLift Audit Log Report")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Total Records: {len(logs)}")
    lines.append("")
    lines.append("-" * 60)

    for log in logs:
        lines.append(f"Timestamp: {log.timestamp.isoformat() if log.timestamp else 'N/A'}")
        lines.append(f"User: {log.username or 'N/A'}")
        lines.append(f"Type: {log.event_type or 'N/A'}")
        lines.append(f"Action: {log.action or 'N/A'}")
        lines.append(f"Status: {log.status or 'N/A'}")
        lines.append("-" * 60)

    content = "\n".join(lines)
    buffer.write(content.encode("utf-8"))
    buffer.seek(0)
    return buffer


def generate_export_filename(
    format_type: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> str:
    """Generate a filename for the export.

    Args:
        format_type: Export format (csv, json, pdf)
        start_date: Start date of the export range
        end_date: End date of the export range

    Returns:
        Formatted filename string
    """
    date_from = start_date.strftime("%Y-%m-%d") if start_date else "all"
    date_to = end_date.strftime("%Y-%m-%d") if end_date else datetime.now().strftime("%Y-%m-%d")

    extension = format_type.lower()
    if extension == "pdf" and format_type == "txt":
        extension = "txt"

    return f"audit_logs_{date_from}_{date_to}.{extension}"

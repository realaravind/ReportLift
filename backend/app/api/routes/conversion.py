"""Conversion API routes for report conversion operations."""

import io
import logging
import os
import zipfile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.middleware import get_client_ip, get_user_agent
from app.models.analysis import Analysis
from app.models.audit_log import EventType, AuditStatus
from app.models.user import User
from app.services.audit_service import get_audit_service
from app.schemas.conversion import (
    ConversionRequest,
    ConversionJobCreate,
    ConversionProgressResponse,
    ConversionResult,
    ConversionErrorResponse,
    ConversionCancelResponse,
    ConversionStatus,
    SnowflakeWarning,
    DownloadableFile,
    ConversionOutputsResponse,
    DownloadFileType,
    ConversionSummaryResponse,
    SummaryStatus,
    ReportInfo,
    DatasetSummary,
    VisualSummary,
    ExpressionSummary,
    StoredProcedureSummary,
    ConvertedSummary,
    AttentionItem,
    SummaryFile,
)
from app.services.converter import (
    check_snowflake_configuration,
    create_conversion_job,
    get_conversion_job,
    get_conversion_by_analysis,
    cancel_conversion,
    run_conversion,
    get_output_files,
    ConversionError,
)
from app.services.conversion_flagging import (
    get_flagging_service,
    VerificationRequest,
    VerificationResult,
    VerificationAction,
    VerificationStatus,
    UncertainConversionsSummary,
    UncertainConversionDetails,
    ConversionFlag,
)
from app.services.sp_rewriter_ai import AIConfidenceLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversions", tags=["conversions"])


class ErrorDetail(BaseModel):
    """Error details."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: dict | None = Field(default=None, description="Additional details")
    can_retry: bool = Field(default=True, description="Whether operation can be retried")


def _run_conversion_background(db_url: str, job_id: str) -> None:
    """Background task to run conversion.

    This runs in a separate thread with its own database session.
    """
    from app.models.base import SessionLocal

    db = SessionLocal()
    try:
        run_conversion(db, job_id)
    except Exception as e:
        logger.exception("Background conversion failed: %s", str(e))
    finally:
        db.close()


@router.get(
    "/snowflake-status",
    response_model=SnowflakeWarning,
    summary="Check Snowflake configuration status",
    description="Check if Snowflake is configured before initiating conversion.",
)
async def check_snowflake_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SnowflakeWarning:
    """Check Snowflake configuration status.

    Returns warning information if Snowflake is not configured.
    """
    return check_snowflake_configuration(db)


@router.post(
    "/analysis/{analysis_id}",
    response_model=ConversionJobCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate report conversion",
    description="Start conversion of an analyzed report to Power BI and SQL.",
    responses={
        400: {"description": "Conversion already in progress or invalid request"},
        404: {"description": "Analysis not found"},
        500: {"description": "Server error"},
    },
)
async def initiate_conversion(
    analysis_id: int,
    request: ConversionRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionJobCreate:
    """Initiate conversion of an analyzed report.

    This endpoint:
    1. Validates the analysis exists
    2. Checks Snowflake configuration (warns if not configured)
    3. Creates a conversion job
    4. Starts background conversion
    5. Returns job ID for status polling
    """
    logger.info(
        "Conversion requested by %s for analysis %d",
        current_user.username,
        analysis_id,
    )

    # Verify analysis exists
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="ANALYSIS_NOT_FOUND",
                message=f"Analysis {analysis_id} not found",
                can_retry=False,
            ).model_dump(),
        )

    # Check Snowflake configuration
    snowflake_warning = check_snowflake_configuration(db)
    if not snowflake_warning.is_configured and not request.force:
        # Return warning but still allow conversion to proceed
        logger.warning(
            "Snowflake not configured for conversion of analysis %d",
            analysis_id,
        )

    # Create conversion job
    try:
        job = create_conversion_job(db, analysis_id, current_user.id)
    except ConversionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code=e.code,
                message=e.message,
                details=e.details,
                can_retry=e.can_retry,
            ).model_dump(),
        )

    # Start background conversion
    background_tasks.add_task(
        _run_conversion_background,
        str(db.get_bind().url),
        job.job_id,
    )

    message = "Conversion started"
    if not snowflake_warning.is_configured:
        message = "Conversion started (Snowflake not configured - using placeholder schema)"

    return ConversionJobCreate(
        conversion_id=job.job_id,
        status=ConversionStatus(job.status),
        started_at=job.created_at,
        snowflake_configured=snowflake_warning.is_configured,
        message=message,
    )


@router.get(
    "/{conversion_id}",
    response_model=ConversionProgressResponse,
    summary="Get conversion status",
    description="Get the current status and progress of a conversion job.",
    responses={
        404: {"description": "Conversion not found"},
    },
)
async def get_conversion_status(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionProgressResponse:
    """Get the status of a conversion job.

    Poll this endpoint to track conversion progress.
    """
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    return ConversionProgressResponse(
        conversion_id=job.job_id,
        status=ConversionStatus(job.status),
        current_step=job.current_step,
        steps_completed=job.steps_completed or 0,
        total_steps=job.total_steps or 6,
        progress_percent=job.progress_percent,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
    )


@router.get(
    "/{conversion_id}/result",
    response_model=ConversionResult,
    summary="Get conversion result",
    description="Get the complete result of a successful conversion.",
    responses={
        404: {"description": "Conversion not found"},
        400: {"description": "Conversion not complete"},
    },
)
async def get_conversion_result(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionResult:
    """Get the result of a completed conversion.

    Returns file information for downloading converted outputs.
    """
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    if job.status != ConversionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="CONVERSION_NOT_COMPLETE",
                message=f"Conversion is {job.status}, not completed",
                can_retry=True,
            ).model_dump(),
        )

    output_files = get_output_files(job)

    return ConversionResult(
        conversion_id=job.job_id,
        status=ConversionStatus(job.status),
        report_name=job.report_name,
        report_path=job.report_path,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        snowflake_configured=job.snowflake_configured or False,
        snowflake_schema=job.snowflake_schema_used,
        output_files=output_files,
    )


@router.delete(
    "/{conversion_id}",
    response_model=ConversionCancelResponse,
    summary="Cancel conversion",
    description="Cancel an in-progress conversion job.",
    responses={
        404: {"description": "Conversion not found"},
        400: {"description": "Conversion cannot be cancelled"},
    },
)
async def cancel_conversion_job(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionCancelResponse:
    """Cancel a conversion job.

    Only pending or in-progress conversions can be cancelled.
    Partial output files will be discarded.
    """
    try:
        job = cancel_conversion(db, conversion_id)
    except ConversionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code=e.code,
                message=e.message,
                can_retry=False,
            ).model_dump(),
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    logger.info(
        "Conversion %s cancelled by user %s",
        conversion_id,
        current_user.username,
    )

    return ConversionCancelResponse(
        conversion_id=job.job_id,
        status=ConversionStatus.CANCELLED,
        message="Conversion cancelled successfully",
    )


@router.get(
    "/analysis/{analysis_id}/latest",
    response_model=ConversionProgressResponse | None,
    summary="Get latest conversion for analysis",
    description="Get the most recent conversion job for an analysis.",
)
async def get_latest_conversion_for_analysis(
    analysis_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionProgressResponse | None:
    """Get the latest conversion job for an analysis.

    Returns None if no conversion has been attempted.
    """
    job = get_conversion_by_analysis(db, analysis_id)
    if not job:
        return None

    return ConversionProgressResponse(
        conversion_id=job.job_id,
        status=ConversionStatus(job.status),
        current_step=job.current_step,
        steps_completed=job.steps_completed or 0,
        total_steps=job.total_steps or 6,
        progress_percent=job.progress_percent,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
    )


# Helper functions for downloads
def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _find_file_by_type(
    output_dir: str,
    output_files: list[str] | None,
    file_type: DownloadFileType,
) -> str | None:
    """Find a specific file type in the output directory.

    Args:
        output_dir: Path to output directory
        output_files: List of output file paths
        file_type: Type of file to find

    Returns:
        Path to the file if found, None otherwise
    """
    if not output_files or not output_dir:
        return None

    for filepath in output_files:
        filename = os.path.basename(filepath).lower()

        if file_type == DownloadFileType.PBIX:
            if filename.endswith(".pbix"):
                return filepath
        elif file_type == DownloadFileType.SQL:
            # Look for combined SQL file (all_scripts.sql or *_all.sql)
            if "all_scripts" in filename or filename.endswith("_all.sql"):
                return filepath
        elif file_type == DownloadFileType.ANALYSIS:
            if filename == "metadata.json" or filename.endswith("_analysis.json"):
                return filepath

    return None


def _create_sql_zip(output_dir: str, output_files: list[str], report_name: str) -> io.BytesIO:
    """Create a ZIP file containing all SQL scripts.

    Args:
        output_dir: Path to output directory
        output_files: List of output file paths
        report_name: Report name for README

    Returns:
        BytesIO containing the ZIP file
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        sql_files = []
        combined_sql = None

        for filepath in output_files:
            if not os.path.exists(filepath):
                continue

            filename = os.path.basename(filepath).lower()

            if filename.endswith(".sql"):
                # Add to scripts folder in ZIP
                arcname = f"scripts/{os.path.basename(filepath)}"
                zf.write(filepath, arcname)
                sql_files.append(os.path.basename(filepath))

                # Check for combined SQL
                if "all_scripts" in filename or filename.endswith("_all.sql"):
                    combined_sql = filepath

        # Add combined SQL to root if exists
        if combined_sql and os.path.exists(combined_sql):
            zf.write(combined_sql, "all_scripts.sql")

        # Add README
        readme_content = f"""# {report_name} - Snowflake SQL Scripts

This ZIP contains SQL scripts generated from the SSRS report conversion.

## Contents

### /scripts/
Individual SQL script files for each dataset:
{chr(10).join(f'- {f}' for f in sql_files)}

### all_scripts.sql
Combined SQL file containing all scripts.

## Usage

1. Review and customize the SQL scripts as needed
2. Execute in Snowflake in the following order:
   - Schema/table creation scripts first
   - View/procedure scripts second
   - Data transformation scripts last

## Generated

This package was generated by ReportLift.
"""
        zf.writestr("README.txt", readme_content)

    buffer.seek(0)
    return buffer


@router.get(
    "/{conversion_id}/outputs",
    response_model=ConversionOutputsResponse,
    summary="List available download files",
    description="Get list of all files available for download from a conversion.",
    responses={
        404: {"description": "Conversion not found"},
    },
)
async def list_conversion_outputs(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionOutputsResponse:
    """List all downloadable files for a conversion.

    Returns file information including size and download URLs.
    For incomplete conversions, returns a message and empty file list.
    """
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    # Handle incomplete conversions
    if job.status != ConversionStatus.COMPLETED.value:
        message = None
        if job.status == ConversionStatus.FAILED.value:
            message = f"Conversion failed: {job.error_message or 'Unknown error'}"
        elif job.status == ConversionStatus.CANCELLED.value:
            message = "Conversion was cancelled - no files available"
        elif job.status in [ConversionStatus.PENDING.value, ConversionStatus.IN_PROGRESS.value]:
            message = f"Conversion in progress ({job.progress_percent}% complete)"

        return ConversionOutputsResponse(
            conversion_id=job.job_id,
            status=ConversionStatus(job.status),
            report_name=job.report_name,
            generated_at=None,
            files=[],
            message=message,
        )

    # Build list of downloadable files
    files: list[DownloadableFile] = []
    base_url = f"/api/v1/conversions/{conversion_id}/download"

    # Check for PBIX file
    pbix_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.PBIX,
    )
    if pbix_path and os.path.exists(pbix_path):
        stat = os.stat(pbix_path)
        files.append(DownloadableFile(
            type="pbix",
            name=f"{job.report_name}_converted.pbix",
            size=stat.st_size,
            size_display=_format_file_size(stat.st_size),
            download_url=f"{base_url}/pbix",
            available=True,
        ))

    # Check for combined SQL file
    sql_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.SQL,
    )
    if sql_path and os.path.exists(sql_path):
        stat = os.stat(sql_path)
        files.append(DownloadableFile(
            type="sql",
            name=f"{job.report_name}_snowflake_scripts.sql",
            size=stat.st_size,
            size_display=_format_file_size(stat.st_size),
            download_url=f"{base_url}/sql",
            available=True,
        ))

    # SQL ZIP is always available if there are any SQL files
    sql_files = [f for f in (job.output_files or []) if f.endswith(".sql")]
    if sql_files:
        # Estimate ZIP size (usually smaller than sum of files)
        total_sql_size = sum(
            os.path.getsize(f) for f in sql_files if os.path.exists(f)
        )
        files.append(DownloadableFile(
            type="sql-zip",
            name=f"{job.report_name}_scripts.zip",
            size=total_sql_size,
            size_display=_format_file_size(total_sql_size),
            download_url=f"{base_url}/sql-zip",
            available=True,
        ))

    # Check for analysis/metadata file
    analysis_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.ANALYSIS,
    )
    if analysis_path and os.path.exists(analysis_path):
        stat = os.stat(analysis_path)
        files.append(DownloadableFile(
            type="analysis",
            name=f"{job.report_name}_analysis.json",
            size=stat.st_size,
            size_display=_format_file_size(stat.st_size),
            download_url=f"{base_url}/analysis",
            available=True,
        ))

    return ConversionOutputsResponse(
        conversion_id=job.job_id,
        status=ConversionStatus(job.status),
        report_name=job.report_name,
        generated_at=job.completed_at,
        files=files,
        message=None,
    )


@router.get(
    "/{conversion_id}/download/pbix",
    summary="Download Power BI file",
    description="Download the generated Power BI (.pbix) file.",
    responses={
        404: {"description": "File not found"},
        400: {"description": "Conversion incomplete"},
    },
)
async def download_pbix(
    conversion_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download the Power BI file for a completed conversion."""
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    if job.status != ConversionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="CONVERSION_INCOMPLETE",
                message="Conversion incomplete - no files available",
                details={"status": job.status},
                can_retry=True,
            ).model_dump(),
        )

    pbix_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.PBIX,
    )

    if not pbix_path or not os.path.exists(pbix_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="FILE_NOT_FOUND",
                message="Power BI file not available",
                details={"conversion_id": conversion_id, "file_type": "pbix"},
                can_retry=False,
            ).model_dump(),
        )

    filename = f"{job.report_name}_converted.pbix"
    file_size = os.path.getsize(pbix_path)
    logger.info(
        "User %s downloading PBIX for conversion %s",
        current_user.username,
        conversion_id,
    )

    # Log download event (non-blocking)
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONVERSION,
            action="Downloaded conversion output",
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="conversion_output",
            resource_id=conversion_id,
            details={
                "file_type": "pbix",
                "file_name": filename,
                "file_size_bytes": file_size,
                "original_report": job.report_path,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log PBIX download audit event: %s", audit_error)

    return FileResponse(
        path=pbix_path,
        media_type="application/octet-stream",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{conversion_id}/download/sql",
    summary="Download combined SQL file",
    description="Download the combined Snowflake SQL scripts file.",
    responses={
        404: {"description": "File not found"},
        400: {"description": "Conversion incomplete"},
    },
)
async def download_sql(
    conversion_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download the combined SQL file for a completed conversion."""
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    if job.status != ConversionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="CONVERSION_INCOMPLETE",
                message="Conversion incomplete - no files available",
                details={"status": job.status},
                can_retry=True,
            ).model_dump(),
        )

    sql_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.SQL,
    )

    if not sql_path or not os.path.exists(sql_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="FILE_NOT_FOUND",
                message="SQL file not available",
                details={"conversion_id": conversion_id, "file_type": "sql"},
                can_retry=False,
            ).model_dump(),
        )

    filename = f"{job.report_name}_snowflake_scripts.sql"
    file_size = os.path.getsize(sql_path)
    logger.info(
        "User %s downloading SQL for conversion %s",
        current_user.username,
        conversion_id,
    )

    # Log download event (non-blocking)
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONVERSION,
            action="Downloaded conversion output",
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="conversion_output",
            resource_id=conversion_id,
            details={
                "file_type": "sql",
                "file_name": filename,
                "file_size_bytes": file_size,
                "original_report": job.report_path,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log SQL download audit event: %s", audit_error)

    return FileResponse(
        path=sql_path,
        media_type="text/plain",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{conversion_id}/download/sql-zip",
    summary="Download SQL scripts ZIP",
    description="Download all SQL scripts as a ZIP bundle.",
    responses={
        404: {"description": "Files not found"},
        400: {"description": "Conversion incomplete"},
    },
)
async def download_sql_zip(
    conversion_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Download all SQL scripts as a ZIP file."""
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    if job.status != ConversionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="CONVERSION_INCOMPLETE",
                message="Conversion incomplete - no files available",
                details={"status": job.status},
                can_retry=True,
            ).model_dump(),
        )

    sql_files = [f for f in (job.output_files or []) if f.endswith(".sql")]
    if not sql_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="FILE_NOT_FOUND",
                message="No SQL files available",
                details={"conversion_id": conversion_id, "file_type": "sql-zip"},
                can_retry=False,
            ).model_dump(),
        )

    # Create ZIP file in memory
    zip_buffer = _create_sql_zip(
        job.output_directory,
        job.output_files,
        job.report_name,
    )

    filename = f"{job.report_name}_scripts.zip"
    # Calculate zip size
    zip_size = zip_buffer.getbuffer().nbytes

    logger.info(
        "User %s downloading SQL ZIP for conversion %s",
        current_user.username,
        conversion_id,
    )

    # Log download event (non-blocking)
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONVERSION,
            action="Downloaded conversion output",
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="conversion_output",
            resource_id=conversion_id,
            details={
                "file_type": "sql-zip",
                "file_name": filename,
                "file_size_bytes": zip_size,
                "sql_file_count": len(sql_files),
                "original_report": job.report_path,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log SQL ZIP download audit event: %s", audit_error)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{conversion_id}/download/analysis",
    summary="Download analysis JSON",
    description="Download the analysis/metadata JSON file.",
    responses={
        404: {"description": "File not found"},
        400: {"description": "Conversion incomplete"},
    },
)
async def download_analysis(
    conversion_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download the analysis metadata JSON file."""
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    if job.status != ConversionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="CONVERSION_INCOMPLETE",
                message="Conversion incomplete - no files available",
                details={"status": job.status},
                can_retry=True,
            ).model_dump(),
        )

    analysis_path = _find_file_by_type(
        job.output_directory,
        job.output_files,
        DownloadFileType.ANALYSIS,
    )

    if not analysis_path or not os.path.exists(analysis_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="FILE_NOT_FOUND",
                message="Analysis file not available",
                details={"conversion_id": conversion_id, "file_type": "analysis"},
                can_retry=False,
            ).model_dump(),
        )

    filename = f"{job.report_name}_analysis.json"
    file_size = os.path.getsize(analysis_path)
    logger.info(
        "User %s downloading analysis for conversion %s",
        current_user.username,
        conversion_id,
    )

    # Log download event (non-blocking)
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONVERSION,
            action="Downloaded conversion output",
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="conversion_output",
            resource_id=conversion_id,
            details={
                "file_type": "analysis",
                "file_name": filename,
                "file_size_bytes": file_size,
                "original_report": job.report_path,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log analysis download audit event: %s", audit_error)

    return FileResponse(
        path=analysis_path,
        media_type="application/json",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _build_conversion_summary(
    job,
    analysis,
    output_files_info: list,
) -> ConversionSummaryResponse:
    """Build a conversion summary from job and analysis data.

    Args:
        job: ConversionJob instance
        analysis: Analysis instance
        output_files_info: List of file info dicts

    Returns:
        ConversionSummaryResponse with aggregated data
    """
    import json

    # Parse analysis features
    features = analysis.features
    if isinstance(features, str):
        features = json.loads(features)

    # Initialize counters
    datasets_total = 0
    datasets_converted = 0
    visuals_total = 0
    visuals_tables = 0
    visuals_charts = 0
    visuals_matrices = 0
    visuals_textboxes = 0
    visuals_placeholders = 0
    expressions_total = 0
    expressions_auto = 0
    expressions_manual = 0
    sp_total = 0
    sp_auto = 0
    sp_partial = 0
    sp_manual = 0

    attention_items = []

    # Process datasets
    datasets = features.get("datasets", [])
    datasets_total = len(datasets)
    datasets_converted = len(datasets)  # All datasets get SQL generated

    # Process stored procedures (check classification from output or features)
    for ds in datasets:
        if ds.get("stored_procedure_name") or ds.get("query_type") == "stored_procedure":
            sp_total += 1
            classification = ds.get("sp_classification", "COMPLEX")
            if classification == "SIMPLE":
                sp_auto += 1
            elif classification == "MODERATE":
                sp_partial += 1
            else:
                sp_manual += 1
                attention_items.append(AttentionItem(
                    type="stored_procedure",
                    name=ds.get("stored_procedure_name") or ds.get("name", "Unknown SP"),
                    reason="Complex SP requiring manual conversion",
                ))

    # Process visuals
    visuals = features.get("visuals", [])
    visuals_total = len(visuals)
    for visual in visuals:
        visual_type = visual.get("type", "").lower()
        if "table" in visual_type:
            visuals_tables += 1
        elif "matrix" in visual_type:
            visuals_matrices += 1
        elif "chart" in visual_type or "bar" in visual_type or "line" in visual_type or "pie" in visual_type:
            visuals_charts += 1
        elif "text" in visual_type:
            visuals_textboxes += 1
        elif "map" in visual_type or "gauge" in visual_type or "subreport" in visual_type:
            visuals_placeholders += 1
            attention_items.append(AttentionItem(
                type="visual",
                name=visual.get("name", "Unnamed visual"),
                reason=f"{visual_type.title()} visuals require manual conversion",
                visual_type=visual_type,
            ))
        else:
            visuals_placeholders += 1

    # Process expressions
    expressions = features.get("expressions", [])
    expressions_total = len(expressions)
    for expr in expressions:
        complexity = expr.get("complexity", "unknown")
        if complexity in ["simple", "low"]:
            expressions_auto += 1
        else:
            expressions_manual += 1

    if expressions_manual == 0:
        expressions_auto = expressions_total

    # Get TODO count from analysis todos
    todos = features.get("todos", [])
    todo_count = len(todos) if todos else len(attention_items)

    # Determine overall status
    if not attention_items:
        summary_status = SummaryStatus.SUCCESS
    elif len(attention_items) < 5:
        summary_status = SummaryStatus.PARTIAL
    else:
        summary_status = SummaryStatus.PARTIAL

    if job.status == ConversionStatus.FAILED.value:
        summary_status = SummaryStatus.FAILED

    # Build file list
    files = []
    for f_info in output_files_info:
        files.append(SummaryFile(
            type=f_info.get("type", "unknown"),
            name=f_info.get("name", ""),
            size=f_info.get("size", 0),
            size_display=_format_file_size(f_info.get("size", 0)),
        ))

    return ConversionSummaryResponse(
        conversion_id=job.job_id,
        analysis_id=analysis.id,
        report=ReportInfo(
            name=job.report_name,
            path=job.report_path,
        ),
        conversion_timestamp=job.completed_at or job.created_at,
        duration_ms=job.duration_ms,
        status=summary_status,
        snowflake_configured=job.snowflake_configured or False,
        converted=ConvertedSummary(
            datasets=DatasetSummary(
                total=datasets_total,
                converted_to_sql=datasets_converted,
            ),
            visuals=VisualSummary(
                total=visuals_total,
                tables=visuals_tables,
                charts=visuals_charts,
                matrices=visuals_matrices,
                textboxes=visuals_textboxes,
                placeholders=visuals_placeholders,
            ),
            expressions=ExpressionSummary(
                total=expressions_total,
                auto_converted=expressions_auto,
                manual_required=expressions_manual,
            ),
            stored_procedures=StoredProcedureSummary(
                total=sp_total,
                auto_rewritten=sp_auto,
                partial_rewrite=sp_partial,
                manual_required=sp_manual,
            ),
        ),
        attention_required=attention_items,
        files=files,
        todo_count=todo_count,
    )


@router.get(
    "/{conversion_id}/summary",
    response_model=ConversionSummaryResponse,
    summary="Get conversion summary",
    description="Get a comprehensive summary of conversion results including what was converted and what needs attention.",
    responses={
        404: {"description": "Conversion not found"},
    },
)
async def get_conversion_summary(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversionSummaryResponse:
    """Get a comprehensive summary of a conversion.

    Returns statistics about what was converted, what needs attention,
    and information about generated files.
    """
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message="Conversion job not found",
                can_retry=False,
            ).model_dump(),
        )

    # Get analysis data
    analysis = db.query(Analysis).filter(Analysis.id == job.analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="ANALYSIS_NOT_FOUND",
                message="Analysis data not found",
                can_retry=False,
            ).model_dump(),
        )

    # Get output files info
    output_files_info = []
    if job.output_files and job.output_directory:
        # PBIX file
        pbix_path = _find_file_by_type(
            job.output_directory,
            job.output_files,
            DownloadFileType.PBIX,
        )
        if pbix_path and os.path.exists(pbix_path):
            output_files_info.append({
                "type": "pbix",
                "name": f"{job.report_name}_converted.pbix",
                "size": os.path.getsize(pbix_path),
            })

        # SQL file
        sql_path = _find_file_by_type(
            job.output_directory,
            job.output_files,
            DownloadFileType.SQL,
        )
        if sql_path and os.path.exists(sql_path):
            output_files_info.append({
                "type": "sql",
                "name": f"{job.report_name}_snowflake_scripts.sql",
                "size": os.path.getsize(sql_path),
            })

        # SQL ZIP
        sql_files = [f for f in job.output_files if f.endswith(".sql")]
        if sql_files:
            total_size = sum(
                os.path.getsize(f) for f in sql_files if os.path.exists(f)
            )
            output_files_info.append({
                "type": "sql-zip",
                "name": f"{job.report_name}_scripts.zip",
                "size": total_size,
            })

    logger.info(
        "User %s viewing summary for conversion %s",
        current_user.username,
        conversion_id,
    )

    return _build_conversion_summary(job, analysis, output_files_info)


# ============================================
# Uncertain Conversion Verification Endpoints
# ============================================


@router.post(
    "/{conversion_id}/rewrites/{rewrite_id}/verify",
    response_model=VerificationResult,
    summary="Verify or reject an uncertain conversion",
)
async def verify_conversion(
    conversion_id: str,
    rewrite_id: str,
    request: VerificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> VerificationResult:
    """Verify or reject an uncertain AI conversion.

    This endpoint allows users to mark an uncertain conversion as
    "verified" (accepting it for use) or "rejected" (excluding it from output).

    Args:
        conversion_id: ID of the conversion job
        rewrite_id: ID of the specific AI rewrite to verify
        request: VerificationRequest with action and optional notes
        current_user: Current authenticated user
        db: Database session

    Returns:
        VerificationResult with the outcome
    """
    # Verify conversion exists
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message=f"Conversion {conversion_id} not found",
                can_retry=False,
            ).model_dump(),
        )

    # Get flagging service
    flagging_service = get_flagging_service()

    # Perform verification
    # In a full implementation, we would look up the actual rewrite record
    # For now, we'll use mock data
    result = flagging_service.verify_conversion(
        rewrite_id=rewrite_id,
        sp_name="sp_Unknown",  # Would be looked up from database
        confidence_level=AIConfidenceLevel.MEDIUM,  # Would be from record
        request=request,
        user_id=str(current_user.id) if current_user.id else None,
        user_email=current_user.email,
    )

    logger.info(
        "User %s %s conversion rewrite %s in conversion %s",
        current_user.username,
        request.action.value,
        rewrite_id,
        conversion_id,
    )

    return result


@router.get(
    "/{conversion_id}/uncertain",
    response_model=UncertainConversionsSummary,
    summary="Get uncertain conversions summary",
)
async def get_uncertain_conversions_summary(
    conversion_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UncertainConversionsSummary:
    """Get summary of uncertain conversions for a conversion job.

    Returns counts of uncertain, verified, and rejected conversions.

    Args:
        conversion_id: ID of the conversion job
        current_user: Current authenticated user
        db: Database session

    Returns:
        UncertainConversionsSummary with counts
    """
    # Verify conversion exists
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message=f"Conversion {conversion_id} not found",
                can_retry=False,
            ).model_dump(),
        )

    # In a full implementation, we would query the database for actual counts
    # For now, return mock data
    return UncertainConversionsSummary(
        total_ai_rewrites=0,
        uncertain_count=0,
        high_confidence_count=0,
        medium_confidence_count=0,
        low_confidence_count=0,
        pending_review_count=0,
        verified_count=0,
        rejected_count=0,
    )


@router.get(
    "/{conversion_id}/rewrites/{rewrite_id}/status",
    response_model=dict,
    summary="Get verification status for a rewrite",
)
async def get_rewrite_verification_status(
    conversion_id: str,
    rewrite_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get the current verification status of a rewrite.

    Args:
        conversion_id: ID of the conversion job
        rewrite_id: ID of the rewrite
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with status information
    """
    # Verify conversion exists
    job = get_conversion_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="CONVERSION_NOT_FOUND",
                message=f"Conversion {conversion_id} not found",
                can_retry=False,
            ).model_dump(),
        )

    # Get flagging service
    flagging_service = get_flagging_service()
    status_value = flagging_service.get_verification_status(rewrite_id)

    return {
        "rewrite_id": rewrite_id,
        "verification_status": status_value.value,
    }

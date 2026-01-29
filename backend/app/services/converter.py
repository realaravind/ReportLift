"""Conversion service for orchestrating SSRS to Power BI conversion."""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.audit_log import EventType, AuditStatus
from app.models.conversion import ConversionJob, ConversionStatus
from app.schemas.conversion import (
    ConversionStep,
    ConversionOutputFile,
    SnowflakeWarning,
)
from app.services.audit_service import get_audit_service
from app.services.connection_config_service import get_connection_config

logger = logging.getLogger(__name__)

# Storage configuration
CONVERSION_STORAGE_PATH = os.environ.get(
    "CONVERSION_STORAGE_PATH",
    "/tmp/reportlift/conversions",
)


class ConversionError(Exception):
    """Exception raised during conversion."""

    def __init__(
        self,
        message: str,
        code: str = "CONVERSION_ERROR",
        details: dict | None = None,
        can_retry: bool = True,
    ):
        self.message = message
        self.code = code
        self.details = details
        self.can_retry = can_retry
        super().__init__(self.message)


def check_snowflake_configuration(db: Session) -> SnowflakeWarning:
    """Check if Snowflake is configured and return warning if not.

    Args:
        db: Database session

    Returns:
        SnowflakeWarning with configuration status
    """
    try:
        config = get_connection_config(db, "snowflake", decrypt=False)
        if config and config.get("account"):
            return SnowflakeWarning(
                is_configured=True,
                warning_message=None,
                can_proceed=True,
                placeholder_schema=config.get("schema", "PUBLIC"),
            )
    except Exception as e:
        logger.warning("Error checking Snowflake config: %s", e)

    return SnowflakeWarning(
        is_configured=False,
        warning_message="Snowflake not configured - SQL scripts will use placeholder schema",
        can_proceed=True,
        placeholder_schema="PLACEHOLDER_SCHEMA",
    )


def create_conversion_job(
    db: Session,
    analysis_id: int,
    user_id: int | None = None,
) -> ConversionJob:
    """Create a new conversion job.

    Args:
        db: Database session
        analysis_id: ID of the analysis to convert
        user_id: ID of the user initiating conversion

    Returns:
        Created ConversionJob

    Raises:
        ConversionError: If analysis not found or already converting
    """
    # Verify analysis exists
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ConversionError(
            message=f"Analysis {analysis_id} not found",
            code="ANALYSIS_NOT_FOUND",
            can_retry=False,
        )

    # Check if there's already a running conversion for this analysis
    existing = (
        db.query(ConversionJob)
        .filter(
            ConversionJob.analysis_id == analysis_id,
            ConversionJob.status.in_([
                ConversionStatus.PENDING.value,
                ConversionStatus.IN_PROGRESS.value,
            ]),
        )
        .first()
    )
    if existing:
        raise ConversionError(
            message="A conversion is already in progress for this analysis",
            code="CONVERSION_IN_PROGRESS",
            details={"existing_job_id": existing.job_id},
            can_retry=False,
        )

    # Check Snowflake configuration
    snowflake_warning = check_snowflake_configuration(db)

    # Create conversion job
    job = ConversionJob(
        job_id=str(uuid.uuid4()),
        analysis_id=analysis_id,
        report_path=analysis.report_path,
        report_name=analysis.report_name,
        status=ConversionStatus.PENDING.value,
        total_steps=6,
        snowflake_configured=snowflake_warning.is_configured,
        snowflake_schema_used=snowflake_warning.placeholder_schema,
        created_by_id=user_id,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(
        "Created conversion job %s for analysis %s",
        job.job_id,
        analysis_id,
    )

    return job


def get_conversion_job(db: Session, job_id: str) -> ConversionJob | None:
    """Get a conversion job by ID.

    Args:
        db: Database session
        job_id: Job UUID

    Returns:
        ConversionJob or None
    """
    return (
        db.query(ConversionJob)
        .filter(ConversionJob.job_id == job_id)
        .first()
    )


def get_conversion_by_analysis(
    db: Session,
    analysis_id: int,
) -> ConversionJob | None:
    """Get the latest conversion job for an analysis.

    Args:
        db: Database session
        analysis_id: Analysis ID

    Returns:
        Latest ConversionJob or None
    """
    return (
        db.query(ConversionJob)
        .filter(ConversionJob.analysis_id == analysis_id)
        .order_by(ConversionJob.created_at.desc())
        .first()
    )


def cancel_conversion(db: Session, job_id: str) -> ConversionJob | None:
    """Cancel a conversion job.

    Args:
        db: Database session
        job_id: Job UUID

    Returns:
        Updated ConversionJob or None if not found
    """
    job = get_conversion_job(db, job_id)
    if not job:
        return None

    if job.is_complete:
        raise ConversionError(
            message="Cannot cancel a completed conversion",
            code="ALREADY_COMPLETE",
            can_retry=False,
        )

    job.cancel()
    db.commit()
    db.refresh(job)

    # Clean up any partial output files
    if job.output_directory:
        cleanup_output_directory(job.output_directory)

    logger.info("Cancelled conversion job %s", job_id)
    return job


def cleanup_output_directory(output_dir: str) -> None:
    """Clean up output directory on failure or cancellation.

    Args:
        output_dir: Path to output directory
    """
    try:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            logger.info("Cleaned up output directory: %s", output_dir)
    except Exception as e:
        logger.error("Failed to cleanup output directory %s: %s", output_dir, e)


def run_conversion(db: Session, job_id: str) -> None:
    """Execute the conversion process.

    This is the main conversion orchestration function that:
    1. Validates analysis data
    2. Generates SQL scripts
    3. Rewrites stored procedures
    4. Builds Power BI report
    5. Applies branding
    6. Finalizes outputs

    Args:
        db: Database session
        job_id: Job UUID to process

    Note:
        This function is designed to be called in a background task.
        It handles its own error handling and cleanup.
    """
    job = get_conversion_job(db, job_id)
    if not job:
        logger.error("Conversion job not found: %s", job_id)
        return

    if job.status != ConversionStatus.PENDING.value:
        logger.warning("Job %s not in pending state: %s", job_id, job.status)
        return

    # Start the job
    job.start()
    db.commit()

    # Create output directory
    output_dir = os.path.join(CONVERSION_STORAGE_PATH, job_id)
    os.makedirs(output_dir, exist_ok=True)
    job.output_directory = output_dir
    db.commit()

    output_files: list[str] = []

    try:
        # Step 1: Validate analysis data
        _update_step(db, job, ConversionStep.VALIDATING.value, 1)
        _validate_analysis(db, job.analysis_id)

        # Check if cancelled
        db.refresh(job)
        if job.status == ConversionStatus.CANCELLED.value:
            cleanup_output_directory(output_dir)
            return

        # Step 2: Generate SQL scripts
        _update_step(db, job, ConversionStep.GENERATING_SQL.value, 2)
        sql_files = _generate_sql_scripts(db, job, output_dir)
        output_files.extend(sql_files)

        # Check if cancelled
        db.refresh(job)
        if job.status == ConversionStatus.CANCELLED.value:
            cleanup_output_directory(output_dir)
            return

        # Step 3: Rewrite stored procedures
        _update_step(db, job, ConversionStep.REWRITING_SP.value, 3)
        sp_files = _rewrite_stored_procedures(db, job, output_dir)
        output_files.extend(sp_files)

        # Check if cancelled
        db.refresh(job)
        if job.status == ConversionStatus.CANCELLED.value:
            cleanup_output_directory(output_dir)
            return

        # Step 4: Build Power BI report
        _update_step(db, job, ConversionStep.BUILDING_PBIX.value, 4)
        pbix_files = _build_power_bi_report(db, job, output_dir)
        output_files.extend(pbix_files)

        # Check if cancelled
        db.refresh(job)
        if job.status == ConversionStatus.CANCELLED.value:
            cleanup_output_directory(output_dir)
            return

        # Step 5: Apply branding
        _update_step(db, job, ConversionStep.APPLYING_BRANDING.value, 5)
        _apply_branding(db, job, output_dir)

        # Check if cancelled
        db.refresh(job)
        if job.status == ConversionStatus.CANCELLED.value:
            cleanup_output_directory(output_dir)
            return

        # Step 6: Finalize outputs
        _update_step(db, job, ConversionStep.FINALIZING.value, 6)
        metadata_file = _finalize_outputs(db, job, output_dir, output_files)
        output_files.append(metadata_file)

        # Mark as complete
        job.complete(output_dir, output_files)
        db.commit()

        logger.info(
            "Conversion completed successfully: %s (files: %d)",
            job_id,
            len(output_files),
        )

        # Log successful conversion to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            # Determine conversion method
            ai_used = any("ai_" in f.lower() for f in output_files) if output_files else False
            conversion_method = "mixed" if ai_used else "rule-based"

            # Calculate duration
            duration_ms = job.duration_ms or 0

            audit_service.log_event_sync(
                db=db,
                event_type=EventType.CONVERSION,
                action=f"Report converted: {job.report_name}",
                status=AuditStatus.SUCCESS,
                user_id=job.created_by_id,
                resource_type="report",
                resource_id=job.report_path,
                details={
                    "report_name": job.report_name,
                    "output_files": [os.path.basename(f) for f in output_files],
                    "output_file_count": len(output_files),
                    "conversion_method": conversion_method,
                    "ai_used": ai_used,
                    "snowflake_configured": job.snowflake_configured,
                    "snowflake_schema": job.snowflake_schema_used,
                    "conversion_duration_ms": duration_ms,
                    "conversion_id": job.job_id,
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log conversion success audit event: %s", audit_error)

    except ConversionError as e:
        logger.error("Conversion failed: %s - %s", job_id, e.message)
        job.fail(e.message, e.details)
        db.commit()
        cleanup_output_directory(output_dir)

        # Log failed conversion to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.CONVERSION,
                action=f"Report conversion failed: {job.report_name}",
                status=AuditStatus.FAILURE,
                user_id=job.created_by_id,
                resource_type="report",
                resource_id=job.report_path,
                details={
                    "report_name": job.report_name,
                    "error_code": e.code,
                    "error_message": e.message,
                    "stage_failed": job.current_step,
                    "partial_outputs": [os.path.basename(f) for f in output_files] if output_files else [],
                    "conversion_id": job.job_id,
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log conversion failure audit event: %s", audit_error)

    except Exception as e:
        logger.exception("Unexpected error during conversion: %s", job_id)
        job.fail(str(e), {"type": type(e).__name__})
        db.commit()
        cleanup_output_directory(output_dir)

        # Log unexpected failure to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.CONVERSION,
                action=f"Report conversion failed: {job.report_name}",
                status=AuditStatus.FAILURE,
                user_id=job.created_by_id,
                resource_type="report",
                resource_id=job.report_path,
                details={
                    "report_name": job.report_name,
                    "error_code": "UNEXPECTED_ERROR",
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "stage_failed": job.current_step,
                    "partial_outputs": [os.path.basename(f) for f in output_files] if output_files else [],
                    "conversion_id": job.job_id,
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log conversion error audit event: %s", audit_error)


def _update_step(db: Session, job: ConversionJob, step: str, completed: int) -> None:
    """Update job progress step."""
    job.update_progress(step, completed)
    db.commit()


def _validate_analysis(db: Session, analysis_id: int) -> None:
    """Validate that analysis data is sufficient for conversion.

    Args:
        db: Database session
        analysis_id: Analysis ID to validate

    Raises:
        ConversionError: If validation fails
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ConversionError(
            message="Analysis not found",
            code="ANALYSIS_NOT_FOUND",
            can_retry=False,
        )

    if not analysis.features:
        raise ConversionError(
            message="Analysis has no feature data",
            code="NO_FEATURES",
            can_retry=False,
        )

    if not analysis.rdl_content:
        raise ConversionError(
            message="Analysis has no RDL content",
            code="NO_RDL_CONTENT",
            can_retry=True,  # User can re-analyze
        )


def _generate_sql_scripts(
    db: Session,
    job: ConversionJob,
    output_dir: str,
) -> list[str]:
    """Generate SQL scripts for Snowflake.

    Args:
        db: Database session
        job: Conversion job
        output_dir: Output directory path

    Returns:
        List of generated SQL file paths
    """
    from app.schemas.analysis import AnalysisFeatures, DatasetFeature
    from app.services.sql_generator import generate_sql_scripts

    # Get analysis features
    analysis = db.query(Analysis).filter(Analysis.id == job.analysis_id).first()
    if not analysis or not analysis.features:
        logger.warning("No analysis features found for job %s", job.job_id)
        return []

    # Parse features JSON to get datasets
    features_data = analysis.features
    if isinstance(features_data, str):
        import json
        features_data = json.loads(features_data)

    # Extract datasets from features
    datasets_data = features_data.get("datasets", [])
    if not datasets_data:
        logger.info("No datasets found in analysis for job %s", job.job_id)
        return []

    # Convert to DatasetFeature objects
    datasets = [DatasetFeature(**ds) for ds in datasets_data]

    # Get Snowflake configuration
    database = "PLACEHOLDER_DATABASE"
    schema = job.snowflake_schema_used or "PLACEHOLDER_SCHEMA"
    warehouse = "PLACEHOLDER_WAREHOUSE"

    # Try to get actual Snowflake config
    try:
        config = get_connection_config(db, "snowflake", decrypt=False)
        if config:
            database = config.get("database", database)
            schema = config.get("schema", schema)
            warehouse = config.get("warehouse", warehouse)
    except Exception as e:
        logger.warning("Could not get Snowflake config: %s", e)

    # Generate SQL scripts
    result = generate_sql_scripts(
        datasets=datasets,
        report_name=job.report_name or "Unknown Report",
        output_dir=output_dir,
        database=database,
        schema=schema,
        warehouse=warehouse,
    )

    # Collect all generated file paths
    sql_dir = os.path.join(output_dir, "sql")
    file_paths = [os.path.join(sql_dir, script.filename) for script in result.scripts]

    # Add the combined file
    if result.all_scripts_path:
        file_paths.append(result.all_scripts_path)

    logger.info(
        "Generated %d SQL scripts for job %s (%d functions mapped)",
        len(file_paths),
        job.job_id,
        result.total_functions_mapped,
    )

    return file_paths


def _rewrite_stored_procedures(
    db: Session,
    job: ConversionJob,
    output_dir: str,
) -> list[str]:
    """Rewrite stored procedures for Snowflake.

    Args:
        db: Database session
        job: Conversion job
        output_dir: Output directory path

    Returns:
        List of generated SP file paths
    """
    from app.schemas.analysis import DatasetFeature, QueryType
    from app.services.sp_rewriter import rewrite_stored_procedure, SPClassification

    # Get analysis features
    analysis = db.query(Analysis).filter(Analysis.id == job.analysis_id).first()
    if not analysis or not analysis.features:
        logger.info("No analysis features found for SP rewriting")
        return []

    # Parse features JSON to get datasets
    features_data = analysis.features
    if isinstance(features_data, str):
        import json
        features_data = json.loads(features_data)

    # Extract datasets with stored procedures
    datasets_data = features_data.get("datasets", [])
    sp_datasets = [
        ds for ds in datasets_data
        if ds.get("query_type") == QueryType.STORED_PROCEDURE.value
        or ds.get("stored_procedure_name")
    ]

    if not sp_datasets:
        logger.info("No stored procedures found in analysis for job %s", job.job_id)
        return []

    # Get Snowflake configuration
    database = "PLACEHOLDER_DATABASE"
    schema = job.snowflake_schema_used or "PLACEHOLDER_SCHEMA"
    warehouse = "PLACEHOLDER_WAREHOUSE"

    try:
        config = get_connection_config(db, "snowflake", decrypt=False)
        if config:
            database = config.get("database", database)
            schema = config.get("schema", schema)
            warehouse = config.get("warehouse", warehouse)
    except Exception as e:
        logger.warning("Could not get Snowflake config for SP rewriting: %s", e)

    # Create SP output directory
    sp_dir = os.path.join(output_dir, "stored_procedures")
    os.makedirs(sp_dir, exist_ok=True)

    file_paths = []
    classification_counts = {
        SPClassification.SIMPLE: 0,
        SPClassification.MODERATE: 0,
        SPClassification.COMPLEX: 0,
    }

    for ds in sp_datasets:
        sp_name = ds.get("stored_procedure_name") or ds.get("name", "unknown_sp")

        # Get SP definition if available (from command_text or dedicated field)
        sp_definition = ds.get("sp_definition")
        sp_call = ds.get("command_text")

        # Rewrite the stored procedure
        result = rewrite_stored_procedure(
            sp_name=sp_name,
            sp_definition=sp_definition,
            sp_call=sp_call,
            database=database,
            schema=schema,
            warehouse=warehouse,
        )

        # Track classification counts
        classification_counts[result.classification] += 1

        # Generate filename
        safe_name = sp_name.lower().replace(" ", "_")
        filename = f"{safe_name}_converted.sql"
        filepath = os.path.join(sp_dir, filename)

        # Write the converted SQL (or placeholder)
        with open(filepath, "w") as f:
            if result.converted_sql:
                f.write(result.converted_sql)
            else:
                # Write a minimal placeholder if no converted SQL
                f.write(f"-- SP: {sp_name}\n")
                f.write(f"-- Classification: {result.classification.value}\n")
                f.write(f"-- Error: {result.error_message}\n")
                f.write(f"SELECT 'TODO: Convert {sp_name}' AS status;\n")

            # Add validation suggestions
            if result.validation_suggestions:
                f.write("\n\n-- Validation Recommendations:\n")
                for i, suggestion in enumerate(result.validation_suggestions, 1):
                    f.write(f"-- {i}. {suggestion}\n")

        file_paths.append(filepath)

        logger.debug(
            "Rewrote SP %s: classification=%s, confidence=%s, success=%s",
            sp_name,
            result.classification.value,
            result.confidence.value,
            result.success,
        )

    # Create summary file
    summary_path = os.path.join(sp_dir, "_sp_conversion_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Stored Procedure Conversion Summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Total SPs processed: {len(sp_datasets)}\n")
        f.write(f"  Simple (auto-converted):  {classification_counts[SPClassification.SIMPLE]}\n")
        f.write(f"  Moderate (partial):       {classification_counts[SPClassification.MODERATE]}\n")
        f.write(f"  Complex (manual needed):  {classification_counts[SPClassification.COMPLEX]}\n")
    file_paths.append(summary_path)

    logger.info(
        "Rewrote %d stored procedures for job %s (simple=%d, moderate=%d, complex=%d)",
        len(sp_datasets),
        job.job_id,
        classification_counts[SPClassification.SIMPLE],
        classification_counts[SPClassification.MODERATE],
        classification_counts[SPClassification.COMPLEX],
    )

    return file_paths


def _build_power_bi_report(
    db: Session,
    job: ConversionJob,
    output_dir: str,
) -> list[str]:
    """Build Power BI report file.

    Args:
        db: Database session
        job: Conversion job
        output_dir: Output directory path

    Returns:
        List of generated PBIX file paths
    """
    from app.services.pbix_builder import build_pbix_from_analysis

    # Get analysis features
    analysis = db.query(Analysis).filter(Analysis.id == job.analysis_id).first()
    if not analysis or not analysis.features:
        logger.warning("No analysis features found for PBIX generation")
        return []

    # Parse features JSON
    features_data = analysis.features
    if isinstance(features_data, str):
        import json
        features_data = json.loads(features_data)

    # Get branding theme if configured
    theme = None
    try:
        branding_config = get_connection_config(db, "branding", decrypt=False)
        if branding_config:
            theme = branding_config.get("theme")
    except Exception as e:
        logger.debug("No branding theme configured: %s", e)

    # Build the PBIX file
    result = build_pbix_from_analysis(
        analysis_features=features_data,
        report_name=job.report_name or "Converted Report",
        output_dir=output_dir,
        theme=theme,
    )

    if not result.success:
        logger.error("Failed to build PBIX: %s", result.error_message)
        return []

    # Log warnings
    for warning in result.warnings:
        logger.warning("PBIX build warning: %s", warning)

    logger.info(
        "Generated Power BI report: %s (pages=%d, visuals=%d, placeholders=%d)",
        result.file_path,
        result.page_count,
        result.visual_count,
        result.placeholder_count,
    )

    return [result.file_path] if result.file_path else []


def _apply_branding(
    db: Session,
    job: ConversionJob,
    output_dir: str,
) -> None:
    """Apply branding template to generated outputs.

    This is a stub that will be implemented in Story 5.5.

    Args:
        db: Database session
        job: Conversion job
        output_dir: Output directory path
    """
    # TODO: Implement in Story 5.5
    logger.info("Branding application (stub) - no branding applied")


def _finalize_outputs(
    db: Session,
    job: ConversionJob,
    output_dir: str,
    output_files: list[str],
) -> str:
    """Finalize conversion outputs and create metadata file.

    Args:
        db: Database session
        job: Conversion job
        output_dir: Output directory path
        output_files: List of generated file paths

    Returns:
        Path to metadata file
    """
    import json

    metadata = {
        "conversion_id": job.job_id,
        "report_name": job.report_name,
        "report_path": job.report_path,
        "analysis_id": job.analysis_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snowflake_configured": job.snowflake_configured,
        "snowflake_schema": job.snowflake_schema_used,
        "files": [os.path.basename(f) for f in output_files],
    }

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Created conversion metadata: %s", metadata_path)
    return metadata_path


def get_output_files(job: ConversionJob) -> list[ConversionOutputFile]:
    """Get list of output files for a completed conversion.

    Args:
        job: Completed conversion job

    Returns:
        List of ConversionOutputFile objects
    """
    if not job.output_directory or not job.output_files:
        return []

    files = []
    for filepath in job.output_files:
        if os.path.exists(filepath):
            stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            file_type = _get_file_type(filename)
            rel_path = os.path.relpath(filepath, job.output_directory)

            files.append(ConversionOutputFile(
                filename=filename,
                file_type=file_type,
                size_bytes=stat.st_size,
                path=rel_path,
            ))

    return files


def _get_file_type(filename: str) -> str:
    """Get file type from filename."""
    ext = os.path.splitext(filename)[1].lower()
    type_map = {
        ".sql": "sql",
        ".pbix": "pbix",
        ".json": "json",
        ".txt": "text",
    }
    return type_map.get(ext, "unknown")

"""Analysis Service - Handles report analysis orchestration."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisTask
from app.models.audit_log import EventType, AuditStatus
from app.schemas.analysis import AnalysisFeatures, RDLParseError
from app.schemas.classification import ClassificationResult
from app.services.audit_service import get_audit_service
from app.services.rdl_parser import parse_rdl
from app.services.scoring_engine import analyze_report as run_classification_and_scoring
from app.services.ssrs_service import fetch_report_rdl

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of a report analysis."""

    success: bool
    message: str
    analysis_id: int | None = None
    task_id: str | None = None
    classification: str | None = None
    score: int | None = None
    status: str | None = None
    features: dict | None = None
    penalties: dict | None = None
    todo_items: list | None = None
    error_code: str | None = None
    suggestions: list[str] | None = None


def get_latest_analysis(
    db: Session,
    report_path: str,
) -> Analysis | None:
    """Get the most recent analysis for a report.

    Args:
        db: Database session
        report_path: Path to the report

    Returns:
        Analysis object if found, None otherwise
    """
    return (
        db.query(Analysis)
        .filter(Analysis.report_path == report_path)
        .order_by(Analysis.analyzed_at.desc())
        .first()
    )


def get_analysis_by_id(db: Session, analysis_id: int) -> Analysis | None:
    """Get an analysis by its ID.

    Args:
        db: Database session
        analysis_id: ID of the analysis

    Returns:
        Analysis object if found, None otherwise
    """
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


def get_task_by_id(db: Session, task_id: str) -> AnalysisTask | None:
    """Get an analysis task by its task ID.

    Args:
        db: Database session
        task_id: UUID string of the task

    Returns:
        AnalysisTask object if found, None otherwise
    """
    return db.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()


def create_analysis_task(
    db: Session,
    report_path: str,
    user_id: int | None = None,
) -> AnalysisTask:
    """Create a new analysis task.

    Args:
        db: Database session
        report_path: Path to the report
        user_id: ID of the user who triggered the analysis

    Returns:
        Created AnalysisTask object
    """
    task = AnalysisTask(
        task_id=str(uuid.uuid4()),
        status="pending",
        progress=0,
        current_step="Initializing",
        report_path=report_path,
        created_by_id=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task_progress(
    db: Session,
    task: AnalysisTask,
    status: str,
    progress: int,
    current_step: str,
    error_message: str | None = None,
) -> None:
    """Update an analysis task's progress.

    Args:
        db: Database session
        task: The task to update
        status: New status
        progress: Progress percentage (0-100)
        current_step: Description of current step
        error_message: Optional error message
    """
    task.status = status
    task.progress = progress
    task.current_step = current_step
    task.error_message = error_message

    if status == "running" and not task.started_at:
        task.started_at = datetime.now(timezone.utc)
    elif status in ("completed", "failed", "cancelled"):
        task.completed_at = datetime.now(timezone.utc)

    db.commit()


def _parse_rdl_with_new_parser(rdl_content: str) -> tuple[dict[str, Any], AnalysisFeatures | None]:
    """Parse RDL using the comprehensive parser.

    Args:
        rdl_content: The RDL XML content

    Returns:
        Tuple of (legacy_features_dict, AnalysisFeatures or None on error)
    """
    try:
        features = parse_rdl(rdl_content)
        # Convert to legacy dict for backward compatibility with scoring
        legacy_dict = features.to_legacy_dict()

        # Add additional fields from the comprehensive parser
        legacy_dict["rdl_version"] = features.rdl_version
        legacy_dict["running_values"] = features.running_value_count
        legacy_dict["lookups"] = sum(
            1 for e in features.expressions
            if "lookup" in e.category.value.lower()
        )
        legacy_dict["maps"] = features.map_count
        legacy_dict["gauges"] = features.gauge_count
        legacy_dict["custom_code_functions"] = features.custom_code_function_count

        return legacy_dict, features

    except RDLParseError as e:
        logger.warning("RDL parse error: %s", str(e))
        # Return empty features on parse error
        return _get_empty_features(), None
    except Exception as e:
        logger.warning("Error extracting RDL features: %s", str(e))
        return _get_empty_features(), None


def _get_empty_features() -> dict[str, Any]:
    """Return empty features dictionary."""
    return {
        "data_sources": 0,
        "datasets": 0,
        "parameters": 0,
        "tables": 0,
        "matrices": 0,
        "charts": 0,
        "subreports": 0,
        "custom_code": False,
        "expressions": 0,
        "stored_procedures": 0,
        "has_grouping": False,
        "has_sorting": False,
        "has_filters": False,
        "page_breaks": 0,
        "images": 0,
        "rectangles": 0,
        "textboxes": 0,
        "lines": 0,
        "running_values": 0,
        "lookups": 0,
        "maps": 0,
        "gauges": 0,
        "custom_code_functions": 0,
    }


def _calculate_score(features: dict[str, Any]) -> tuple[int, str, dict]:
    """Calculate conversion readiness score from features.

    This is a simplified scoring for Story 4.1. Full scoring is in Story 4.3.

    Args:
        features: Extracted report features

    Returns:
        Tuple of (score, status, penalties)
    """
    score = 100
    penalties = {}

    # Penalty for custom code (major complexity)
    if features.get("custom_code"):
        penalty = 25
        score -= penalty
        penalties["custom_code"] = {
            "penalty": penalty,
            "reason": "Report contains custom VB.NET code that requires manual conversion",
        }

    # Penalty for stored procedures
    sp_count = features.get("stored_procedures", 0)
    if sp_count > 0:
        penalty = min(20, sp_count * 5)
        score -= penalty
        penalties["stored_procedures"] = {
            "penalty": penalty,
            "count": sp_count,
            "reason": f"Contains {sp_count} stored procedure call(s) requiring Snowflake conversion",
        }

    # Penalty for subreports
    subreport_count = features.get("subreports", 0)
    if subreport_count > 0:
        penalty = min(15, subreport_count * 5)
        score -= penalty
        penalties["subreports"] = {
            "penalty": penalty,
            "count": subreport_count,
            "reason": f"Contains {subreport_count} subreport(s) requiring separate handling",
        }

    # Penalty for complex expressions
    expr_count = features.get("expressions", 0)
    if expr_count > 50:
        penalty = min(15, (expr_count - 50) // 10)
        score -= penalty
        penalties["expressions"] = {
            "penalty": penalty,
            "count": expr_count,
            "reason": f"High expression count ({expr_count}) may require manual review",
        }

    # Penalty for charts (Power BI conversion required)
    chart_count = features.get("charts", 0)
    if chart_count > 0:
        penalty = min(10, chart_count * 2)
        score -= penalty
        penalties["charts"] = {
            "penalty": penalty,
            "count": chart_count,
            "reason": f"Contains {chart_count} chart(s) requiring Power BI visual recreation",
        }

    # Penalty for matrices (complex layout)
    matrix_count = features.get("matrices", 0)
    if matrix_count > 0:
        penalty = min(10, matrix_count * 3)
        score -= penalty
        penalties["matrices"] = {
            "penalty": penalty,
            "count": matrix_count,
            "reason": f"Contains {matrix_count} matrix element(s) with complex layout",
        }

    # Penalty for running values (complex calculation)
    running_value_count = features.get("running_values", 0)
    if running_value_count > 0:
        penalty = min(15, running_value_count * 5)
        score -= penalty
        penalties["running_values"] = {
            "penalty": penalty,
            "count": running_value_count,
            "reason": f"Contains {running_value_count} RunningValue expression(s) requiring DAX conversion",
        }

    # Penalty for lookups (complex data relationships)
    lookup_count = features.get("lookups", 0)
    if lookup_count > 0:
        penalty = min(10, lookup_count * 3)
        score -= penalty
        penalties["lookups"] = {
            "penalty": penalty,
            "count": lookup_count,
            "reason": f"Contains {lookup_count} Lookup expression(s) requiring relationship modeling",
        }

    # Penalty for maps (unsupported visual)
    map_count = features.get("maps", 0)
    if map_count > 0:
        penalty = min(15, map_count * 10)
        score -= penalty
        penalties["maps"] = {
            "penalty": penalty,
            "count": map_count,
            "reason": f"Contains {map_count} Map visual(s) requiring manual recreation",
        }

    # Penalty for gauges (limited Power BI support)
    gauge_count = features.get("gauges", 0)
    if gauge_count > 0:
        penalty = min(10, gauge_count * 3)
        score -= penalty
        penalties["gauges"] = {
            "penalty": penalty,
            "count": gauge_count,
            "reason": f"Contains {gauge_count} Gauge visual(s) requiring adaptation",
        }

    # Ensure score doesn't go below 0
    score = max(0, score)

    # Determine status based on score
    if score >= 70:
        status = "green"
    elif score >= 40:
        status = "yellow"
    else:
        status = "red"

    return score, status, penalties


def _classify_report(features: dict[str, Any]) -> str:
    """Classify report type based on features.

    Args:
        features: Extracted report features

    Returns:
        Classification string
    """
    has_charts = features.get("charts", 0) > 0
    has_tables = features.get("tables", 0) > 0
    has_matrices = features.get("matrices", 0) > 0
    has_grouping = features.get("has_grouping", False)
    has_custom_code = features.get("custom_code", False)
    has_subreports = features.get("subreports", 0) > 0

    # Complex: has custom code or many subreports
    if has_custom_code or features.get("subreports", 0) > 2:
        return "Complex"

    # Analytical: has charts
    if has_charts:
        if has_tables or has_matrices:
            return "Mixed"
        return "Analytical"

    # Tabular: has tables/matrices with grouping
    if has_tables or has_matrices:
        if has_grouping:
            return "Tabular"
        return "Simple Tabular"

    return "Simple"


def _generate_todo_items(
    features: dict[str, Any],
    penalties: dict[str, Any],
) -> list[dict]:
    """Generate todo items for conversion based on analysis.

    Args:
        features: Extracted report features
        penalties: Calculated penalties

    Returns:
        List of todo items
    """
    todos = []

    # Todo for custom code
    if features.get("custom_code"):
        todos.append({
            "category": "Custom Code",
            "priority": "high",
            "title": "Convert custom VB.NET code",
            "description": "The report contains custom code that needs to be reviewed and converted to DAX or Power Query.",
            "estimated_effort": "high",
        })

    # Todo for stored procedures
    if features.get("stored_procedures", 0) > 0:
        todos.append({
            "category": "Data Source",
            "priority": "high",
            "title": "Convert stored procedures to Snowflake",
            "description": f"Convert {features['stored_procedures']} stored procedure(s) to Snowflake SQL.",
            "estimated_effort": "medium" if features["stored_procedures"] < 3 else "high",
        })

    # Todo for subreports
    if features.get("subreports", 0) > 0:
        todos.append({
            "category": "Report Structure",
            "priority": "medium",
            "title": "Handle subreports",
            "description": f"Review and convert {features['subreports']} subreport(s). Consider consolidating into main report.",
            "estimated_effort": "medium",
        })

    # Todo for charts
    if features.get("charts", 0) > 0:
        todos.append({
            "category": "Visualizations",
            "priority": "medium",
            "title": "Recreate charts in Power BI",
            "description": f"Recreate {features['charts']} chart(s) using Power BI visualizations.",
            "estimated_effort": "low" if features["charts"] < 3 else "medium",
        })

    # Todo for parameters
    if features.get("parameters", 0) > 0:
        todos.append({
            "category": "Parameters",
            "priority": "low",
            "title": "Configure report parameters",
            "description": f"Set up {features['parameters']} parameter(s) in Power BI.",
            "estimated_effort": "low",
        })

    # Todo for data sources
    if features.get("data_sources", 0) > 0:
        todos.append({
            "category": "Data Source",
            "priority": "high",
            "title": "Configure Snowflake data connection",
            "description": "Set up Snowflake connection in Power BI with appropriate credentials.",
            "estimated_effort": "low",
        })

    # Todo for running values
    if features.get("running_values", 0) > 0:
        todos.append({
            "category": "Expressions",
            "priority": "high",
            "title": "Convert RunningValue expressions",
            "description": f"Convert {features['running_values']} RunningValue expression(s) to DAX running totals.",
            "estimated_effort": "medium",
        })

    # Todo for lookups
    if features.get("lookups", 0) > 0:
        todos.append({
            "category": "Expressions",
            "priority": "medium",
            "title": "Set up data relationships for Lookups",
            "description": f"Configure Power BI relationships to replace {features['lookups']} Lookup expression(s).",
            "estimated_effort": "medium",
        })

    # Todo for maps
    if features.get("maps", 0) > 0:
        todos.append({
            "category": "Visualizations",
            "priority": "medium",
            "title": "Recreate map visuals",
            "description": f"Recreate {features['maps']} map visual(s) using Power BI map components.",
            "estimated_effort": "high",
        })

    # Todo for gauges
    if features.get("gauges", 0) > 0:
        todos.append({
            "category": "Visualizations",
            "priority": "low",
            "title": "Convert gauge visuals",
            "description": f"Convert {features['gauges']} gauge visual(s) to Power BI KPI or gauge visuals.",
            "estimated_effort": "low",
        })

    return todos


def analyze_uploaded_rdl(
    db: Session,
    rdl_content: str,
    report_name: str,
    user_id: int | None = None,
    task: AnalysisTask | None = None,
) -> AnalysisResult:
    """Analyze an uploaded RDL file directly.

    Args:
        db: Database session
        rdl_content: The RDL XML content
        report_name: Display name of the report
        user_id: ID of the user triggering the analysis
        task: Optional AnalysisTask to update with progress

    Returns:
        AnalysisResult with analysis data or error
    """
    start_time = time.time()
    report_path = f"uploaded/{report_name}"

    try:
        # Update task progress: Parsing
        if task:
            update_task_progress(db, task, "running", 30, "Parsing report definition")

        # Parse RDL and extract features using comprehensive parser
        features, analysis_features = _parse_rdl_with_new_parser(rdl_content)

        # Log parsed features summary
        if analysis_features:
            logger.info(
                "Parsed uploaded RDL version %s: %d datasets, %d visuals, %d expressions",
                analysis_features.rdl_version,
                analysis_features.dataset_count,
                analysis_features.visual_count,
                analysis_features.expression_count,
            )

        # Update task progress: Analyzing
        if task:
            update_task_progress(db, task, "running", 60, "Analyzing report complexity")

        # Use new classification and scoring engine when features available
        classification_result: ClassificationResult | None = None
        if analysis_features:
            classification_result = run_classification_and_scoring(analysis_features)
            classification = classification_result.classification.value
            score = classification_result.score
            status = classification_result.status.value
            # Convert breakdown to dict for storage
            penalties = classification_result.breakdown.model_dump()
        else:
            # Fallback to legacy scoring
            score, status, penalties = _calculate_score(features)
            classification = _classify_report(features)

        # Update task progress: Generating recommendations
        if task:
            update_task_progress(db, task, "running", 80, "Generating conversion recommendations")

        # Generate todo items
        todo_items = _generate_todo_items(features, penalties if not classification_result else features)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Store analysis in database
        analysis = Analysis(
            report_path=report_path,
            report_name=report_name,
            report_id=None,  # No SSRS report ID for uploaded files
            classification=classification,
            score=score,
            status=status,
            features=features,
            penalties=penalties,
            todo_items=todo_items,
            rdl_content=rdl_content,
            analysis_duration_ms=duration_ms,
            created_by_id=user_id,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # Update task with completion
        if task:
            task.analysis_id = analysis.id
            update_task_progress(db, task, "completed", 100, "Analysis complete")

        logger.info(
            "Completed analysis for uploaded %s: score=%d, classification=%s, duration=%dms",
            report_name, score, classification, duration_ms
        )

        # Log successful analysis to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.ANALYSIS,
                action=f"Uploaded report analyzed: {report_name}",
                status=AuditStatus.SUCCESS,
                user_id=user_id,
                resource_type="uploaded_report",
                resource_id=report_path,
                details={
                    "report_name": report_name,
                    "score": score,
                    "classification": classification,
                    "status_color": status,
                    "stored_procedures_count": features.get("stored_procedures", 0),
                    "expressions_count": features.get("expressions", 0),
                    "analysis_duration_ms": duration_ms,
                    "analysis_id": analysis.id,
                    "source": "file_upload",
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log analysis success audit event: %s", audit_error)

        return AnalysisResult(
            success=True,
            message="Analysis completed successfully",
            analysis_id=analysis.id,
            task_id=task.task_id if task else None,
            classification=classification,
            score=score,
            status=status,
            features=features,
            penalties=penalties,
            todo_items=todo_items,
        )

    except Exception as e:
        logger.exception("Error analyzing uploaded report %s: %s", report_name, str(e))
        if task:
            update_task_progress(
                db, task, "failed", 0, "Analysis failed",
                error_message=str(e)
            )

        # Log failed analysis to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.ANALYSIS,
                action=f"Uploaded report analysis failed: {report_name}",
                status=AuditStatus.FAILURE,
                user_id=user_id,
                resource_type="uploaded_report",
                resource_id=report_path,
                details={
                    "report_name": report_name,
                    "error_code": "ANALYSIS_ERROR",
                    "error_message": str(e),
                    "source": "file_upload",
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log analysis failure audit event: %s", audit_error)

        return AnalysisResult(
            success=False,
            message=f"Analysis failed: {str(e)}",
            error_code="ANALYSIS_ERROR",
            suggestions=["Check if the RDL file is valid", "Ensure the file is a valid SSRS report definition"],
        )


def analyze_report(
    db: Session,
    report_path: str,
    report_name: str,
    ssrs_url: str,
    username: str | None,
    password: str | None,
    domain: str | None,
    user_id: int | None = None,
    task: AnalysisTask | None = None,
) -> AnalysisResult:
    """Analyze a report and store the results.

    Args:
        db: Database session
        report_path: Full path to the report in SSRS
        report_name: Display name of the report
        ssrs_url: SSRS server URL
        username: Username for SSRS authentication
        password: Password for SSRS authentication
        domain: Domain for NTLM authentication
        user_id: ID of the user triggering the analysis
        task: Optional AnalysisTask to update with progress

    Returns:
        AnalysisResult with analysis data or error
    """
    start_time = time.time()

    try:
        # Update task progress: Fetching RDL
        if task:
            update_task_progress(db, task, "running", 10, "Fetching report definition from SSRS")

        # Fetch RDL from SSRS
        rdl_result = fetch_report_rdl(
            report_server_url=ssrs_url,
            report_path=report_path,
            username=username,
            password=password,
            domain=domain,
            timeout=30,
        )

        if not rdl_result.success:
            if task:
                update_task_progress(
                    db, task, "failed", 10, "Failed to fetch RDL",
                    error_message=rdl_result.message
                )

            # Log failed RDL fetch to audit trail (non-blocking)
            try:
                audit_service = get_audit_service()
                audit_service.log_event_sync(
                    db=db,
                    event_type=EventType.ANALYSIS,
                    action=f"Report analysis failed: {report_name}",
                    status=AuditStatus.FAILURE,
                    user_id=user_id,
                    resource_type="report",
                    resource_id=report_path,
                    details={
                        "report_name": report_name,
                        "error_code": rdl_result.error_code.value if rdl_result.error_code else "RDL_FETCH_FAILED",
                        "error_message": rdl_result.message,
                        "stage_failed": "rdl_fetch",
                    },
                )
            except Exception as audit_error:
                logger.warning("Failed to log RDL fetch failure audit event: %s", audit_error)

            return AnalysisResult(
                success=False,
                message=rdl_result.message,
                error_code=rdl_result.error_code.value if rdl_result.error_code else "FETCH_ERROR",
                suggestions=rdl_result.suggestions,
            )

        # Update task progress: Parsing
        if task:
            update_task_progress(db, task, "running", 40, "Parsing report definition")

        # Parse RDL and extract features using comprehensive parser
        features, analysis_features = _parse_rdl_with_new_parser(rdl_result.rdl_content)

        # Log parsed features summary
        if analysis_features:
            logger.info(
                "Parsed RDL version %s: %d datasets, %d visuals, %d expressions",
                analysis_features.rdl_version,
                analysis_features.dataset_count,
                analysis_features.visual_count,
                analysis_features.expression_count,
            )

        # Update task progress: Analyzing
        if task:
            update_task_progress(db, task, "running", 60, "Analyzing report complexity")

        # Use new classification and scoring engine when features available
        classification_result: ClassificationResult | None = None
        if analysis_features:
            classification_result = run_classification_and_scoring(analysis_features)
            classification = classification_result.classification.value
            score = classification_result.score
            status = classification_result.status.value
            # Convert breakdown to dict for storage
            penalties = classification_result.breakdown.model_dump()
        else:
            # Fallback to legacy scoring
            score, status, penalties = _calculate_score(features)
            classification = _classify_report(features)

        # Update task progress: Generating recommendations
        if task:
            update_task_progress(db, task, "running", 80, "Generating conversion recommendations")

        # Generate todo items
        todo_items = _generate_todo_items(features, penalties if not classification_result else features)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Store analysis in database
        analysis = Analysis(
            report_path=report_path,
            report_name=report_name,
            report_id=rdl_result.report_id,
            classification=classification,
            score=score,
            status=status,
            features=features,
            penalties=penalties,
            todo_items=todo_items,
            rdl_content=rdl_result.rdl_content,
            analysis_duration_ms=duration_ms,
            created_by_id=user_id,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # Update task with completion
        if task:
            task.analysis_id = analysis.id
            update_task_progress(db, task, "completed", 100, "Analysis complete")

        logger.info(
            "Completed analysis for %s: score=%d, classification=%s, duration=%dms",
            report_path, score, classification, duration_ms
        )

        # Log successful analysis to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.ANALYSIS,
                action=f"Report analyzed: {report_name}",
                status=AuditStatus.SUCCESS,
                user_id=user_id,
                resource_type="report",
                resource_id=report_path,
                details={
                    "report_name": report_name,
                    "score": score,
                    "classification": classification,
                    "status_color": status,
                    "stored_procedures_count": features.get("stored_procedures", 0),
                    "expressions_count": features.get("expressions", 0),
                    "analysis_duration_ms": duration_ms,
                    "analysis_id": analysis.id,
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log analysis success audit event: %s", audit_error)

        return AnalysisResult(
            success=True,
            message="Analysis completed successfully",
            analysis_id=analysis.id,
            task_id=task.task_id if task else None,
            classification=classification,
            score=score,
            status=status,
            features=features,
            penalties=penalties,
            todo_items=todo_items,
        )

    except Exception as e:
        logger.exception("Error analyzing report %s: %s", report_path, str(e))
        if task:
            update_task_progress(
                db, task, "failed", 0, "Analysis failed",
                error_message=str(e)
            )

        # Log failed analysis to audit trail (non-blocking)
        try:
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.ANALYSIS,
                action=f"Report analysis failed: {report_name}",
                status=AuditStatus.FAILURE,
                user_id=user_id,
                resource_type="report",
                resource_id=report_path,
                details={
                    "report_name": report_name,
                    "error_code": "ANALYSIS_ERROR",
                    "error_message": str(e),
                    "stage_failed": "analysis",
                },
            )
        except Exception as audit_error:
            logger.warning("Failed to log analysis failure audit event: %s", audit_error)

        return AnalysisResult(
            success=False,
            message=f"Analysis failed: {str(e)}",
            error_code="ANALYSIS_ERROR",
            suggestions=["Try analyzing the report again", "Check if the report is accessible"],
        )

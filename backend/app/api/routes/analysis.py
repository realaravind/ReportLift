"""Analysis API routes for report analysis operations."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.auth import UserInfo
from app.services.connection_config_service import (
    get_connection_config,
    ConnectionConfigError,
)
from app.services.analysis_service import (
    analyze_report,
    get_latest_analysis,
    get_analysis_by_id,
    get_task_by_id,
    create_analysis_task,
)
from app.services.guidance_generator import (
    GuidanceGenerator,
    GuidanceCategory,
    TodoGuidance,
    TodoGuidanceResponse,
    get_guidance_generator,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


# Request/Response schemas
class AnalyzeRequest(BaseModel):
    """Request to analyze a report."""

    report_path: str = Field(description="Full path to the report in SSRS")
    report_name: str = Field(description="Display name of the report")
    force: bool = Field(default=False, description="Force re-analysis even if cached")


class PreviousAnalysisInfo(BaseModel):
    """Information about a previous analysis."""

    id: int = Field(description="Analysis ID")
    analyzed_at: datetime = Field(description="When the analysis was performed")
    score: int | None = Field(description="Conversion readiness score")
    status: str | None = Field(description="Status color (green/yellow/red)")
    classification: str | None = Field(description="Report classification")


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""

    task_id: str = Field(description="Task ID for status polling")
    status: str = Field(description="Current task status")
    message: str = Field(description="Status message")
    previous_analysis: PreviousAnalysisInfo | None = Field(
        default=None, description="Previous analysis if exists"
    )


class TaskStatusResponse(BaseModel):
    """Response for task status polling."""

    task_id: str = Field(description="Task ID")
    status: str = Field(description="Task status: pending, running, completed, failed, cancelled")
    progress: int = Field(description="Progress percentage 0-100")
    current_step: str | None = Field(description="Current processing step")
    error_message: str | None = Field(default=None, description="Error message if failed")
    analysis_id: int | None = Field(default=None, description="Analysis ID if completed")


class AnalysisDetailResponse(BaseModel):
    """Detailed analysis response."""

    id: int = Field(description="Analysis ID")
    report_path: str = Field(description="Report path")
    report_name: str = Field(description="Report name")
    analyzed_at: datetime = Field(description="When analyzed")
    classification: str | None = Field(description="Report classification")
    score: int | None = Field(description="Conversion readiness score 0-100")
    status: str | None = Field(description="Status color")
    features: dict | None = Field(description="Extracted features")
    penalties: dict | None = Field(description="Score penalties breakdown")
    todo_items: list | None = Field(description="Conversion todo items")
    analysis_duration_ms: int | None = Field(description="Analysis duration in ms")


class ErrorDetail(BaseModel):
    """Error details."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    suggestions: list[str] | None = Field(default=None, description="Troubleshooting suggestions")


def _get_user_id(db: Session, identity: str) -> int | None:
    """Get user ID from identity string."""
    user = db.query(User).filter(User.full_identity == identity).first()
    return user.id if user else None


def _run_analysis_task(
    db_url: str,
    task_id: str,
    report_path: str,
    report_name: str,
    ssrs_url: str,
    username: str | None,
    password: str | None,
    domain: str | None,
    user_id: int | None,
):
    """Background task to run analysis.

    This runs in a separate thread with its own database session.
    """
    from app.models.base import SessionLocal

    db = SessionLocal()
    try:
        task = get_task_by_id(db, task_id)
        if not task:
            logger.error("Task not found: %s", task_id)
            return

        analyze_report(
            db=db,
            report_path=report_path,
            report_name=report_name,
            ssrs_url=ssrs_url,
            username=username,
            password=password,
            domain=domain,
            user_id=user_id,
            task=task,
        )
    except Exception as e:
        logger.exception("Background analysis failed: %s", str(e))
    finally:
        db.close()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Initiate report analysis",
    responses={
        400: {"description": "Invalid request or SSRS not configured"},
        500: {"description": "Server error"},
    },
)
async def initiate_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalyzeResponse:
    """Initiate analysis of an SSRS report.

    This endpoint:
    1. Checks for existing analysis (returns prompt if exists and force=False)
    2. Creates an analysis task
    3. Starts background analysis
    4. Returns task ID for status polling
    """
    logger.info(
        "Analysis requested by %s for report: %s",
        current_user.identity,
        request.report_path,
    )

    # Check for existing analysis
    previous = get_latest_analysis(db, request.report_path)
    previous_info = None
    if previous:
        previous_info = PreviousAnalysisInfo(
            id=previous.id,
            analyzed_at=previous.analyzed_at,
            score=previous.score,
            status=previous.status,
            classification=previous.classification,
        )

        # If not forcing re-analysis and we have recent results, prompt user
        if not request.force and not previous.is_stale:
            return AnalyzeResponse(
                task_id="",
                status="cached",
                message=f"Report was analyzed on {previous.analyzed_at.strftime('%Y-%m-%d %H:%M')}. Use force=true to re-analyze.",
                previous_analysis=previous_info,
            )

    # Get SSRS configuration
    try:
        config = get_connection_config(db, "ssrs", decrypt=True)
    except ConnectionConfigError as e:
        logger.error("Failed to get SSRS config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorDetail(
                code="CONFIG_ERROR",
                message="Failed to retrieve SSRS configuration",
            ).model_dump(),
        )

    if not config or not config.get("report_server_url"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="SSRS_NOT_CONFIGURED",
                message="SSRS is not configured. Please configure SSRS settings first.",
                suggestions=["Go to Settings and configure your SSRS connection"],
            ).model_dump(),
        )

    ssrs_url = config["report_server_url"]

    # Get credentials
    username = config.get("service_account_username")
    password = config.get("password")
    domain = current_user.domain

    if not username:
        username = current_user.username
        password = None

    # Get user ID
    user_id = _get_user_id(db, current_user.identity)

    # Create analysis task
    task = create_analysis_task(db, request.report_path, user_id)

    # Start background analysis
    background_tasks.add_task(
        _run_analysis_task,
        str(db.get_bind().url),
        task.task_id,
        request.report_path,
        request.report_name,
        ssrs_url,
        username,
        password,
        domain,
        user_id,
    )

    return AnalyzeResponse(
        task_id=task.task_id,
        status="pending",
        message="Analysis started",
        previous_analysis=previous_info,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get analysis task status",
    responses={
        404: {"description": "Task not found"},
    },
)
async def get_task_status(
    task_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskStatusResponse:
    """Get the status of an analysis task.

    Poll this endpoint to track analysis progress.
    """
    task = get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "Analysis task not found"},
        )

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress or 0,
        current_step=task.current_step,
        error_message=task.error_message,
        analysis_id=task.analysis_id,
    )


@router.get(
    "/report",
    response_model=AnalysisDetailResponse | None,
    summary="Get latest analysis for a report",
    responses={
        404: {"description": "No analysis found"},
    },
)
async def get_report_analysis(
    path: str = Query(..., description="Report path to look up"),
    current_user: Annotated[UserInfo, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> AnalysisDetailResponse:
    """Get the latest analysis for a report by path.

    Returns the most recent analysis if one exists.
    """
    analysis = get_latest_analysis(db, path)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "No analysis found for this report"},
        )

    return AnalysisDetailResponse(
        id=analysis.id,
        report_path=analysis.report_path,
        report_name=analysis.report_name,
        analyzed_at=analysis.analyzed_at,
        classification=analysis.classification,
        score=analysis.score,
        status=analysis.status,
        features=analysis.features,
        penalties=analysis.penalties,
        todo_items=analysis.todo_items,
        analysis_duration_ms=analysis.analysis_duration_ms,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Get analysis by ID",
    responses={
        404: {"description": "Analysis not found"},
    },
)
async def get_analysis(
    analysis_id: int,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisDetailResponse:
    """Get a specific analysis by its ID."""
    analysis = get_analysis_by_id(db, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Analysis not found"},
        )

    return AnalysisDetailResponse(
        id=analysis.id,
        report_path=analysis.report_path,
        report_name=analysis.report_name,
        analyzed_at=analysis.analyzed_at,
        classification=analysis.classification,
        score=analysis.score,
        status=analysis.status,
        features=analysis.features,
        penalties=analysis.penalties,
        todo_items=analysis.todo_items,
        analysis_duration_ms=analysis.analysis_duration_ms,
    )


# =============================================================================
# Guidance Request/Response Schemas
# =============================================================================


class GuidanceRequest(BaseModel):
    """Request schema for generating guidance."""

    category: Literal["stored_procedure", "expression", "visual", "subreport", "custom_code"] = Field(
        description="TODO item category"
    )
    item_name: str = Field(description="Name of the item (SP name, function name, etc.)")
    content: str | None = Field(default=None, description="Content (SP definition, expression, code)")
    location: str | None = Field(default=None, description="Location in report")
    context: str | None = Field(default=None, description="Additional context")
    pattern: str | None = Field(default=None, description="Detected pattern (for expressions)")
    complexity: str | None = Field(default=None, description="Complexity level (for SPs)")
    complexity_factors: list[str] | None = Field(default=None, description="Complexity factors")
    parameters: list[str] | None = Field(default=None, description="Parameters (for functions)")
    patterns: list[str] | None = Field(default=None, description="Detected patterns (for code)")
    use_cache: bool = Field(default=True, description="Whether to use cached guidance")


class GuidanceResponse(BaseModel):
    """Response schema for guidance endpoint."""

    todo_id: str | None = Field(default=None, description="TODO item ID if provided")
    category: str = Field(description="TODO category")
    item_name: str = Field(description="Item name")
    guidance: TodoGuidance = Field(description="Generated guidance")


# =============================================================================
# Guidance Endpoints
# =============================================================================


@router.post(
    "/guidance",
    response_model=GuidanceResponse,
    summary="Generate AI guidance for a TODO item",
    responses={
        400: {"description": "Invalid category or missing required fields"},
    },
)
async def generate_guidance(
    request: GuidanceRequest,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> GuidanceResponse:
    """Generate human-readable guidance for a TODO item.

    Uses AI (Ollama) when available, with automatic fallback to static templates.
    Guidance includes:
    - Summary of what needs to be done
    - Detailed explanation
    - Step-by-step instructions
    - Potential challenges
    - References and DAX equivalents (where applicable)
    """
    logger.info(
        "Guidance requested by %s for %s: %s",
        current_user.identity,
        request.category,
        request.item_name,
    )

    generator = get_guidance_generator()
    category = GuidanceCategory(request.category)

    # Generate guidance based on category
    if category == GuidanceCategory.STORED_PROCEDURE:
        guidance = await generator.generate_sp_guidance(
            sp_name=request.item_name,
            sp_definition=request.content,
            complexity=request.complexity,
            complexity_factors=request.complexity_factors,
            use_cache=request.use_cache,
        )
    elif category == GuidanceCategory.EXPRESSION:
        guidance = await generator.generate_expression_guidance(
            expression=request.content or request.item_name,
            location=request.location,
            context=request.context,
            pattern=request.pattern,
            use_cache=request.use_cache,
        )
    elif category == GuidanceCategory.VISUAL:
        guidance = await generator.generate_visual_guidance(
            visual_type=request.item_name,
            visual_name=request.content or request.item_name,
            context=request.context,
            use_cache=request.use_cache,
        )
    elif category == GuidanceCategory.SUBREPORT:
        guidance = await generator.generate_subreport_guidance(
            subreport_name=request.item_name,
            subreport_path=request.content,
            use_cache=request.use_cache,
        )
    elif category == GuidanceCategory.CUSTOM_CODE:
        guidance = await generator.generate_custom_code_guidance(
            function_name=request.item_name,
            code=request.content,
            parameters=request.parameters,
            patterns=request.patterns,
            use_cache=request.use_cache,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CATEGORY", "message": f"Unknown category: {request.category}"},
        )

    return GuidanceResponse(
        category=request.category,
        item_name=request.item_name,
        guidance=guidance,
    )


@router.get(
    "/{analysis_id}/todos/{todo_index}/guidance",
    response_model=GuidanceResponse,
    summary="Get guidance for a specific TODO item",
    responses={
        404: {"description": "Analysis or TODO item not found"},
    },
)
async def get_todo_guidance(
    analysis_id: int,
    todo_index: int,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    use_cache: bool = Query(default=True, description="Whether to use cached guidance"),
) -> GuidanceResponse:
    """Get AI-generated guidance for a specific TODO item from an analysis.

    Args:
        analysis_id: The analysis ID
        todo_index: Index of the TODO item in the analysis
        use_cache: Whether to use cached guidance

    Returns:
        GuidanceResponse with AI or template guidance
    """
    # Get analysis
    analysis = get_analysis_by_id(db, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Analysis not found"},
        )

    # Get TODO items
    todo_items = analysis.todo_items or []
    if todo_index < 0 or todo_index >= len(todo_items):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TODO_NOT_FOUND", "message": f"TODO item at index {todo_index} not found"},
        )

    todo = todo_items[todo_index]
    category_str = todo.get("category", "stored_procedure")
    item_name = todo.get("item_name") or todo.get("title", "Unknown")
    content = todo.get("original_content")
    location = todo.get("location")

    # Map category string to enum
    try:
        category = GuidanceCategory(category_str)
    except ValueError:
        category = GuidanceCategory.STORED_PROCEDURE

    generator = get_guidance_generator()

    # Generate guidance based on category
    if category == GuidanceCategory.STORED_PROCEDURE:
        guidance = await generator.generate_sp_guidance(
            sp_name=item_name,
            sp_definition=content,
            use_cache=use_cache,
        )
    elif category == GuidanceCategory.EXPRESSION:
        guidance = await generator.generate_expression_guidance(
            expression=content or item_name,
            location=location,
            use_cache=use_cache,
        )
    elif category == GuidanceCategory.VISUAL:
        guidance = await generator.generate_visual_guidance(
            visual_type=item_name,
            visual_name=item_name,
            use_cache=use_cache,
        )
    elif category == GuidanceCategory.SUBREPORT:
        guidance = await generator.generate_subreport_guidance(
            subreport_name=item_name,
            subreport_path=content,
            use_cache=use_cache,
        )
    elif category == GuidanceCategory.CUSTOM_CODE:
        guidance = await generator.generate_custom_code_guidance(
            function_name=item_name,
            code=content,
            use_cache=use_cache,
        )
    else:
        # Default to SP guidance
        guidance = await generator.generate_sp_guidance(
            sp_name=item_name,
            use_cache=use_cache,
        )

    return GuidanceResponse(
        todo_id=str(todo_index),
        category=category_str,
        item_name=item_name,
        guidance=guidance,
    )

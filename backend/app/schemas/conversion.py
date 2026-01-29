"""Conversion Pydantic schemas for report conversion operations."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConversionStatus(str, Enum):
    """Status of a conversion job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionStep(str, Enum):
    """Conversion process steps."""

    VALIDATING = "Validating analysis data..."
    GENERATING_SQL = "Generating SQL scripts..."
    REWRITING_SP = "Rewriting stored procedures..."
    BUILDING_PBIX = "Building Power BI report..."
    APPLYING_BRANDING = "Applying branding template..."
    FINALIZING = "Finalizing outputs..."


# Request schemas
class ConversionRequest(BaseModel):
    """Request to initiate report conversion."""

    force: bool = Field(
        default=False,
        description="Force conversion even if Snowflake is not configured",
    )


# Response schemas
class ConversionJobCreate(BaseModel):
    """Response when conversion job is created."""

    conversion_id: str = Field(description="Unique conversion job ID")
    status: ConversionStatus = Field(description="Current job status")
    started_at: datetime = Field(description="When conversion started")
    snowflake_configured: bool = Field(description="Whether Snowflake was configured")
    message: str = Field(description="Status message")


class ConversionProgressResponse(BaseModel):
    """Response for conversion status polling."""

    conversion_id: str = Field(description="Unique conversion job ID")
    status: ConversionStatus = Field(description="Current job status")
    current_step: str | None = Field(description="Current processing step")
    steps_completed: int = Field(description="Number of steps completed")
    total_steps: int = Field(description="Total number of steps")
    progress_percent: int = Field(description="Progress percentage 0-100")
    started_at: datetime | None = Field(description="When conversion started")
    completed_at: datetime | None = Field(description="When conversion completed")
    duration_ms: int | None = Field(description="Duration in milliseconds")


class ConversionOutputFile(BaseModel):
    """Information about a generated output file."""

    filename: str = Field(description="File name")
    file_type: str = Field(description="Type of file: sql, pbix, json")
    size_bytes: int = Field(description="File size in bytes")
    path: str = Field(description="Relative path in output directory")


class ConversionResult(BaseModel):
    """Complete conversion result with outputs."""

    conversion_id: str = Field(description="Unique conversion job ID")
    status: ConversionStatus = Field(description="Final job status")
    report_name: str = Field(description="Report name")
    report_path: str = Field(description="Original SSRS report path")
    started_at: datetime | None = Field(description="When conversion started")
    completed_at: datetime | None = Field(description="When conversion completed")
    duration_ms: int | None = Field(description="Duration in milliseconds")
    snowflake_configured: bool = Field(description="Whether Snowflake was configured")
    snowflake_schema: str | None = Field(description="Snowflake schema used")
    output_files: list[ConversionOutputFile] = Field(
        default_factory=list,
        description="List of generated output files",
    )

    model_config = {"from_attributes": True}


class ConversionErrorResponse(BaseModel):
    """Response when conversion fails."""

    conversion_id: str = Field(description="Unique conversion job ID")
    status: ConversionStatus = Field(default=ConversionStatus.FAILED)
    error_code: str = Field(description="Error code for categorization")
    error_message: str = Field(description="Human-readable error message")
    error_details: dict | None = Field(
        default=None,
        description="Additional error context",
    )
    can_retry: bool = Field(
        default=True,
        description="Whether the conversion can be retried",
    )


class ConversionCancelResponse(BaseModel):
    """Response when conversion is cancelled."""

    conversion_id: str = Field(description="Unique conversion job ID")
    status: ConversionStatus = Field(default=ConversionStatus.CANCELLED)
    message: str = Field(default="Conversion cancelled successfully")


class SnowflakeWarning(BaseModel):
    """Warning about Snowflake configuration status."""

    is_configured: bool = Field(description="Whether Snowflake is configured")
    warning_message: str | None = Field(
        default=None,
        description="Warning message if not configured",
    )
    can_proceed: bool = Field(
        default=True,
        description="Whether conversion can proceed",
    )
    placeholder_schema: str = Field(
        default="PLACEHOLDER_SCHEMA",
        description="Schema name to use if Snowflake not configured",
    )


# List response for multiple conversions
class ConversionListItem(BaseModel):
    """Summary item for listing conversions."""

    conversion_id: str
    report_name: str
    status: ConversionStatus
    created_at: datetime
    completed_at: datetime | None
    duration_ms: int | None

    model_config = {"from_attributes": True}


class ConversionListResponse(BaseModel):
    """Response for listing conversions."""

    items: list[ConversionListItem] = Field(default_factory=list)
    total_count: int = Field(default=0)


# Download schemas
class DownloadableFile(BaseModel):
    """Information about a downloadable output file."""

    type: str = Field(description="File type: pbix, sql, sql-zip, analysis")
    name: str = Field(description="File name for download")
    size: int = Field(description="File size in bytes")
    size_display: str = Field(description="Human-readable file size")
    download_url: str = Field(description="URL to download the file")
    available: bool = Field(default=True, description="Whether file is available")


class ConversionOutputsResponse(BaseModel):
    """Response listing all available download files."""

    conversion_id: str = Field(description="Conversion job ID")
    status: ConversionStatus = Field(description="Conversion status")
    report_name: str = Field(description="Report name")
    generated_at: datetime | None = Field(description="When outputs were generated")
    files: list[DownloadableFile] = Field(
        default_factory=list,
        description="List of downloadable files",
    )
    message: str | None = Field(
        default=None,
        description="Status message for incomplete conversions",
    )


class DownloadFileType(str, Enum):
    """Types of files that can be downloaded."""

    PBIX = "pbix"
    SQL = "sql"
    SQL_ZIP = "sql-zip"
    ANALYSIS = "analysis"


# Summary schemas
class SummaryStatus(str, Enum):
    """Overall conversion summary status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ReportInfo(BaseModel):
    """Information about the source report."""

    name: str = Field(description="Report name")
    path: str = Field(description="Original SSRS report path")


class DatasetSummary(BaseModel):
    """Summary of dataset conversions."""

    total: int = Field(description="Total datasets in report")
    converted_to_sql: int = Field(description="Datasets converted to SQL")


class VisualSummary(BaseModel):
    """Summary of visual conversions."""

    total: int = Field(description="Total visuals in report")
    tables: int = Field(default=0, description="Table visuals converted")
    charts: int = Field(default=0, description="Chart visuals converted")
    matrices: int = Field(default=0, description="Matrix visuals converted")
    textboxes: int = Field(default=0, description="Textbox visuals converted")
    placeholders: int = Field(default=0, description="Placeholder visuals created")


class ExpressionSummary(BaseModel):
    """Summary of expression conversions."""

    total: int = Field(description="Total expressions")
    auto_converted: int = Field(description="Expressions auto-converted")
    manual_required: int = Field(description="Expressions requiring manual review")


class StoredProcedureSummary(BaseModel):
    """Summary of stored procedure conversions."""

    total: int = Field(description="Total stored procedures")
    auto_rewritten: int = Field(description="SPs auto-rewritten (SIMPLE)")
    partial_rewrite: int = Field(default=0, description="SPs partially rewritten (MODERATE)")
    manual_required: int = Field(description="SPs requiring manual work (COMPLEX)")


class ConvertedSummary(BaseModel):
    """Summary of all converted elements."""

    datasets: DatasetSummary = Field(description="Dataset conversion summary")
    visuals: VisualSummary = Field(description="Visual conversion summary")
    expressions: ExpressionSummary = Field(description="Expression conversion summary")
    stored_procedures: StoredProcedureSummary = Field(description="SP conversion summary")


class AttentionItem(BaseModel):
    """Item requiring user attention."""

    type: str = Field(description="Item type: stored_procedure, visual, expression")
    name: str = Field(description="Item name or identifier")
    reason: str = Field(description="Reason attention is needed")
    visual_type: str | None = Field(default=None, description="Visual type if applicable")


class SummaryFile(BaseModel):
    """File information for summary display."""

    type: str = Field(description="File type")
    name: str = Field(description="File name")
    size: int = Field(description="File size in bytes")
    size_display: str = Field(description="Human-readable file size")


class ConversionSummaryResponse(BaseModel):
    """Complete conversion summary response."""

    conversion_id: str = Field(description="Conversion job ID")
    analysis_id: int = Field(description="Analysis ID")
    report: ReportInfo = Field(description="Report information")
    conversion_timestamp: datetime = Field(description="When conversion completed")
    duration_ms: int | None = Field(description="Conversion duration in milliseconds")
    status: SummaryStatus = Field(description="Overall summary status")
    snowflake_configured: bool = Field(description="Whether Snowflake was configured")
    converted: ConvertedSummary = Field(description="Converted elements summary")
    attention_required: list[AttentionItem] = Field(
        default_factory=list,
        description="Items requiring attention",
    )
    files: list[SummaryFile] = Field(
        default_factory=list,
        description="Generated files",
    )
    todo_count: int = Field(description="Total TODO items from analysis")

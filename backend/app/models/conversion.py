"""ConversionJob model for tracking report conversion jobs."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base


class ConversionStatus(str, Enum):
    """Status of a conversion job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionJob(Base):
    """Tracks conversion jobs for SSRS to Power BI conversion.

    Stores the state and outputs of a conversion process including:
    - Status tracking (pending, in_progress, completed, failed, cancelled)
    - Progress indicators (current step, steps completed)
    - Output file references
    - Error handling
    """

    __tablename__ = "conversion_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID

    # Link to analysis
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    analysis = relationship("Analysis", backref="conversion_jobs")

    # Report info (denormalized for convenience)
    report_path = Column(String(1000), nullable=False)
    report_name = Column(String(255), nullable=False)

    # Job status
    status = Column(
        String(20),
        nullable=False,
        default=ConversionStatus.PENDING.value,
        index=True,
    )

    # Progress tracking
    current_step = Column(String(100), nullable=True)
    steps_completed = Column(Integer, default=0)
    total_steps = Column(Integer, default=6)  # Default conversion has 6 steps

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Output storage
    output_directory = Column(String(500), nullable=True)  # Path to output files
    output_files = Column(JSON, nullable=True)  # List of generated files

    # Snowflake configuration status at conversion time
    snowflake_configured = Column(Boolean, default=False)
    snowflake_schema_used = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # User who triggered
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", backref="conversion_jobs")

    def __repr__(self) -> str:
        return f"<ConversionJob {self.job_id} status={self.status}>"

    def start(self) -> None:
        """Mark job as started."""
        self.status = ConversionStatus.IN_PROGRESS.value
        self.started_at = datetime.now(timezone.utc)

    def update_progress(self, step: str, steps_completed: int) -> None:
        """Update job progress."""
        self.current_step = step
        self.steps_completed = steps_completed

    def complete(self, output_directory: str, output_files: list[str]) -> None:
        """Mark job as completed."""
        self.status = ConversionStatus.COMPLETED.value
        self.completed_at = datetime.now(timezone.utc)
        self.output_directory = output_directory
        self.output_files = output_files
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def fail(self, error_message: str, error_details: dict | None = None) -> None:
        """Mark job as failed."""
        self.status = ConversionStatus.FAILED.value
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        self.error_details = error_details
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = ConversionStatus.CANCELLED.value
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status in [
            ConversionStatus.PENDING.value,
            ConversionStatus.IN_PROGRESS.value,
        ]

    @property
    def is_complete(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in [
            ConversionStatus.COMPLETED.value,
            ConversionStatus.FAILED.value,
            ConversionStatus.CANCELLED.value,
        ]

    @property
    def progress_percent(self) -> int:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0
        return int((self.steps_completed / self.total_steps) * 100)

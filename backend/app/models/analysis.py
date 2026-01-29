"""Analysis model for storing report analysis results."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Analysis(Base):
    """Analysis model for storing SSRS report analysis results.

    Stores the results of analyzing an SSRS report including:
    - Classification (Tabular, Analytical, Mixed, Complex)
    - Conversion score (0-100)
    - Extracted features and penalties
    """

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Report identification
    report_path = Column(String(1000), nullable=False, index=True)
    report_name = Column(String(255), nullable=False)
    report_id = Column(String(255), nullable=True)  # SSRS report ID if available

    # Analysis results
    classification = Column(String(50), nullable=True)  # Tabular, Analytical, Mixed, Complex
    score = Column(Integer, nullable=True)  # 0-100 conversion readiness score
    status = Column(String(20), nullable=True)  # green, yellow, red

    # Detailed analysis data (JSON)
    features = Column(JSON, nullable=True)  # Extracted report features
    penalties = Column(JSON, nullable=True)  # Score breakdown by category
    todo_items = Column(JSON, nullable=True)  # Generated todo list for conversion

    # RDL content (stored for reference)
    rdl_content = Column(Text, nullable=True)  # Original RDL XML

    # Timestamps and tracking
    analyzed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    analysis_duration_ms = Column(Integer, nullable=True)  # How long analysis took

    # User who triggered the analysis
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", backref="analyses")

    def __repr__(self) -> str:
        return f"<Analysis {self.report_name} score={self.score}>"

    @property
    def is_stale(self) -> bool:
        """Check if analysis is older than 24 hours."""
        if not self.analyzed_at:
            return True
        age = datetime.now(timezone.utc) - self.analyzed_at
        return age.total_seconds() > 86400  # 24 hours


class AnalysisTask(Base):
    """Tracks in-progress analysis tasks for status polling."""

    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID

    # Task state
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100), nullable=True)  # Current processing step
    error_message = Column(Text, nullable=True)

    # Link to report and result
    report_path = Column(String(1000), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    analysis = relationship("Analysis", backref="tasks")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # User who triggered
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self) -> str:
        return f"<AnalysisTask {self.task_id} status={self.status}>"

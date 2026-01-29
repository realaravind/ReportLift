"""Branding template model for storing Power BI template files."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class BrandingTemplate(Base):
    """BrandingTemplate model for storing Power BI branding templates.

    Stores metadata about uploaded .pbit template files used for
    applying corporate branding to converted reports.
    Only one template can be active at a time.
    """

    __tablename__ = "branding_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Template identification
    name = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(1000), nullable=False)  # Storage path
    file_size = Column(Integer, nullable=False)  # File size in bytes

    # Template status
    is_active = Column(Boolean, default=True, nullable=False)

    # Theme metadata extracted from template (for preview)
    theme_metadata = Column(JSON, nullable=True)  # colors, fonts, etc.

    # Timestamps and tracking
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # User who uploaded the template
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by = relationship("User", backref="uploaded_templates")

    def __repr__(self) -> str:
        return f"<BrandingTemplate {self.name} active={self.is_active}>"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)

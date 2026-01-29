"""Pydantic schemas for branding template operations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ThemeMetadata(BaseModel):
    """Theme metadata extracted from template."""
    name: Optional[str] = None
    dataColors: Optional[list[str]] = None
    background: Optional[str] = None
    foreground: Optional[str] = None


class TemplateResponse(BaseModel):
    """Response for a branding template."""
    id: int
    name: str
    file_size: int = Field(description="File size in bytes")
    file_size_mb: float = Field(description="File size in megabytes")
    uploaded_at: datetime
    uploaded_by: Optional[str] = None
    is_active: bool = True
    theme_metadata: Optional[ThemeMetadata] = None

    model_config = {"from_attributes": True}


class TemplateStatusResponse(BaseModel):
    """Response for template status check."""
    data: Optional[TemplateResponse] = None
    is_configured: bool = False
    message: Optional[str] = None


class TemplateUploadResponse(BaseModel):
    """Response after template upload."""
    data: TemplateResponse
    message: str = "Branding template uploaded successfully"
    replaced_existing: bool = False


class TemplateDeleteResponse(BaseModel):
    """Response after template deletion."""
    id: int
    deleted: bool = True
    message: str = "Branding template removed"


class TemplateValidationErrorResponse(BaseModel):
    """Response for template validation errors."""
    error: str
    code: str
    details: Optional[dict] = None

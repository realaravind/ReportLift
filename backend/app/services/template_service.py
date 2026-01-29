"""Branding Template Service.

This service handles upload, validation, storage, and retrieval
of Power BI branding templates (.pbit files).
"""

import json
import logging
import os
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, BinaryIO

from sqlalchemy.orm import Session

from app.models.branding_template import BrandingTemplate

logger = logging.getLogger(__name__)

# Configuration
TEMPLATE_STORAGE_PATH = os.environ.get(
    "TEMPLATE_STORAGE_PATH",
    "/tmp/reportlift/templates",
)
MAX_TEMPLATE_SIZE_MB = 50
MAX_TEMPLATE_SIZE_BYTES = MAX_TEMPLATE_SIZE_MB * 1024 * 1024


class TemplateValidationError(Exception):
    """Exception raised for template validation failures."""

    def __init__(
        self,
        message: str,
        code: str = "VALIDATION_ERROR",
    ):
        self.message = message
        self.code = code
        super().__init__(self.message)


@dataclass
class TemplateValidationResult:
    """Result of template validation."""
    is_valid: bool
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    file_size: int = 0
    theme_metadata: Optional[dict] = None


@dataclass
class TemplateInfo:
    """Information about a branding template."""
    id: int
    name: str
    file_size: int
    file_size_mb: float
    uploaded_at: datetime
    uploaded_by: Optional[str] = None
    is_active: bool = True
    theme_metadata: Optional[dict] = None


def validate_template_file(
    file: BinaryIO,
    filename: str,
) -> TemplateValidationResult:
    """Validate a template file.

    Args:
        file: File-like object containing the template
        filename: Original filename

    Returns:
        TemplateValidationResult with validation status
    """
    # Check file extension
    if not filename.lower().endswith(".pbit"):
        return TemplateValidationResult(
            is_valid=False,
            error_message="Only .pbit files are accepted",
            error_code="INVALID_EXTENSION",
        )

    # Read file content to check size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Seek back to start

    # Check file size
    if file_size > MAX_TEMPLATE_SIZE_BYTES:
        return TemplateValidationResult(
            is_valid=False,
            error_message=f"File size exceeds {MAX_TEMPLATE_SIZE_MB}MB limit",
            error_code="FILE_TOO_LARGE",
            file_size=file_size,
        )

    if file_size == 0:
        return TemplateValidationResult(
            is_valid=False,
            error_message="File is empty",
            error_code="EMPTY_FILE",
        )

    # Validate ZIP structure (PBIT is a ZIP file)
    try:
        with zipfile.ZipFile(file, "r") as zf:
            names = zf.namelist()

            # Check for required PBIT components
            required_files = ["[Content_Types].xml"]
            optional_but_expected = ["Report/Layout", "Settings", "Metadata"]

            has_required = all(
                any(req in name for name in names)
                for req in required_files
            )

            has_layout = any("Layout" in name for name in names)

            if not has_required:
                return TemplateValidationResult(
                    is_valid=False,
                    error_message="Invalid file: not a valid Power BI template",
                    error_code="INVALID_STRUCTURE",
                    file_size=file_size,
                )

            if not has_layout:
                return TemplateValidationResult(
                    is_valid=False,
                    error_message="Invalid template: missing required Layout component",
                    error_code="MISSING_LAYOUT",
                    file_size=file_size,
                )

            # Extract theme metadata if available
            theme_metadata = _extract_theme_metadata(zf)

            # Reset file position for further use
            file.seek(0)

            return TemplateValidationResult(
                is_valid=True,
                file_size=file_size,
                theme_metadata=theme_metadata,
            )

    except zipfile.BadZipFile:
        return TemplateValidationResult(
            is_valid=False,
            error_message="Invalid file: not a valid ZIP/PBIT file",
            error_code="BAD_ZIP",
            file_size=file_size,
        )
    except Exception as e:
        logger.exception("Error validating template file")
        return TemplateValidationResult(
            is_valid=False,
            error_message=f"Error validating file: {str(e)}",
            error_code="VALIDATION_ERROR",
            file_size=file_size,
        )


def _extract_theme_metadata(zf: zipfile.ZipFile) -> Optional[dict]:
    """Extract theme metadata from a PBIT file.

    Args:
        zf: Open ZipFile object

    Returns:
        Theme metadata dict or None
    """
    try:
        # Try to read Layout file for theme info
        layout_names = [n for n in zf.namelist() if "Layout" in n]
        if not layout_names:
            return None

        layout_content = zf.read(layout_names[0]).decode("utf-8")
        layout_data = json.loads(layout_content)

        # Extract theme from config
        config_str = layout_data.get("config", "{}")
        config = json.loads(config_str) if isinstance(config_str, str) else config_str

        theme_collection = config.get("themeCollection", {})
        base_theme = theme_collection.get("baseTheme", {})

        if base_theme:
            return {
                "name": base_theme.get("name", "Custom Theme"),
                "dataColors": base_theme.get("dataColors", [])[:4],  # First 4 colors
                "background": base_theme.get("background"),
                "foreground": base_theme.get("foreground"),
            }

    except Exception as e:
        logger.debug("Could not extract theme metadata: %s", e)

    return None


def get_current_template(db: Session) -> Optional[BrandingTemplate]:
    """Get the current active branding template.

    Args:
        db: Database session

    Returns:
        Active BrandingTemplate or None
    """
    return (
        db.query(BrandingTemplate)
        .filter(BrandingTemplate.is_active == True)
        .first()
    )


def get_template_info(db: Session) -> Optional[TemplateInfo]:
    """Get information about the current template.

    Args:
        db: Database session

    Returns:
        TemplateInfo or None if no template configured
    """
    template = get_current_template(db)
    if not template:
        return None

    uploaded_by_name = None
    if template.uploaded_by:
        uploaded_by_name = template.uploaded_by.username

    return TemplateInfo(
        id=template.id,
        name=template.name,
        file_size=template.file_size,
        file_size_mb=template.file_size_mb,
        uploaded_at=template.uploaded_at,
        uploaded_by=uploaded_by_name,
        is_active=template.is_active,
        theme_metadata=template.theme_metadata,
    )


def upload_template(
    db: Session,
    file: BinaryIO,
    filename: str,
    user_id: Optional[int] = None,
    replace_existing: bool = True,
) -> BrandingTemplate:
    """Upload a new branding template.

    Args:
        db: Database session
        file: File-like object containing the template
        filename: Original filename
        user_id: ID of user uploading the template
        replace_existing: Whether to replace existing template

    Returns:
        Created BrandingTemplate

    Raises:
        TemplateValidationError: If validation fails
    """
    # Validate the file
    validation = validate_template_file(file, filename)
    if not validation.is_valid:
        raise TemplateValidationError(
            message=validation.error_message,
            code=validation.error_code,
        )

    # Check for existing template
    existing = get_current_template(db)
    if existing and not replace_existing:
        raise TemplateValidationError(
            message="A template already exists. Set replace_existing=True to replace.",
            code="TEMPLATE_EXISTS",
        )

    # Deactivate existing template
    if existing:
        existing.is_active = False
        # Optionally move to archive
        _archive_template(existing)

    # Create storage directory
    current_dir = os.path.join(TEMPLATE_STORAGE_PATH, "current")
    os.makedirs(current_dir, exist_ok=True)

    # Generate unique filename
    template_id = str(uuid.uuid4())
    safe_filename = f"{template_id}.pbit"
    file_path = os.path.join(current_dir, safe_filename)

    # Save file to storage
    file.seek(0)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file, f)

    # Create database record
    template = BrandingTemplate(
        name=filename,
        file_path=file_path,
        file_size=validation.file_size,
        is_active=True,
        theme_metadata=validation.theme_metadata,
        uploaded_by_id=user_id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(
        "Uploaded branding template: %s (size=%d bytes)",
        filename,
        validation.file_size,
    )

    return template


def _archive_template(template: BrandingTemplate) -> None:
    """Move a template file to the archive directory.

    Args:
        template: Template to archive
    """
    try:
        if not os.path.exists(template.file_path):
            return

        archive_dir = os.path.join(TEMPLATE_STORAGE_PATH, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        archive_filename = f"{template.id}_{os.path.basename(template.file_path)}"
        archive_path = os.path.join(archive_dir, archive_filename)

        shutil.move(template.file_path, archive_path)
        template.file_path = archive_path

        logger.info("Archived template %s to %s", template.id, archive_path)

    except Exception as e:
        logger.error("Failed to archive template: %s", e)


def delete_template(
    db: Session,
    template_id: int,
    delete_file: bool = True,
) -> bool:
    """Delete a branding template.

    Args:
        db: Database session
        template_id: ID of template to delete
        delete_file: Whether to delete the file from storage

    Returns:
        True if deleted, False if not found
    """
    template = db.query(BrandingTemplate).filter(
        BrandingTemplate.id == template_id
    ).first()

    if not template:
        return False

    # Delete file if requested
    if delete_file and template.file_path and os.path.exists(template.file_path):
        try:
            os.remove(template.file_path)
            logger.info("Deleted template file: %s", template.file_path)
        except Exception as e:
            logger.error("Failed to delete template file: %s", e)

    # Delete database record
    db.delete(template)
    db.commit()

    logger.info("Deleted branding template: %s (id=%d)", template.name, template_id)
    return True


def get_template_file_path(db: Session, template_id: int) -> Optional[str]:
    """Get the file path for a template.

    Args:
        db: Database session
        template_id: Template ID

    Returns:
        File path or None if not found
    """
    template = db.query(BrandingTemplate).filter(
        BrandingTemplate.id == template_id
    ).first()

    if not template or not os.path.exists(template.file_path):
        return None

    return template.file_path


def get_template_theme(db: Session) -> Optional[dict]:
    """Get the theme from the current active template.

    Args:
        db: Database session

    Returns:
        Theme dict or None if no template configured
    """
    template = get_current_template(db)
    if not template:
        return None

    # Return stored metadata if available
    if template.theme_metadata:
        return template.theme_metadata

    # Otherwise try to extract from file
    if template.file_path and os.path.exists(template.file_path):
        try:
            with zipfile.ZipFile(template.file_path, "r") as zf:
                return _extract_theme_metadata(zf)
        except Exception as e:
            logger.debug("Could not extract theme from template: %s", e)

    return None

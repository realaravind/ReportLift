"""Template API routes for branding template management."""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.middleware import get_client_ip, get_user_agent
from app.models.audit_log import EventType, AuditStatus
from app.models.user import User
from app.schemas.template import (
    TemplateResponse,
    TemplateStatusResponse,
    TemplateUploadResponse,
    TemplateDeleteResponse,
    TemplateValidationErrorResponse,
    ThemeMetadata,
)
from app.services.audit_service import get_audit_service
from app.services.template_service import (
    get_current_template,
    get_template_info,
    upload_template,
    delete_template,
    get_template_file_path,
    TemplateValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get(
    "/current",
    response_model=TemplateStatusResponse,
    summary="Get current branding template",
    description="Get information about the currently configured branding template.",
)
async def get_current_template_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateStatusResponse:
    """Get the current branding template status.

    Returns template info if configured, or a message if not.
    """
    info = get_template_info(db)

    if not info:
        return TemplateStatusResponse(
            data=None,
            is_configured=False,
            message="No branding template configured",
        )

    # Convert to response model
    theme_metadata = None
    if info.theme_metadata:
        theme_metadata = ThemeMetadata(**info.theme_metadata)

    template_response = TemplateResponse(
        id=info.id,
        name=info.name,
        file_size=info.file_size,
        file_size_mb=info.file_size_mb,
        uploaded_at=info.uploaded_at,
        uploaded_by=info.uploaded_by,
        is_active=info.is_active,
        theme_metadata=theme_metadata,
    )

    return TemplateStatusResponse(
        data=template_response,
        is_configured=True,
        message=None,
    )


@router.post(
    "",
    response_model=TemplateUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload branding template",
    description="Upload a new Power BI branding template (.pbit file).",
    responses={
        400: {"model": TemplateValidationErrorResponse},
    },
)
async def upload_branding_template(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Power BI template file (.pbit)")],
    replace_existing: bool = True,
) -> TemplateUploadResponse:
    """Upload a new branding template.

    Accepts only .pbit files up to 50MB.
    If a template already exists and replace_existing is True,
    the existing template will be replaced.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "No filename provided",
                "code": "NO_FILENAME",
            },
        )

    # Check if template exists and get info for audit logging
    existing = get_current_template(db)
    replaced = existing is not None
    old_template_name = existing.name if existing else None
    old_file_size = existing.file_size if existing else None

    try:
        template = upload_template(
            db=db,
            file=file.file,
            filename=file.filename,
            user_id=current_user.id,
            replace_existing=replace_existing,
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.message,
                "code": e.code,
            },
        )

    # Log template upload/replace to audit trail
    try:
        audit_service = get_audit_service()
        operation = "replace" if replaced else "upload"
        action = "Branding template replaced" if replaced else "Branding template uploaded"

        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONFIG_CHANGE,
            action=action,
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="branding_template",
            resource_id=str(template.id),
            details={
                "old_template_name": old_template_name,
                "new_template_name": template.name,
                "old_file_size_bytes": old_file_size,
                "new_file_size_bytes": template.file_size,
                "operation": operation,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log template upload audit event: %s", audit_error)

    # Build response
    theme_metadata = None
    if template.theme_metadata:
        theme_metadata = ThemeMetadata(**template.theme_metadata)

    template_response = TemplateResponse(
        id=template.id,
        name=template.name,
        file_size=template.file_size,
        file_size_mb=template.file_size_mb,
        uploaded_at=template.uploaded_at,
        uploaded_by=current_user.username,
        is_active=template.is_active,
        theme_metadata=theme_metadata,
    )

    message = "Branding template uploaded successfully"
    if replaced:
        message = "Branding template replaced successfully"

    return TemplateUploadResponse(
        data=template_response,
        message=message,
        replaced_existing=replaced,
    )


@router.delete(
    "/{template_id}",
    response_model=TemplateDeleteResponse,
    summary="Delete branding template",
    description="Remove the branding template. Future conversions will not have branding applied.",
)
async def delete_branding_template(
    template_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateDeleteResponse:
    """Delete a branding template.

    Removes the template from storage and database.
    """
    # Get template info before deletion for audit logging
    template_info = get_template_info(db)
    old_template_name = template_info.name if template_info else None
    old_file_size = template_info.file_size if template_info else None

    deleted = delete_template(db, template_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Template not found",
                "code": "NOT_FOUND",
            },
        )

    # Log template deletion to audit trail
    try:
        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONFIG_CHANGE,
            action="Branding template removed",
            status=AuditStatus.SUCCESS,
            user_id=current_user.id,
            username=current_user.username,
            resource_type="branding_template",
            resource_id=str(template_id),
            details={
                "old_template_name": old_template_name,
                "new_template_name": None,
                "old_file_size_bytes": old_file_size,
                "new_file_size_bytes": None,
                "operation": "remove",
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as audit_error:
        logger.warning("Failed to log template delete audit event: %s", audit_error)

    return TemplateDeleteResponse(
        id=template_id,
        deleted=True,
        message="Branding template removed",
    )


@router.get(
    "/{template_id}/download",
    summary="Download branding template",
    description="Download the current branding template file.",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Template file download",
        },
        404: {"description": "Template not found"},
    },
)
async def download_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download a branding template file.

    Returns the .pbit file for backup or sharing.
    """
    file_path = get_template_file_path(db, template_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Template file not found",
                "code": "FILE_NOT_FOUND",
            },
        )

    # Get original filename from database
    template = get_current_template(db)
    filename = template.name if template else "template.pbit"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )

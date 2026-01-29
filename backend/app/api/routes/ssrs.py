"""SSRS API routes for browsing and managing SSRS content."""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.auth import UserInfo
from app.services.connection_config_service import (
    get_connection_config,
    ConnectionConfigError,
)
from app.services.ssrs_service import list_ssrs_folders, list_ssrs_reports

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ssrs", tags=["ssrs"])


class FolderItem(BaseModel):
    """Schema for a folder in the SSRS catalog."""

    name: str = Field(description="Folder name")
    path: str = Field(description="Full path to the folder")
    has_children: bool = Field(description="Whether the folder has subfolders")
    description: str | None = Field(default=None, description="Folder description")


class FoldersMeta(BaseModel):
    """Metadata for folder listing response."""

    timestamp: datetime = Field(description="When the request was processed")
    total_count: int = Field(description="Total number of folders returned")
    path: str = Field(description="The path that was queried")


class FoldersResponse(BaseModel):
    """Response schema for folder listing."""

    data: list[FolderItem] = Field(description="List of folders")
    meta: FoldersMeta = Field(description="Response metadata")


class FoldersErrorDetail(BaseModel):
    """Error details for folder listing failures."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    suggestions: list[str] | None = Field(default=None, description="Troubleshooting suggestions")


@router.get(
    "/folders",
    response_model=FoldersResponse,
    summary="List SSRS folders",
    responses={
        400: {"description": "SSRS not configured"},
        401: {"description": "Authentication failed"},
        403: {"description": "Permission denied"},
        500: {"description": "Server error"},
    },
)
async def list_folders(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    path: str = Query(default="/", description="Folder path to list (default: root)"),
) -> FoldersResponse:
    """List folders at a given path in the SSRS catalog.

    Uses the user's AD identity for permission filtering - only folders
    the user has access to will be returned.

    Args:
        current_user: Current authenticated user
        db: Database session
        path: Folder path to list (default "/" for root)

    Returns:
        FoldersResponse with list of folders

    Raises:
        HTTPException: If SSRS is not configured or an error occurs
    """
    logger.info(
        "SSRS folder listing requested by user: %s, path: %s",
        current_user.identity,
        path,
    )

    # Get SSRS configuration
    try:
        config = get_connection_config(db, "ssrs", decrypt=True)
    except ConnectionConfigError as e:
        logger.error("Failed to get SSRS config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FoldersErrorDetail(
                code="CONFIG_ERROR",
                message="Failed to retrieve SSRS configuration",
            ).model_dump(),
        )

    if not config or not config.get("report_server_url"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FoldersErrorDetail(
                code="SSRS_NOT_CONFIGURED",
                message="SSRS is not configured. Please configure SSRS settings first.",
                suggestions=["Go to Settings and configure your SSRS connection"],
            ).model_dump(),
        )

    report_server_url = config["report_server_url"]

    # Get credentials for authentication
    username = config.get("service_account_username")
    password = config.get("password")
    domain = current_user.domain if current_user.domain else None

    # If no service account, use current user's identity
    if not username:
        username = current_user.username
        password = None  # Will rely on NTLM pass-through

    # List folders
    result = list_ssrs_folders(
        report_server_url=report_server_url,
        path=path,
        username=username,
        password=password,
        domain=domain,
        timeout=10,
    )

    if not result.success:
        # Map error codes to HTTP status codes
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if result.error_code:
            error_code_value = result.error_code.value
            if error_code_value == "AUTH_FAILED":
                status_code = status.HTTP_401_UNAUTHORIZED
            elif error_code_value == "PERMISSION_DENIED":
                status_code = status.HTTP_403_FORBIDDEN
            elif error_code_value == "NOT_FOUND":
                status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=FoldersErrorDetail(
                code=result.error_code.value if result.error_code else "UNKNOWN",
                message=result.message,
                suggestions=result.suggestions,
            ).model_dump(),
        )

    # Build response
    folders = []
    if result.folders:
        folders = [
            FolderItem(
                name=folder.name,
                path=folder.path,
                has_children=folder.has_children,
                description=folder.description,
            )
            for folder in result.folders
        ]

    return FoldersResponse(
        data=folders,
        meta=FoldersMeta(
            timestamp=datetime.now(timezone.utc),
            total_count=len(folders),
            path=path,
        ),
    )


# Report schemas
class ReportItem(BaseModel):
    """Schema for a report in the SSRS catalog."""

    id: str = Field(description="Report unique identifier")
    name: str = Field(description="Report name")
    path: str = Field(description="Full path to the report")
    description: str | None = Field(default=None, description="Report description")
    modified_date: str | None = Field(default=None, description="Last modified date")
    size_bytes: int = Field(default=0, description="Report definition size in bytes")
    created_by: str | None = Field(default=None, description="Creator username")


class ReportsMeta(BaseModel):
    """Metadata for report listing response."""

    timestamp: datetime = Field(description="When the request was processed")
    total_count: int = Field(description="Total number of reports returned")
    folder_path: str = Field(description="The folder path that was queried")


class ReportsResponse(BaseModel):
    """Response schema for report listing."""

    data: list[ReportItem] = Field(description="List of reports")
    meta: ReportsMeta = Field(description="Response metadata")


class ReportsErrorDetail(BaseModel):
    """Error details for report listing failures."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    suggestions: list[str] | None = Field(default=None, description="Troubleshooting suggestions")


@router.get(
    "/reports",
    response_model=ReportsResponse,
    summary="List SSRS reports in a folder",
    responses={
        400: {"description": "SSRS not configured or invalid path"},
        401: {"description": "Authentication failed"},
        403: {"description": "Permission denied"},
        404: {"description": "Folder not found"},
        500: {"description": "Server error"},
    },
)
async def list_reports(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    path: str = Query(..., description="Folder path to list reports from"),
) -> ReportsResponse:
    """List reports in a specific folder in the SSRS catalog.

    Uses the user's AD identity for permission filtering - only reports
    the user has access to will be returned.

    Args:
        current_user: Current authenticated user
        db: Database session
        path: Folder path to list reports from (required)

    Returns:
        ReportsResponse with list of reports

    Raises:
        HTTPException: If SSRS is not configured or an error occurs
    """
    logger.info(
        "SSRS report listing requested by user: %s, path: %s",
        current_user.identity,
        path,
    )

    # Get SSRS configuration
    try:
        config = get_connection_config(db, "ssrs", decrypt=True)
    except ConnectionConfigError as e:
        logger.error("Failed to get SSRS config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ReportsErrorDetail(
                code="CONFIG_ERROR",
                message="Failed to retrieve SSRS configuration",
            ).model_dump(),
        )

    if not config or not config.get("report_server_url"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ReportsErrorDetail(
                code="SSRS_NOT_CONFIGURED",
                message="SSRS is not configured. Please configure SSRS settings first.",
                suggestions=["Go to Settings and configure your SSRS connection"],
            ).model_dump(),
        )

    report_server_url = config["report_server_url"]

    # Get credentials for authentication
    username = config.get("service_account_username")
    password = config.get("password")
    domain = current_user.domain if current_user.domain else None

    # If no service account, use current user's identity
    if not username:
        username = current_user.username
        password = None  # Will rely on NTLM pass-through

    # List reports
    result = list_ssrs_reports(
        report_server_url=report_server_url,
        path=path,
        username=username,
        password=password,
        domain=domain,
        timeout=10,
    )

    if not result.success:
        # Map error codes to HTTP status codes
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if result.error_code:
            error_code_value = result.error_code.value
            if error_code_value == "AUTH_FAILED":
                status_code = status.HTTP_401_UNAUTHORIZED
            elif error_code_value == "PERMISSION_DENIED":
                status_code = status.HTTP_403_FORBIDDEN
            elif error_code_value == "NOT_FOUND":
                status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=ReportsErrorDetail(
                code=result.error_code.value if result.error_code else "UNKNOWN",
                message=result.message,
                suggestions=result.suggestions,
            ).model_dump(),
        )

    # Build response
    reports = []
    if result.reports:
        reports = [
            ReportItem(
                id=report.id,
                name=report.name,
                path=report.path,
                description=report.description,
                modified_date=report.modified_date,
                size_bytes=report.size_bytes,
                created_by=report.created_by,
            )
            for report in result.reports
        ]

    return ReportsResponse(
        data=reports,
        meta=ReportsMeta(
            timestamp=datetime.now(timezone.utc),
            total_count=len(reports),
            folder_path=path,
        ),
    )

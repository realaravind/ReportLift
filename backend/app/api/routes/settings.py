"""Settings API routes for application configuration."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.middleware import get_client_ip, get_user_agent
from app.models.audit_log import EventType, AuditStatus
from app.models.connection_config import ConnectionConfig
from app.models.user import User
from app.schemas.auth import UserInfo
from app.schemas.settings import (
    AllSettingsResponse,
    SSRSSettingsResponse,
    SSRSSettingsUpdateRequest,
    SSRSTestResultDetails,
    SSRSTestResultResponse,
    SnowflakeSettingsResponse,
    SnowflakeSettingsUpdateRequest,
    SnowflakeTestResultDetails,
    SnowflakeTestResultResponse,
    OllamaSettingsResponse,
    OllamaSettingsUpdateRequest,
    SystemSettingsResponse,
)
from app.services.audit_service import get_audit_service
from app.services.oauth_service import OAuthService, OAuthError
from app.services.snowflake_service import test_snowflake_connection
from app.services.ssrs_service import test_ssrs_connection
from app.services.connection_config_service import (
    save_connection_config,
    get_connection_config,
    ConnectionConfigError,
)

logger = logging.getLogger(__name__)


# Sensitive field patterns that should be redacted in audit logs
SENSITIVE_FIELD_PATTERNS = frozenset({
    "password", "secret", "token", "api_key", "apikey",
    "credential", "private_key", "client_secret",
    "access_token", "refresh_token",
})


def _calculate_config_diff(
    old_config: dict[str, Any] | None,
    new_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Calculate differences between old and new configuration.

    Args:
        old_config: Previous configuration (None if new)
        new_config: New configuration

    Returns:
        Dictionary of changed fields with old/new values
    """
    if old_config is None:
        old_config = {}

    changes = {}
    all_keys = set(old_config.keys()) | set(new_config.keys())

    for key in all_keys:
        old_value = old_config.get(key)
        new_value = new_config.get(key)

        if old_value != new_value:
            # Redact sensitive values
            key_lower = key.lower()
            is_sensitive = any(
                pattern in key_lower for pattern in SENSITIVE_FIELD_PATTERNS
            )

            if is_sensitive:
                changes[key] = {
                    "old": "[REDACTED]" if old_value else None,
                    "new": "[REDACTED]" if new_value else None,
                }
            else:
                changes[key] = {
                    "old": old_value,
                    "new": new_value,
                }

    return changes


def _log_config_change(
    db: Session,
    request: Request,
    config_type: str,
    action: str,
    user: UserInfo,
    changes: dict[str, dict[str, Any]],
) -> None:
    """Log a configuration change to the audit trail.

    Args:
        db: Database session
        request: HTTP request for IP/user agent
        config_type: Type of configuration (ssrs_config, snowflake_config, etc.)
        action: Description of the action
        user: Current user
        changes: Dictionary of changed fields
    """
    if not changes:
        return  # No changes to log

    try:
        # Get user ID from database
        user_record = db.query(User).filter(User.full_identity == user.identity).first()
        user_id = user_record.id if user_record else None

        audit_service = get_audit_service()
        audit_service.log_event_sync(
            db=db,
            event_type=EventType.CONFIG_CHANGE,
            action=action,
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            username=user.identity,
            resource_type=config_type,
            details={
                "changed_fields": list(changes.keys()),
                "changes": changes,
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except Exception as e:
        logger.warning("Failed to log config change audit event: %s", e)

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_ssrs_settings_from_db(db: Session) -> SSRSSettingsResponse:
    """Get SSRS settings with sensitive values masked from database."""
    try:
        config = get_connection_config(db, "ssrs", decrypt=False)
    except ConnectionConfigError as e:
        logger.error("Failed to get SSRS config: %s", e.message)
        config = None

    if config is None:
        return SSRSSettingsResponse(
            report_server_url=None,
            auth_method="windows_integrated",
            service_account_username=None,
            has_credentials=False,
            updated_at=None,
        )

    # Get updated_at from the database record
    config_record = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == "ssrs"
    ).first()
    updated_at = config_record.updated_at if config_record else None

    return SSRSSettingsResponse(
        report_server_url=config.get("report_server_url"),
        auth_method=config.get("auth_method", "windows_integrated"),
        service_account_username=config.get("service_account_username"),
        has_credentials=bool(config.get("password")),
        updated_at=updated_at,
    )


def _get_snowflake_settings_from_db(db: Session, user_id: int | None = None) -> SnowflakeSettingsResponse:
    """Get Snowflake settings with sensitive values masked from database.

    Args:
        db: Database session
        user_id: Optional user ID to check OAuth status (if None, status is 'not_authorized')

    Returns:
        SnowflakeSettingsResponse with settings
    """
    # Check if OAuth is configured in environment
    has_oauth = bool(
        settings.snowflake_oauth_client_id
        and settings.snowflake_oauth_auth_url
        and settings.snowflake_oauth_token_url
    )

    # Get connection config from database
    try:
        config = get_connection_config(db, "snowflake", decrypt=False)
    except ConnectionConfigError as e:
        logger.error("Failed to get Snowflake config: %s", e.message)
        config = None

    if config is None:
        return SnowflakeSettingsResponse(
            account_identifier=None,
            warehouse=None,
            database=None,
            schema_name=None,
            auth_method="oauth" if has_oauth else "basic",
            has_oauth_config=has_oauth,
            oauth_status="not_authorized",
            username=None,
            has_password=False,
            updated_at=None,
        )

    # Get updated_at from the database record
    config_record = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == "snowflake"
    ).first()
    updated_at = config_record.updated_at if config_record else None

    # Determine OAuth status if user_id is provided
    oauth_status = "not_authorized"
    if user_id and has_oauth:
        try:
            oauth_service = OAuthService(db)
            status = oauth_service.get_status(user_id, "snowflake")
            if status.authenticated:
                oauth_status = "authorized"
            elif status.expires_at:
                oauth_status = "expired"
        except Exception as e:
            logger.warning("Failed to get OAuth status: %s", e)

    return SnowflakeSettingsResponse(
        account_identifier=config.get("account_identifier"),
        warehouse=config.get("warehouse"),
        database=config.get("database"),
        schema_name=config.get("schema_name"),
        auth_method=config.get("auth_method", "oauth" if has_oauth else "basic"),
        has_oauth_config=has_oauth,
        oauth_status=oauth_status,
        username=config.get("username"),
        has_password=bool(config.get("password")),
        updated_at=updated_at,
    )


def _get_ollama_settings_from_db(db: Session) -> OllamaSettingsResponse:
    """Get Ollama settings from database.

    Args:
        db: Database session

    Returns:
        OllamaSettingsResponse with settings
    """
    try:
        config = get_connection_config(db, "ollama", decrypt=False)
    except ConnectionConfigError as e:
        logger.error("Failed to get Ollama config: %s", e.message)
        config = None

    if config is None:
        return OllamaSettingsResponse(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=False,
            timeout_seconds=60,
            updated_at=None,
        )

    # Get updated_at from the database record
    config_record = db.query(ConnectionConfig).filter(
        ConnectionConfig.service_type == "ollama"
    ).first()
    updated_at = config_record.updated_at if config_record else None

    return OllamaSettingsResponse(
        host_url=config.get("host_url", "http://localhost:11434"),
        model_name=config.get("model_name", "codellama:13b"),
        enabled=config.get("enabled", False),
        timeout_seconds=config.get("timeout_seconds", 60),
        updated_at=updated_at,
    )


def _get_system_settings() -> SystemSettingsResponse:
    """Get system settings."""
    return SystemSettingsResponse(
        environment=settings.environment,
        version=settings.app_version,
        debug_mode=settings.environment == "development",
    )


@router.get(
    "",
    response_model=AllSettingsResponse,
    summary="Get all settings",
    description="Returns all application settings with sensitive values masked.",
)
async def get_all_settings(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AllSettingsResponse:
    """Get all application settings.

    Sensitive values (passwords, secrets) are never returned.
    Instead, boolean flags indicate whether credentials are configured.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        AllSettingsResponse with all settings
    """
    logger.debug("Settings requested by user: %s", current_user.identity)

    return AllSettingsResponse(
        ssrs=_get_ssrs_settings_from_db(db),
        snowflake=_get_snowflake_settings_from_db(db, current_user.user_id),
        ollama=_get_ollama_settings_from_db(db),
        system=_get_system_settings(),
    )


@router.get(
    "/ssrs",
    response_model=SSRSSettingsResponse,
    summary="Get SSRS settings",
)
async def get_ssrs_settings(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SSRSSettingsResponse:
    """Get SSRS connection settings."""
    return _get_ssrs_settings_from_db(db)


@router.put(
    "/ssrs",
    response_model=SSRSSettingsResponse,
    summary="Update SSRS settings",
)
async def update_ssrs_settings(
    request_body: SSRSSettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SSRSSettingsResponse:
    """Update SSRS connection settings.

    Credentials are encrypted before storage.

    Args:
        request_body: SSRS settings to update
        request: HTTP request for audit logging
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated SSRS settings (with sensitive values masked)
    """
    logger.info("SSRS settings update by user: %s", current_user.identity)

    # Get existing config for change tracking
    try:
        old_config = get_connection_config(db, "ssrs", decrypt=False) or {}
    except ConnectionConfigError:
        old_config = {}

    # Build config dictionary
    config = {
        "report_server_url": request_body.report_server_url,
        "auth_method": request_body.auth_method,
        "service_account_username": request_body.service_account_username,
    }

    # Only include password if provided (allows partial updates)
    if request_body.service_account_password:
        config["password"] = request_body.service_account_password

    # If no new password provided, preserve existing password
    if not request_body.service_account_password:
        if old_config.get("password"):
            config["password"] = old_config["password"]

    try:
        save_connection_config(db, "ssrs", config)
        logger.info("SSRS settings saved successfully")

        # Log configuration change
        changes = _calculate_config_diff(old_config, config)
        _log_config_change(
            db=db,
            request=request,
            config_type="ssrs_config",
            action="SSRS connection updated",
            user=current_user,
            changes=changes,
        )
    except ConnectionConfigError as e:
        logger.error("Failed to save SSRS config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_SAVE_ERROR", "message": "Failed to save configuration"},
        )

    return _get_ssrs_settings_from_db(db)


@router.delete(
    "/ssrs/credentials",
    response_model=SSRSSettingsResponse,
    summary="Clear SSRS credentials",
)
async def clear_ssrs_credentials(
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SSRSSettingsResponse:
    """Clear SSRS service account credentials.

    Removes the stored password but preserves other settings.

    Args:
        request: HTTP request for audit logging
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated SSRS settings (with credentials cleared)
    """
    logger.info("SSRS credentials clear requested by user: %s", current_user.identity)

    try:
        existing_config = get_connection_config(db, "ssrs", decrypt=False)
        if existing_config:
            old_config = existing_config.copy()
            # Remove password but keep other settings
            existing_config.pop("password", None)
            save_connection_config(db, "ssrs", existing_config)
            logger.info("SSRS credentials cleared successfully")

            # Log configuration change
            changes = _calculate_config_diff(old_config, existing_config)
            _log_config_change(
                db=db,
                request=request,
                config_type="ssrs_config",
                action="SSRS credentials cleared",
                user=current_user,
                changes=changes,
            )
    except ConnectionConfigError as e:
        logger.error("Failed to clear SSRS credentials: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_CLEAR_ERROR", "message": "Failed to clear credentials"},
        )

    return _get_ssrs_settings_from_db(db)


@router.post(
    "/ssrs/test",
    response_model=SSRSTestResultResponse,
    summary="Test SSRS connection",
)
async def test_ssrs_connection_endpoint(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SSRSTestResultResponse:
    """Test SSRS connection using current user's AD identity.

    Attempts to connect to the configured Report Server and verify
    the user has access to the root folder.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        SSRSTestResultResponse with test results

    Raises:
        HTTPException: If SSRS is not configured
    """
    logger.info("SSRS connection test requested by user: %s", current_user.identity)

    # Get SSRS configuration
    try:
        config = get_connection_config(db, "ssrs", decrypt=True)
    except ConnectionConfigError as e:
        logger.error("Failed to get SSRS config for test: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_ERROR", "message": "Failed to retrieve SSRS configuration"},
        )

    if not config or not config.get("report_server_url"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SSRS_NOT_CONFIGURED",
                "message": "SSRS is not configured. Please configure SSRS settings first.",
            },
        )

    report_server_url = config["report_server_url"]

    # Get credentials - use service account if configured, otherwise use current user
    username = config.get("service_account_username")
    password = config.get("password")
    domain = current_user.domain if current_user.domain else None

    # If no service account, we'll rely on NTLM pass-through with current user
    # For NTLM pass-through, we use the current user's domain\username
    if not username:
        username = current_user.username
        password = None  # No password for pass-through (will use Windows auth)

    # Test the connection
    result = test_ssrs_connection(
        report_server_url=report_server_url,
        username=username,
        password=password,
        domain=domain,
        timeout=10,
    )

    # Convert to response schema
    return SSRSTestResultResponse(
        success=result.success,
        message=result.message,
        details=SSRSTestResultDetails(
            server_version=result.server_version,
            response_time_ms=result.response_time_ms,
            root_folder_accessible=result.root_folder_accessible,
            error_code=result.error_code.value if result.error_code else None,
        ),
        suggestions=result.suggestions,
        tested_at=datetime.now(timezone.utc),
    )


@router.get(
    "/snowflake",
    response_model=SnowflakeSettingsResponse,
    summary="Get Snowflake settings",
)
async def get_snowflake_settings(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SnowflakeSettingsResponse:
    """Get Snowflake connection settings."""
    return _get_snowflake_settings_from_db(db, current_user.user_id)


@router.put(
    "/snowflake",
    response_model=SnowflakeSettingsResponse,
    summary="Update Snowflake settings",
)
async def update_snowflake_settings(
    request_body: SnowflakeSettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SnowflakeSettingsResponse:
    """Update Snowflake connection settings.

    Credentials are encrypted before storage.

    Args:
        request_body: Snowflake settings to update
        request: HTTP request for audit logging
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated Snowflake settings (with sensitive values masked)
    """
    logger.info("Snowflake settings update by user: %s", current_user.identity)

    # Get existing config for change tracking
    try:
        old_config = get_connection_config(db, "snowflake", decrypt=False) or {}
    except ConnectionConfigError:
        old_config = {}

    # Build config dictionary
    config = {
        "account_identifier": request_body.account_identifier,
        "warehouse": request_body.warehouse,
        "database": request_body.database,
        "schema_name": request_body.schema_name,
        "auth_method": request_body.auth_method,
        "username": request_body.username,
    }

    # Only include password if provided (allows partial updates)
    if request_body.password:
        config["password"] = request_body.password

    # If no new password provided, preserve existing password
    if not request_body.password:
        if old_config.get("password"):
            config["password"] = old_config["password"]

    try:
        save_connection_config(db, "snowflake", config)
        logger.info("Snowflake settings saved successfully")

        # Log configuration change
        changes = _calculate_config_diff(old_config, config)
        _log_config_change(
            db=db,
            request=request,
            config_type="snowflake_config",
            action="Snowflake connection updated",
            user=current_user,
            changes=changes,
        )
    except ConnectionConfigError as e:
        logger.error("Failed to save Snowflake config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_SAVE_ERROR", "message": "Failed to save configuration"},
        )

    return _get_snowflake_settings_from_db(db, current_user.user_id)


@router.delete(
    "/snowflake/credentials",
    response_model=SnowflakeSettingsResponse,
    summary="Clear Snowflake credentials",
)
async def clear_snowflake_credentials(
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SnowflakeSettingsResponse:
    """Clear Snowflake basic auth credentials.

    Removes the stored password but preserves other settings.
    Note: This does not revoke OAuth tokens - use the OAuth revoke endpoint for that.

    Args:
        request: HTTP request for audit logging
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated Snowflake settings (with credentials cleared)
    """
    logger.info("Snowflake credentials clear requested by user: %s", current_user.identity)

    try:
        existing_config = get_connection_config(db, "snowflake", decrypt=False)
        if existing_config:
            old_config = existing_config.copy()
            # Remove password but keep other settings
            existing_config.pop("password", None)
            save_connection_config(db, "snowflake", existing_config)
            logger.info("Snowflake credentials cleared successfully")

            # Log configuration change
            changes = _calculate_config_diff(old_config, existing_config)
            _log_config_change(
                db=db,
                request=request,
                config_type="snowflake_config",
                action="Snowflake credentials cleared",
                user=current_user,
                changes=changes,
            )
    except ConnectionConfigError as e:
        logger.error("Failed to clear Snowflake credentials: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_CLEAR_ERROR", "message": "Failed to clear credentials"},
        )

    return _get_snowflake_settings_from_db(db, current_user.user_id)


@router.post(
    "/snowflake/test",
    response_model=SnowflakeTestResultResponse,
    summary="Test Snowflake connection",
)
async def test_snowflake_connection_endpoint(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SnowflakeTestResultResponse:
    """Test Snowflake connection using stored configuration.

    Attempts to connect to Snowflake and execute a test query.
    For OAuth authentication, uses stored tokens (refreshing if needed).
    For basic authentication, uses stored username/password.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        SnowflakeTestResultResponse with test results

    Raises:
        HTTPException: If Snowflake is not configured
    """
    logger.info("Snowflake connection test requested by user: %s", current_user.identity)

    # Get Snowflake configuration
    try:
        config = get_connection_config(db, "snowflake", decrypt=True)
    except ConnectionConfigError as e:
        logger.error("Failed to get Snowflake config for test: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_ERROR", "message": "Failed to retrieve Snowflake configuration"},
        )

    if not config or not config.get("account_identifier"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SNOWFLAKE_NOT_CONFIGURED",
                "message": "Snowflake is not configured. Please configure Snowflake settings first.",
            },
        )

    account_identifier = config["account_identifier"]
    warehouse = config.get("warehouse", "")
    database = config.get("database", "")
    schema = config.get("schema_name", "")
    auth_method = config.get("auth_method", "oauth")

    # Get credentials based on auth method
    oauth_token = None
    username = None
    password = None

    if auth_method == "oauth":
        # Check if OAuth is configured and get valid token
        oauth_service = OAuthService(db)
        if not oauth_service.is_configured:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "OAUTH_NOT_CONFIGURED",
                    "message": "OAuth is not configured. Switch to basic authentication or configure OAuth.",
                },
            )

        try:
            # Get valid token (will refresh if expired)
            oauth_token = await oauth_service.get_valid_token(
                user_id=current_user.user_id,
                service_type="snowflake",
            )
        except OAuthError as e:
            logger.warning("OAuth token retrieval failed: %s", e.message)
            # Return result indicating re-auth is needed
            return SnowflakeTestResultResponse(
                success=False,
                message="OAuth authorization required",
                details=SnowflakeTestResultDetails(
                    account=account_identifier,
                    warehouse=warehouse,
                    database=database,
                    schema=schema,
                    error_code="TOKEN_EXPIRED",
                ),
                suggestions=["Click 'Connect with SSO' to authorize your Snowflake connection"],
                requires_reauth=True,
                tested_at=datetime.now(timezone.utc),
            )
    else:
        # Basic authentication
        username = config.get("username")
        password = config.get("password")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CREDENTIALS_MISSING",
                    "message": "Username is required for basic authentication.",
                },
            )

    # Test the connection
    result = test_snowflake_connection(
        account_identifier=account_identifier,
        warehouse=warehouse,
        database=database,
        schema=schema,
        auth_method=auth_method,
        username=username,
        password=password,
        oauth_token=oauth_token,
        timeout=15,
    )

    # Convert to response schema
    return SnowflakeTestResultResponse(
        success=result.success,
        message=result.message,
        details=SnowflakeTestResultDetails(
            account=result.account or account_identifier,
            warehouse=result.warehouse,
            database=result.database,
            schema=result.schema,
            role=result.role,
            user=result.user,
            response_time_ms=result.response_time_ms,
            error_code=result.error_code.value if result.error_code else None,
            snowflake_error_code=result.snowflake_error_code,
        ),
        suggestions=result.suggestions if result.suggestions else None,
        requires_reauth=result.requires_reauth,
        tested_at=datetime.now(timezone.utc),
    )


@router.get(
    "/ollama",
    response_model=OllamaSettingsResponse,
    summary="Get Ollama settings",
)
async def get_ollama_settings(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OllamaSettingsResponse:
    """Get Ollama AI service settings."""
    return _get_ollama_settings_from_db(db)


@router.put(
    "/ollama",
    response_model=OllamaSettingsResponse,
    summary="Update Ollama settings",
)
async def update_ollama_settings(
    request_body: OllamaSettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OllamaSettingsResponse:
    """Update Ollama AI service settings.

    Args:
        request_body: Ollama settings to update
        request: HTTP request for audit logging
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated Ollama settings
    """
    logger.info("Ollama settings update by user: %s", current_user.identity)

    # Get existing config for change tracking
    try:
        old_config = get_connection_config(db, "ollama", decrypt=False) or {}
    except ConnectionConfigError:
        old_config = {}

    # Build config dictionary
    config = {
        "host_url": request_body.host_url,
        "model_name": request_body.model_name,
        "enabled": request_body.enabled,
        "timeout_seconds": request_body.timeout_seconds,
    }

    try:
        save_connection_config(db, "ollama", config)
        logger.info("Ollama settings saved successfully")

        # Log configuration change
        changes = _calculate_config_diff(old_config, config)
        _log_config_change(
            db=db,
            request=request,
            config_type="ollama_config",
            action="Ollama setting changed",
            user=current_user,
            changes=changes,
        )
    except ConnectionConfigError as e:
        logger.error("Failed to save Ollama config: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_SAVE_ERROR", "message": "Failed to save configuration"},
        )

    return _get_ollama_settings_from_db(db)


@router.get(
    "/system",
    response_model=SystemSettingsResponse,
    summary="Get system settings",
)
async def get_system_settings(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> SystemSettingsResponse:
    """Get system settings."""
    return _get_system_settings()

"""Health check endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.schemas.auth import UserInfo
from app.schemas.settings import (
    HealthResponse,
    ServiceHealth,
    ServiceHealthDetails,
)
from app.services.connection_config_service import (
    get_connection_config,
    ConnectionConfigError,
)
from app.services.ollama_service import (
    check_ollama_health_async,
    get_ollama_client,
    OllamaConfig,
    OllamaErrorCode,
)
from app.services.snowflake_service import test_snowflake_connection, SnowflakeErrorCode
from app.services.ssrs_service import test_ssrs_connection, SSRSErrorCode
from app.services.oauth_service import OAuthService, OAuthError
from app.services.ai_fallback import (
    get_ai_fallback_service,
    AIStatusResponse,
    ConversionMethodBreakdown,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-service timeout for health checks (seconds)
SERVICE_TIMEOUT = 10


class BasicHealthResponse(BaseModel):
    """Basic health check response schema."""

    status: str
    timestamp: str
    version: str


@router.get("/health", response_model=BasicHealthResponse)
async def health_check() -> BasicHealthResponse:
    """
    Health check endpoint.

    Returns the current health status of the API.
    """
    return BasicHealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
    )


async def _check_ssrs_health(db: Session) -> ServiceHealth:
    """Check SSRS connection health."""
    try:
        config = get_connection_config(db, "ssrs", decrypt=True)
    except ConnectionConfigError as e:
        logger.warning("Failed to get SSRS config for health check: %s", e.message)
        config = None

    if not config or not config.get("report_server_url"):
        return ServiceHealth(
            service="ssrs",
            status="not_configured",
            message="SSRS is not configured",
            last_checked=datetime.now(timezone.utc),
        )

    # Run the test in a thread pool since it's blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: test_ssrs_connection(
            report_server_url=config["report_server_url"],
            username=config.get("service_account_username"),
            password=config.get("password"),
            timeout=SERVICE_TIMEOUT,
        ),
    )

    if result.success:
        return ServiceHealth(
            service="ssrs",
            status="connected",
            message=result.message,
            details=ServiceHealthDetails(
                version=result.server_version,
                response_time_ms=result.response_time_ms,
            ),
            last_checked=datetime.now(timezone.utc),
        )
    else:
        return ServiceHealth(
            service="ssrs",
            status="disconnected",
            message=result.message,
            details=ServiceHealthDetails(
                response_time_ms=result.response_time_ms,
                error_code=result.error_code.value if result.error_code else None,
            ),
            last_checked=datetime.now(timezone.utc),
        )


async def _check_snowflake_health(db: Session, user_id: int | None) -> ServiceHealth:
    """Check Snowflake connection health."""
    try:
        config = get_connection_config(db, "snowflake", decrypt=True)
    except ConnectionConfigError as e:
        logger.warning("Failed to get Snowflake config for health check: %s", e.message)
        config = None

    if not config or not config.get("account_identifier"):
        return ServiceHealth(
            service="snowflake",
            status="not_configured",
            message="Snowflake is not configured",
            last_checked=datetime.now(timezone.utc),
        )

    account_identifier = config["account_identifier"]
    warehouse = config.get("warehouse", "")
    database = config.get("database", "")
    schema = config.get("schema_name", "")
    auth_method = config.get("auth_method", "oauth")

    oauth_token = None
    username = None
    password = None

    if auth_method == "oauth":
        # Try to get OAuth token
        oauth_service = OAuthService(db)
        if not oauth_service.is_configured:
            return ServiceHealth(
                service="snowflake",
                status="not_configured",
                message="OAuth is not configured",
                last_checked=datetime.now(timezone.utc),
            )

        if not user_id:
            return ServiceHealth(
                service="snowflake",
                status="not_configured",
                message="OAuth requires user authentication",
                last_checked=datetime.now(timezone.utc),
            )

        try:
            oauth_token = await oauth_service.get_valid_token(
                user_id=user_id,
                service_type="snowflake",
            )
        except OAuthError:
            return ServiceHealth(
                service="snowflake",
                status="disconnected",
                message="OAuth token expired or not authorized",
                details=ServiceHealthDetails(error_code="TOKEN_EXPIRED"),
                last_checked=datetime.now(timezone.utc),
            )
    else:
        username = config.get("username")
        password = config.get("password")
        if not username:
            return ServiceHealth(
                service="snowflake",
                status="not_configured",
                message="Username is required for basic authentication",
                last_checked=datetime.now(timezone.utc),
            )

    # Run the test in a thread pool since it's blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: test_snowflake_connection(
            account_identifier=account_identifier,
            warehouse=warehouse,
            database=database,
            schema=schema,
            auth_method=auth_method,
            username=username,
            password=password,
            oauth_token=oauth_token,
            timeout=SERVICE_TIMEOUT,
        ),
    )

    if result.success:
        return ServiceHealth(
            service="snowflake",
            status="connected",
            message=result.message,
            details=ServiceHealthDetails(
                response_time_ms=result.response_time_ms,
            ),
            last_checked=datetime.now(timezone.utc),
        )
    else:
        return ServiceHealth(
            service="snowflake",
            status="disconnected",
            message=result.message,
            details=ServiceHealthDetails(
                response_time_ms=result.response_time_ms,
                error_code=result.error_code.value if result.error_code else None,
            ),
            last_checked=datetime.now(timezone.utc),
        )


async def _check_ollama_health(db: Session) -> ServiceHealth:
    """Check Ollama service health including circuit breaker status."""
    try:
        config = get_connection_config(db, "ollama", decrypt=False)
    except ConnectionConfigError as e:
        logger.warning("Failed to get Ollama config for health check: %s", e.message)
        config = None

    # Default config if not set
    host_url = "http://localhost:11434"
    model_name = "codellama:13b"
    enabled = False

    if config:
        host_url = config.get("host_url", host_url)
        model_name = config.get("model_name", model_name)
        enabled = config.get("enabled", False)

    if not enabled:
        return ServiceHealth(
            service="ollama",
            status="not_configured",
            message="Ollama AI features are disabled",
            last_checked=datetime.now(timezone.utc),
        )

    # Use async health check
    result = await check_ollama_health_async(
        host_url=host_url,
        model_name=model_name,
        enabled=enabled,
        timeout=SERVICE_TIMEOUT,
    )

    # Get circuit breaker status from the client
    ollama_config = OllamaConfig(
        host_url=host_url,
        model=model_name,
        enabled=enabled,
    )
    client = get_ollama_client(ollama_config)
    circuit_status = client.get_circuit_breaker_status()

    if result.success:
        return ServiceHealth(
            service="ollama",
            status="connected",
            message=result.message,
            details=ServiceHealthDetails(
                response_time_ms=result.response_time_ms,
                extra_info={
                    "model": model_name,
                    "available_models": result.models_found,
                    "circuit_breaker": circuit_status["state"],
                },
            ),
            last_checked=datetime.now(timezone.utc),
        )
    else:
        # Treat disabled as not_configured
        status = "not_configured" if result.error_code == OllamaErrorCode.DISABLED else "disconnected"

        # Include circuit breaker info in error case
        extra_info = {"circuit_breaker": circuit_status["state"]}
        if circuit_status["state"] == "open":
            extra_info["circuit_failure_count"] = circuit_status["failure_count"]

        return ServiceHealth(
            service="ollama",
            status=status,
            message=result.message,
            details=ServiceHealthDetails(
                response_time_ms=result.response_time_ms,
                error_code=result.error_code.value if result.error_code else None,
                extra_info=extra_info,
            ),
            last_checked=datetime.now(timezone.utc),
        )


def _calculate_overall_status(services: list[ServiceHealth]) -> str:
    """Calculate overall system health status.

    - healthy: All configured services are connected
    - degraded: Some services disconnected or not configured
    - unhealthy: All services disconnected
    """
    configured_services = [s for s in services if s.status != "not_configured"]
    connected_services = [s for s in services if s.status == "connected"]

    if not configured_services:
        # No services configured - consider this as healthy (fresh install)
        return "healthy"

    if len(connected_services) == len(configured_services):
        return "healthy"
    elif len(connected_services) == 0:
        return "unhealthy"
    else:
        return "degraded"


@router.get(
    "/health/services",
    response_model=HealthResponse,
    summary="Check all services health",
)
async def get_services_health(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HealthResponse:
    """Check health of all configured services.

    Runs health checks in parallel with 10 second timeout per service.
    Total timeout: 30 seconds.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        HealthResponse with status for all services
    """
    logger.info("Services health check requested by user: %s", current_user.identity)

    # Run all health checks in parallel
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                _check_ssrs_health(db),
                _check_snowflake_health(db, current_user.user_id),
                _check_ollama_health(db),
                return_exceptions=True,
            ),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.error("Services health check timed out")
        results = [
            ServiceHealth(
                service="ssrs",
                status="disconnected",
                message="Health check timed out",
                last_checked=datetime.now(timezone.utc),
            ),
            ServiceHealth(
                service="snowflake",
                status="disconnected",
                message="Health check timed out",
                last_checked=datetime.now(timezone.utc),
            ),
            ServiceHealth(
                service="ollama",
                status="disconnected",
                message="Health check timed out",
                last_checked=datetime.now(timezone.utc),
            ),
        ]

    # Handle any exceptions from individual checks
    services = []
    service_names = ["ssrs", "snowflake", "ollama"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Health check failed for %s: %s", service_names[i], result)
            services.append(
                ServiceHealth(
                    service=service_names[i],
                    status="disconnected",
                    message=f"Health check failed: {str(result)}",
                    last_checked=datetime.now(timezone.utc),
                )
            )
        else:
            services.append(result)

    overall_status = _calculate_overall_status(services)

    return HealthResponse(
        services=services,
        overall_status=overall_status,
        checked_at=datetime.now(timezone.utc),
    )


@router.get(
    "/health/ai",
    response_model=AIStatusResponse,
    summary="Check AI service status",
)
async def get_ai_status(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> AIStatusResponse:
    """Get detailed AI (Ollama) service status.

    Returns availability status, consecutive failures, circuit breaker state,
    and status message for display in the UI.

    Args:
        current_user: Current authenticated user

    Returns:
        AIStatusResponse with detailed AI status
    """
    fallback_service = get_ai_fallback_service()

    # Check availability (uses cached status if recent)
    await fallback_service.is_ai_available()

    return fallback_service.get_status()


@router.get(
    "/health/ai/methods",
    response_model=ConversionMethodBreakdown,
    summary="Get conversion method breakdown",
)
async def get_conversion_method_breakdown(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> ConversionMethodBreakdown:
    """Get breakdown of conversion methods used in current session.

    Returns counts for rule-based, AI-assisted, AI-fallback, and manual conversions.

    Args:
        current_user: Current authenticated user

    Returns:
        ConversionMethodBreakdown with counts
    """
    fallback_service = get_ai_fallback_service()
    return fallback_service.get_method_breakdown()

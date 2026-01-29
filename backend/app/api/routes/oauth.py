"""OAuth API routes for Snowflake SSO authentication."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.schemas.auth import UserInfo
from app.schemas.oauth import (
    OAuthAuthorizeResponse,
    OAuthError,
    OAuthErrorDetail,
    OAuthStatus,
)
from app.services.oauth_service import OAuthService, OAuthError as OAuthServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/snowflake", tags=["oauth"])


def _handle_oauth_error(e: OAuthServiceError) -> HTTPException:
    """Convert OAuthServiceError to HTTPException."""
    status_code = status.HTTP_400_BAD_REQUEST

    if e.code == "OAUTH_NOT_CONFIGURED":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif e.code in ("OAUTH_INVALID_STATE", "OAUTH_NO_TOKEN"):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif e.code in ("OAUTH_TOKEN_EXCHANGE_FAILED", "OAUTH_REFRESH_FAILED"):
        status_code = status.HTTP_502_BAD_GATEWAY

    return HTTPException(
        status_code=status_code,
        detail={"code": e.code, "message": e.message},
    )


@router.get(
    "/authorize",
    response_model=OAuthAuthorizeResponse,
    responses={
        503: {"description": "OAuth not configured", "model": OAuthError},
    },
)
async def authorize(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo | None, Depends(get_current_user_optional)] = None,
    redirect_after: str = Query(default="/", description="URL to redirect to after authentication"),
) -> OAuthAuthorizeResponse:
    """Initiate Snowflake OAuth flow.

    Generates PKCE parameters and returns the authorization URL to redirect to.
    If the user is authenticated, their user ID is associated with the OAuth session.

    Args:
        db: Database session
        current_user: Optional current user (from JWT)
        redirect_after: URL to redirect to after successful authentication

    Returns:
        OAuthAuthorizeResponse with authorization URL and state parameter

    Raises:
        HTTPException: If OAuth is not configured
    """
    try:
        oauth_service = OAuthService(db)

        # Get user ID if authenticated (for token association)
        user_id = None
        if current_user:
            # In a real app, we'd look up the user record by identity
            # For now, we'll pass None and handle user lookup in callback
            pass

        response = oauth_service.initiate_oauth_flow(
            user_id=user_id,
            redirect_after=redirect_after,
        )

        logger.info("OAuth authorization initiated, state=%s", response.state[:8])
        return response

    except OAuthServiceError as e:
        raise _handle_oauth_error(e)


@router.get(
    "/callback",
    responses={
        302: {"description": "Redirect to application after OAuth"},
        400: {"description": "OAuth error", "model": OAuthError},
        401: {"description": "Invalid state", "model": OAuthError},
    },
)
async def callback(
    db: Annotated[Session, Depends(get_db)],
    code: str = Query(default="", description="Authorization code from IdP"),
    state: str = Query(..., description="State parameter for verification"),
    error: str | None = Query(default=None, description="Error code from IdP"),
    error_description: str | None = Query(default=None, description="Error description from IdP"),
) -> RedirectResponse:
    """Handle OAuth callback from IdP.

    Exchanges the authorization code for tokens and redirects to the application.

    Args:
        db: Database session
        code: Authorization code from IdP
        state: State parameter for CSRF verification
        error: Error code if authentication failed
        error_description: Human-readable error description

    Returns:
        Redirect to the application with success or error parameters

    Raises:
        HTTPException: If callback processing fails
    """
    try:
        oauth_service = OAuthService(db)

        tokens, redirect_after = await oauth_service.handle_callback(
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )

        # Redirect with success parameter
        redirect_url = f"{redirect_after}?oauth=success&service=snowflake"
        logger.info("OAuth callback successful, redirecting to %s", redirect_after)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except OAuthServiceError as e:
        logger.warning("OAuth callback failed: %s - %s", e.code, e.message)
        # Redirect with error parameters for frontend handling
        redirect_url = f"/oauth-error?code={e.code}&message={e.message}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/status",
    response_model=OAuthStatus,
)
async def get_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> OAuthStatus:
    """Check Snowflake OAuth authentication status.

    Returns whether the current user has valid OAuth tokens for Snowflake.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        OAuthStatus with authentication status and configuration status
    """
    oauth_service = OAuthService(db)

    # In a real app, we'd look up user ID from identity
    # For now, return unconfigured status for the demo
    user_id = 0  # Placeholder - would come from user lookup

    status_response = oauth_service.get_status(user_id=user_id, service_type="snowflake")

    logger.debug(
        "OAuth status check: authenticated=%s, configured=%s",
        status_response.authenticated,
        status_response.configured,
    )

    return status_response


@router.post(
    "/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def revoke(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> None:
    """Revoke Snowflake OAuth tokens.

    Deletes stored OAuth tokens for the current user.

    Args:
        db: Database session
        current_user: Current authenticated user
    """
    oauth_service = OAuthService(db)

    # In a real app, we'd look up user ID from identity
    user_id = 0  # Placeholder - would come from user lookup

    await oauth_service.revoke_tokens(user_id=user_id, service_type="snowflake")

    logger.info("OAuth tokens revoked for user %s", current_user.identity)
    return None


@router.post(
    "/refresh",
    response_model=OAuthStatus,
    responses={
        401: {"description": "Not authenticated or no refresh token"},
        502: {"description": "Token refresh failed"},
    },
)
async def refresh_token(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> OAuthStatus:
    """Manually refresh Snowflake OAuth tokens.

    Attempts to refresh the access token using the stored refresh token.
    Typically, token refresh happens automatically when accessing Snowflake.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated OAuthStatus after refresh

    Raises:
        HTTPException: If refresh fails
    """
    try:
        oauth_service = OAuthService(db)

        # In a real app, we'd look up user ID from identity
        user_id = 0  # Placeholder - would come from user lookup

        await oauth_service.refresh_tokens(user_id=user_id, service_type="snowflake")

        # Return updated status
        return oauth_service.get_status(user_id=user_id, service_type="snowflake")

    except OAuthServiceError as e:
        raise _handle_oauth_error(e)

"""Authentication API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginRequest,
    AuthResponse,
    TokenResponse,
    UserInfo,
    CurrentUserResponse,
)
from app.services.ad_auth import ad_auth_service, ADAuthError
from app.core.security import (
    create_access_token,
    get_token_expiration_seconds,
)
from app.core.middleware import get_client_ip, get_user_agent
from app.api.deps import get_current_user, get_db
from app.models.audit_log import EventType, AuditStatus
from app.models.user import User
from app.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        401: {"description": "Invalid credentials"},
        503: {"description": "Domain controller unavailable"},
    },
)
async def login(
    login_request: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Authenticate user with Windows/AD credentials.

    Args:
        login_request: Login request containing username, password, and domain
        request: HTTP request for extracting IP and user agent
        db: Database session for audit logging

    Returns:
        AuthResponse with JWT token and user info

    Raises:
        HTTPException: If authentication fails
    """
    audit_service = get_audit_service()
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    try:
        # Authenticate against AD
        identity = ad_auth_service.authenticate(
            username=login_request.username,
            password=login_request.password,
            domain=login_request.domain,
        )

        # Create JWT token
        access_token = create_access_token(
            subject=identity.full_identity,
            domain=identity.domain,
            username=identity.username,
        )

        # Log successful login (non-blocking - don't fail if audit logging fails)
        try:
            user = db.query(User).filter(User.full_identity == identity.full_identity).first()
            user_id = user.id if user else None

            audit_service.log_login(
                db=db,
                username=identity.full_identity,
                success=True,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={
                    "domain": identity.domain,
                    "auth_method": "NTLM",
                },
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log login audit event: {audit_error}")

        # Build response
        user_info = UserInfo(
            identity=identity.full_identity,
            username=identity.username,
            domain=identity.domain,
        )

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiration_seconds(),
            user=user_info,
        )

        logger.info(f"User logged in: {identity.full_identity}")
        return AuthResponse(data=token_response)

    except ADAuthError as e:
        # Log failed login attempt (non-blocking)
        try:
            audit_service.log_login(
                db=db,
                username=f"{login_request.domain}\\{login_request.username}" if login_request.domain else login_request.username,
                success=False,
                user_id=None,
                ip_address=client_ip,
                user_agent=user_agent,
                details={
                    "reason": e.code,
                    "domain": login_request.domain,
                },
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log login failure audit event: {audit_error}")

        logger.warning(f"Authentication failed: {e.code} - {e.message}")
        if e.code in ("AUTH_DC_UNAVAILABLE", "AUTH_DC_TIMEOUT"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": e.code, "message": e.message},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> None:
    """Logout the current user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by clearing the stored token. This endpoint is provided for
    consistency and potential future server-side token invalidation.

    Args:
        request: HTTP request for extracting IP and user agent
        db: Database session for audit logging
        current_user: The authenticated user (validates token)
    """
    # Log logout event (non-blocking - don't fail if audit logging fails)
    try:
        audit_service = get_audit_service()
        client_ip = get_client_ip(request)

        user = db.query(User).filter(User.full_identity == current_user.identity).first()
        user_id = user.id if user else None

        audit_service.log_logout(
            db=db,
            username=current_user.identity,
            user_id=user_id,
            ip_address=client_ip,
        )
    except Exception as audit_error:
        logger.warning(f"Failed to log logout audit event: {audit_error}")

    logger.info(f"User logged out: {current_user.identity}")
    # JWT logout is handled client-side by clearing the token
    # Future: Could add token to a blacklist if needed
    return None


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Get the current authenticated user's information.

    Args:
        current_user: The authenticated user from the JWT token

    Returns:
        CurrentUserResponse with user information
    """
    return CurrentUserResponse(user=current_user)

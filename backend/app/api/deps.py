"""Common API dependencies."""

import logging
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.schemas.auth import UserInfo
from app.core.security import decode_access_token, decode_token_unsafe, TokenError

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _log_session_expiry(token: str, request: Request | None = None) -> None:
    """Log a session expiry event.

    Attempts to extract user info from the expired token for logging.
    Uses a separate db session to avoid blocking the main request.

    Args:
        token: The expired JWT token
        request: Optional request for extracting IP/user agent
    """
    try:
        # Import here to avoid circular imports
        from app.core.middleware import get_client_ip, get_user_agent
        from app.models.audit_log import EventType, AuditStatus
        from app.models.user import User
        from app.services.audit_service import get_audit_service

        # Try to extract user info from the expired token
        payload = decode_token_unsafe(token)
        if not payload:
            return

        username = payload.get("sub", "unknown")
        token_issued_at = payload.get("iat")
        token_expired_at = payload.get("exp")

        # Create a new db session for logging
        db = SessionLocal()
        try:
            # Try to get user ID
            user = db.query(User).filter(User.full_identity == username).first()
            user_id = user.id if user else None

            # Get request context if available
            ip_address = get_client_ip(request) if request else None
            user_agent = get_user_agent(request) if request else None

            # Log the session expiry
            audit_service = get_audit_service()
            audit_service.log_event_sync(
                db=db,
                event_type=EventType.LOGOUT,
                action="Session expired",
                status=AuditStatus.SUCCESS,
                user_id=user_id,
                username=username,
                details={
                    "expiry_reason": "timeout",
                    "token_issued_at": token_issued_at,
                    "token_expired_at": token_expired_at,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
        finally:
            db.close()

    except Exception as e:
        # Don't let audit logging errors affect the main request
        logger.warning(f"Failed to log session expiry: {e}")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserInfo:
    """Dependency to get the current authenticated user from JWT token.

    Args:
        request: HTTP request for session expiry logging
        credentials: HTTP Authorization credentials (Bearer token)

    Returns:
        UserInfo for the authenticated user

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)

        # Extract user info from token claims
        return UserInfo(
            identity=payload.get("sub", ""),
            username=payload.get("username", ""),
            domain=payload.get("domain", ""),
        )
    except TokenError as e:
        # Log session expiry for expired tokens
        if e.code == "AUTH_TOKEN_EXPIRED":
            _log_session_expiry(credentials.credentials, request)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserInfo | None:
    """Dependency to optionally get the current user.

    Returns None if no token is provided, but validates token if present.

    Args:
        request: HTTP request for session expiry logging
        credentials: HTTP Authorization credentials (Bearer token)

    Returns:
        UserInfo for the authenticated user, or None if not authenticated

    Raises:
        HTTPException: If token is present but invalid or expired
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        return UserInfo(
            identity=payload.get("sub", ""),
            username=payload.get("username", ""),
            domain=payload.get("domain", ""),
        )
    except TokenError as e:
        # Log session expiry for expired tokens
        if e.code == "AUTH_TOKEN_EXPIRED":
            _log_session_expiry(credentials.credentials, request)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

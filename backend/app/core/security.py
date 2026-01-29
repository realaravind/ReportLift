"""JWT token utilities for authentication."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


class TokenError(Exception):
    """Exception raised for token-related errors."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def create_access_token(
    subject: str,
    domain: str,
    username: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject of the token (typically DOMAIN\\username)
        domain: The AD domain
        username: The username without domain
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.jwt_expiration_hours
        )

    to_encode: dict[str, Any] = {
        "sub": subject,
        "domain": domain,
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary containing the token claims

    Raises:
        TokenError: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenError("AUTH_TOKEN_EXPIRED", "Token has expired")
        raise TokenError("AUTH_TOKEN_INVALID", "Invalid or malformed token")


def get_token_expiration_seconds() -> int:
    """Get the token expiration time in seconds."""
    return settings.jwt_expiration_hours * 3600


def decode_token_unsafe(token: str) -> dict[str, Any] | None:
    """Decode a JWT token without validating expiration.

    Used for logging purposes when we need to extract user info
    from an expired token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary containing the token claims, or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},  # Don't validate expiration
        )
        return payload
    except JWTError:
        return None

"""Authentication request and response schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., min_length=1, description="Windows username")
    password: str = Field(..., min_length=1, description="Windows password")
    domain: str = Field(..., min_length=1, description="Active Directory domain")


class UserInfo(BaseModel):
    """Schema for user information."""

    identity: str = Field(..., description="Full identity (DOMAIN\\username)")
    username: str = Field(..., description="Username without domain")
    domain: str = Field(..., description="AD domain")


class TokenResponse(BaseModel):
    """Schema for successful authentication response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserInfo = Field(..., description="Authenticated user information")


class AuthResponse(BaseModel):
    """Wrapper for authentication response."""

    data: TokenResponse


class AuthErrorDetail(BaseModel):
    """Schema for authentication error details."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


class AuthError(BaseModel):
    """Schema for authentication error response."""

    error: AuthErrorDetail


class CurrentUserResponse(BaseModel):
    """Schema for /auth/me endpoint response."""

    user: UserInfo

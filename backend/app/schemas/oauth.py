"""OAuth request and response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class OAuthConfig(BaseModel):
    """Schema for OAuth configuration."""

    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(default="", description="OAuth client secret (optional for PKCE)")
    auth_url: str = Field(..., description="Authorization endpoint URL")
    token_url: str = Field(..., description="Token endpoint URL")
    redirect_uri: str = Field(..., description="OAuth callback redirect URI")
    scope: str = Field(default="openid profile", description="OAuth scopes")


class OAuthState(BaseModel):
    """Schema for OAuth state tracking (CSRF protection + PKCE)."""

    state: str = Field(..., description="Random state parameter for CSRF protection")
    code_verifier: str = Field(..., description="PKCE code verifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    redirect_after: str = Field(default="/", description="URL to redirect to after auth")
    user_id: int | None = Field(default=None, description="Associated user ID if authenticated")


class OAuthAuthorizeResponse(BaseModel):
    """Schema for authorization URL response."""

    auth_url: str = Field(..., description="Full authorization URL to redirect to")
    state: str = Field(..., description="State parameter for verification")


class OAuthTokenResponse(BaseModel):
    """Schema for OAuth token response from IdP."""

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str | None = Field(default=None, description="Granted scopes")


class OAuthStatus(BaseModel):
    """Schema for OAuth status check response."""

    authenticated: bool = Field(..., description="Whether OAuth is authenticated")
    service: str = Field(..., description="Service name (e.g., 'snowflake')")
    expires_at: datetime | None = Field(default=None, description="Token expiration time")
    configured: bool = Field(..., description="Whether OAuth is configured")


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback parameters."""

    code: str = Field(..., description="Authorization code from IdP")
    state: str = Field(..., description="State parameter for verification")
    error: str | None = Field(default=None, description="Error code if authentication failed")
    error_description: str | None = Field(default=None, description="Error description")


class OAuthErrorDetail(BaseModel):
    """Schema for OAuth error details."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


class OAuthError(BaseModel):
    """Schema for OAuth error response."""

    error: OAuthErrorDetail

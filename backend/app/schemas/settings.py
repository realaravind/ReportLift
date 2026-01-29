"""Settings API request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
import re


class SSRSSettingsResponse(BaseModel):
    """Schema for SSRS connection settings (masked)."""

    report_server_url: str | None = Field(default=None, description="SSRS Report Server URL")
    auth_method: str = Field(default="windows_integrated", description="Authentication method")
    service_account_username: str | None = Field(default=None, description="Service account username")
    has_credentials: bool = Field(default=False, description="Whether password is configured")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class SSRSSettingsUpdateRequest(BaseModel):
    """Schema for updating SSRS settings."""

    report_server_url: str = Field(..., min_length=1, description="SSRS Report Server URL")
    auth_method: str = Field(default="windows_integrated", description="Authentication method")
    service_account_username: str | None = Field(default=None, description="Service account username")
    service_account_password: str | None = Field(default=None, description="Service account password (only sent when updating)")

    @field_validator("report_server_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the URL is a valid HTTP/HTTPS URL."""
        if not v:
            raise ValueError("Report Server URL is required")

        # Check URL format
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v, re.IGNORECASE):
            raise ValueError("Invalid Report Server URL format. Must start with http:// or https://")

        return v.strip()

    @field_validator("auth_method")
    @classmethod
    def validate_auth_method(cls, v: str) -> str:
        """Validate authentication method."""
        valid_methods = ["windows_integrated"]
        if v not in valid_methods:
            raise ValueError(f"Invalid auth method. Must be one of: {', '.join(valid_methods)}")
        return v


class SnowflakeSettingsResponse(BaseModel):
    """Schema for Snowflake connection settings (masked)."""

    account_identifier: str | None = Field(default=None, description="Snowflake account identifier")
    warehouse: str | None = Field(default=None, description="Default warehouse")
    database: str | None = Field(default=None, description="Default database")
    schema_name: str | None = Field(default=None, description="Default schema")
    auth_method: str = Field(default="oauth", description="Authentication method (oauth, basic)")
    # OAuth fields
    has_oauth_config: bool = Field(default=False, description="Whether OAuth is configured in env")
    oauth_status: str = Field(default="not_authorized", description="OAuth status (authorized, not_authorized, expired)")
    # Basic auth fields
    username: str | None = Field(default=None, description="Basic auth username")
    has_password: bool = Field(default=False, description="Whether password is configured")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class SnowflakeSettingsUpdateRequest(BaseModel):
    """Schema for updating Snowflake settings."""

    account_identifier: str = Field(..., min_length=1, description="Snowflake account identifier")
    warehouse: str = Field(..., min_length=1, description="Default warehouse")
    database: str = Field(..., min_length=1, description="Default database")
    schema_name: str = Field(..., min_length=1, description="Default schema")
    auth_method: str = Field(default="oauth", description="Authentication method (oauth, basic)")
    # Basic auth fields (only used when auth_method is basic)
    username: str | None = Field(default=None, description="Basic auth username")
    password: str | None = Field(default=None, description="Basic auth password (only sent when updating)")

    @field_validator("account_identifier")
    @classmethod
    def validate_account_identifier(cls, v: str) -> str:
        """Validate account identifier format."""
        if not v:
            raise ValueError("Account identifier is required")
        # Basic format check: alphanumeric with dots and hyphens
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$"
        if not re.match(pattern, v):
            raise ValueError("Invalid account identifier format")
        return v.strip()

    @field_validator("auth_method")
    @classmethod
    def validate_auth_method(cls, v: str) -> str:
        """Validate authentication method."""
        valid_methods = ["oauth", "basic"]
        if v not in valid_methods:
            raise ValueError(f"Invalid auth method. Must be one of: {', '.join(valid_methods)}")
        return v


class OllamaSettingsResponse(BaseModel):
    """Schema for Ollama AI service settings."""

    host_url: str = Field(default="http://localhost:11434", description="Ollama service URL")
    model_name: str = Field(default="codellama:13b", description="Model to use for AI features")
    enabled: bool = Field(default=False, description="Whether AI features are enabled")
    timeout_seconds: int = Field(default=60, description="Request timeout in seconds")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class OllamaSettingsUpdateRequest(BaseModel):
    """Schema for updating Ollama settings."""

    host_url: str = Field(default="http://localhost:11434", description="Ollama service URL")
    model_name: str = Field(default="codellama:13b", min_length=1, description="Model to use for AI features")
    enabled: bool = Field(default=False, description="Whether AI features are enabled")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds (1-300)")

    @field_validator("host_url")
    @classmethod
    def validate_host_url(cls, v: str) -> str:
        """Validate that the URL is a valid HTTP/HTTPS URL."""
        if not v:
            raise ValueError("Ollama host URL is required")

        # Check URL format
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v, re.IGNORECASE):
            raise ValueError("Invalid Ollama host URL. Must start with http:// or https://")

        return v.strip()


class SystemSettingsResponse(BaseModel):
    """Schema for system settings."""

    environment: str = Field(description="Current environment (development, production)")
    version: str = Field(description="Application version")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")


class AllSettingsResponse(BaseModel):
    """Schema for all settings combined response."""

    ssrs: SSRSSettingsResponse
    snowflake: SnowflakeSettingsResponse
    ollama: OllamaSettingsResponse
    system: SystemSettingsResponse


class SettingsUpdateRequest(BaseModel):
    """Base schema for settings update requests.

    Note: Individual settings update schemas will be defined
    in their respective story implementations.
    """

    pass


class SSRSTestResultDetails(BaseModel):
    """Details of the SSRS connection test."""

    server_version: str | None = Field(default=None, description="SSRS server version")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    root_folder_accessible: bool = Field(default=False, description="Whether root folder is accessible")
    error_code: str | None = Field(default=None, description="Error code if test failed")


class SSRSTestResultResponse(BaseModel):
    """Response schema for SSRS connection test."""

    success: bool = Field(description="Whether the connection test succeeded")
    message: str = Field(description="Human-readable result message")
    details: SSRSTestResultDetails = Field(description="Detailed test results")
    suggestions: list[str] | None = Field(default=None, description="Troubleshooting suggestions if failed")
    tested_at: datetime = Field(description="Timestamp of the test")


class SnowflakeTestResultDetails(BaseModel):
    """Details of the Snowflake connection test."""

    account: str | None = Field(default=None, description="Snowflake account")
    warehouse: str | None = Field(default=None, description="Active warehouse")
    database: str | None = Field(default=None, description="Active database")
    schema: str | None = Field(default=None, description="Active schema")
    role: str | None = Field(default=None, description="Active role")
    user: str | None = Field(default=None, description="Authenticated user")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    error_code: str | None = Field(default=None, description="Error code if test failed")
    snowflake_error_code: int | None = Field(default=None, description="Snowflake SQL error code if available")


class SnowflakeTestResultResponse(BaseModel):
    """Response schema for Snowflake connection test."""

    success: bool = Field(description="Whether the connection test succeeded")
    message: str = Field(description="Human-readable result message")
    details: SnowflakeTestResultDetails = Field(description="Detailed test results")
    suggestions: list[str] | None = Field(default=None, description="Troubleshooting suggestions if failed")
    requires_reauth: bool = Field(default=False, description="Whether OAuth re-authorization is required")
    tested_at: datetime = Field(description="Timestamp of the test")


# Health check schemas
class ServiceHealthDetails(BaseModel):
    """Details for a service health check."""

    version: str | None = Field(default=None, description="Service version if available")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    error_code: str | None = Field(default=None, description="Error code if unhealthy")
    extra_info: dict[str, Any] | None = Field(default=None, description="Additional service-specific info")


class ServiceHealth(BaseModel):
    """Health status for a single service."""

    service: str = Field(description="Service name (ssrs, snowflake, ollama)")
    status: str = Field(description="Status: connected, disconnected, not_configured, checking")
    message: str | None = Field(default=None, description="Status message")
    details: ServiceHealthDetails | None = Field(default=None, description="Additional details")
    last_checked: datetime | None = Field(default=None, description="When the health was last checked")


class HealthResponse(BaseModel):
    """Response schema for all services health check."""

    services: list[ServiceHealth] = Field(description="Health status of each service")
    overall_status: str = Field(description="Overall status: healthy, degraded, unhealthy")
    checked_at: datetime = Field(description="Timestamp of the health check")

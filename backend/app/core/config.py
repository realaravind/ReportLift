"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite:///./test.db"

    # Security
    secret_key: str = "development-secret-key-change-in-production"

    # JWT Configuration
    jwt_secret_key: str = "jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 8

    # AD Configuration (optional - for DC lookup)
    ad_domain_controller: str = ""

    # Credential Encryption
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # In production, this MUST be set via environment variable
    encryption_key: str = ""

    # TLS Configuration (for production HTTPS)
    tls_cert_path: str = "/etc/nginx/certs/cert.pem"
    tls_key_path: str = "/etc/nginx/certs/key.pem"

    # Snowflake OAuth Configuration
    # These can be left empty if Snowflake OAuth is not configured
    snowflake_oauth_client_id: str = ""
    snowflake_oauth_client_secret: str = ""
    snowflake_oauth_auth_url: str = ""
    snowflake_oauth_token_url: str = ""
    snowflake_oauth_redirect_uri: str = ""
    snowflake_oauth_scope: str = "openid profile"

    # Environment
    environment: str = "development"

    # Logging
    log_level: str = "INFO"

    # Application
    app_name: str = "ReportLift"
    app_version: str = "1.0.0"

    # AI Conversion Confidence Thresholds
    # High confidence >= 80%, Medium >= 50%, Low < 50%
    confidence_high_threshold: float = 0.80
    confidence_medium_threshold: float = 0.50
    # Uncertain flag is set for low and medium confidence conversions
    flag_uncertain_for_low: bool = True
    flag_uncertain_for_medium: bool = True


# Global settings instance
settings = Settings()

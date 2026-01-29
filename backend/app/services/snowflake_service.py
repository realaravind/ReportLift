"""Snowflake Service for connection testing and operations.

This service handles Snowflake database connections, including:
- Connection testing with OAuth or basic authentication
- Error handling and categorization
- Connection metadata retrieval
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Default timeout for connection attempts (seconds)
DEFAULT_TIMEOUT = 15


class SnowflakeErrorCode(Enum):
    """Categorized error codes for Snowflake connection issues."""

    AUTH_FAILED = "AUTH_FAILED"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    WAREHOUSE_NOT_FOUND = "WAREHOUSE_NOT_FOUND"
    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    SCHEMA_NOT_FOUND = "SCHEMA_NOT_FOUND"
    ROLE_NOT_AUTHORIZED = "ROLE_NOT_AUTHORIZED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Map Snowflake SQL error codes to our error codes
SNOWFLAKE_ERROR_MAP = {
    250001: SnowflakeErrorCode.AUTH_FAILED,
    390100: SnowflakeErrorCode.ACCOUNT_NOT_FOUND,
    390201: SnowflakeErrorCode.WAREHOUSE_NOT_FOUND,
    390202: SnowflakeErrorCode.DATABASE_NOT_FOUND,
    390203: SnowflakeErrorCode.SCHEMA_NOT_FOUND,
    390318: SnowflakeErrorCode.ROLE_NOT_AUTHORIZED,
}

# User-friendly error messages
ERROR_MESSAGES = {
    SnowflakeErrorCode.AUTH_FAILED: "Authentication failed. Check your credentials or re-authorize OAuth.",
    SnowflakeErrorCode.ACCOUNT_NOT_FOUND: "Account not found. Verify your Account Identifier format.",
    SnowflakeErrorCode.WAREHOUSE_NOT_FOUND: "Warehouse not found or you don't have access.",
    SnowflakeErrorCode.DATABASE_NOT_FOUND: "Database not found or you don't have access.",
    SnowflakeErrorCode.SCHEMA_NOT_FOUND: "Schema not found or you don't have access.",
    SnowflakeErrorCode.ROLE_NOT_AUTHORIZED: "You don't have permission to use this role.",
    SnowflakeErrorCode.CONNECTION_TIMEOUT: "Connection timed out. Check network connectivity.",
    SnowflakeErrorCode.CONNECTION_ERROR: "Unable to connect to Snowflake server.",
    SnowflakeErrorCode.TOKEN_EXPIRED: "OAuth token has expired. Please re-authorize.",
    SnowflakeErrorCode.UNKNOWN_ERROR: "An unexpected error occurred.",
}

# Troubleshooting suggestions
ERROR_SUGGESTIONS = {
    SnowflakeErrorCode.AUTH_FAILED: [
        "Verify your username and password are correct",
        "If using OAuth, try re-authorizing your connection",
        "Check that your account is not locked",
    ],
    SnowflakeErrorCode.ACCOUNT_NOT_FOUND: [
        "Verify the Account Identifier format (e.g., orgname-account_name)",
        "Check for typos in the account name",
        "Ensure you're using the correct region suffix if required",
    ],
    SnowflakeErrorCode.WAREHOUSE_NOT_FOUND: [
        "Verify the warehouse name is spelled correctly",
        "Check that you have USAGE privilege on the warehouse",
        "Ensure the warehouse exists in your account",
    ],
    SnowflakeErrorCode.DATABASE_NOT_FOUND: [
        "Verify the database name is spelled correctly",
        "Check that you have USAGE privilege on the database",
        "Ensure the database exists in your account",
    ],
    SnowflakeErrorCode.SCHEMA_NOT_FOUND: [
        "Verify the schema name is spelled correctly",
        "Check that you have USAGE privilege on the schema",
        "Ensure the schema exists in the database",
    ],
    SnowflakeErrorCode.ROLE_NOT_AUTHORIZED: [
        "Check that your user has the required role assigned",
        "Contact your Snowflake administrator for role access",
    ],
    SnowflakeErrorCode.CONNECTION_TIMEOUT: [
        "Check your network connectivity",
        "Verify firewall rules allow connections to Snowflake",
        "Try again in a few moments",
    ],
    SnowflakeErrorCode.CONNECTION_ERROR: [
        "Check your internet connection",
        "Verify the Account Identifier is correct",
        "Ensure Snowflake is accessible from your network",
    ],
    SnowflakeErrorCode.TOKEN_EXPIRED: [
        "Click 'Connect with SSO' to re-authorize",
        "Your OAuth session has expired",
    ],
    SnowflakeErrorCode.UNKNOWN_ERROR: [
        "Check the Snowflake error message for details",
        "Try the connection again",
        "Contact support if the issue persists",
    ],
}


@dataclass
class SnowflakeTestResult:
    """Result of a Snowflake connection test."""

    success: bool
    message: str
    user: str | None = None
    role: str | None = None
    warehouse: str | None = None
    database: str | None = None
    schema: str | None = None
    account: str | None = None
    response_time_ms: int = 0
    error_code: SnowflakeErrorCode | None = None
    snowflake_error_code: int | None = None
    suggestions: list[str] = field(default_factory=list)
    requires_reauth: bool = False


def test_snowflake_connection(
    account_identifier: str,
    warehouse: str,
    database: str,
    schema: str,
    auth_method: str = "oauth",
    username: str | None = None,
    password: str | None = None,
    oauth_token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SnowflakeTestResult:
    """Test Snowflake connection using provided configuration.

    Args:
        account_identifier: Snowflake account identifier
        warehouse: Warehouse name
        database: Database name
        schema: Schema name
        auth_method: Authentication method ('oauth' or 'basic')
        username: Username for basic auth
        password: Password for basic auth
        oauth_token: OAuth access token for OAuth auth
        timeout: Connection timeout in seconds

    Returns:
        SnowflakeTestResult with connection details or error information
    """
    start_time = time.time()

    try:
        # Import here to avoid import errors if package not installed
        import snowflake.connector
        from snowflake.connector.errors import DatabaseError, ProgrammingError

        # Build connection parameters
        conn_params: dict[str, Any] = {
            "account": account_identifier,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "login_timeout": timeout,
            "network_timeout": timeout,
        }

        if auth_method == "oauth" and oauth_token:
            conn_params["authenticator"] = "oauth"
            conn_params["token"] = oauth_token
        elif auth_method == "basic" and username:
            conn_params["user"] = username
            if password:
                conn_params["password"] = password
        else:
            return SnowflakeTestResult(
                success=False,
                message="Invalid authentication configuration",
                response_time_ms=int((time.time() - start_time) * 1000),
                error_code=SnowflakeErrorCode.AUTH_FAILED,
                suggestions=["Configure OAuth or provide username/password"],
            )

        logger.info(
            "Testing Snowflake connection to %s (auth: %s)",
            account_identifier,
            auth_method,
        )

        # Attempt connection
        conn = snowflake.connector.connect(**conn_params)

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT CURRENT_USER(), CURRENT_ROLE(),
                       CURRENT_WAREHOUSE(), CURRENT_DATABASE(),
                       CURRENT_SCHEMA(), CURRENT_ACCOUNT()
            """)
            result = cursor.fetchone()

            response_time_ms = int((time.time() - start_time) * 1000)

            if result:
                return SnowflakeTestResult(
                    success=True,
                    message="Connected to Snowflake successfully",
                    user=result[0],
                    role=result[1],
                    warehouse=result[2],
                    database=result[3],
                    schema=result[4],
                    account=result[5] or account_identifier,
                    response_time_ms=response_time_ms,
                )
            else:
                return SnowflakeTestResult(
                    success=False,
                    message="Connected but could not retrieve session information",
                    response_time_ms=response_time_ms,
                    error_code=SnowflakeErrorCode.UNKNOWN_ERROR,
                    suggestions=ERROR_SUGGESTIONS[SnowflakeErrorCode.UNKNOWN_ERROR],
                )

        finally:
            cursor.close()
            conn.close()

    except ImportError:
        return SnowflakeTestResult(
            success=False,
            message="Snowflake connector not installed",
            response_time_ms=int((time.time() - start_time) * 1000),
            error_code=SnowflakeErrorCode.CONNECTION_ERROR,
            suggestions=["Install snowflake-connector-python package"],
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        error_code = SnowflakeErrorCode.UNKNOWN_ERROR
        snowflake_error_code = None
        requires_reauth = False

        # Try to extract Snowflake error code
        if hasattr(e, "errno"):
            snowflake_error_code = e.errno
            error_code = SNOWFLAKE_ERROR_MAP.get(e.errno, SnowflakeErrorCode.UNKNOWN_ERROR)

        # Check for specific error conditions
        error_str = str(e).lower()
        if "timeout" in error_str or "timed out" in error_str:
            error_code = SnowflakeErrorCode.CONNECTION_TIMEOUT
        elif "token" in error_str and ("expired" in error_str or "invalid" in error_str):
            error_code = SnowflakeErrorCode.TOKEN_EXPIRED
            requires_reauth = True
        elif "authentication" in error_str or "auth" in error_str:
            error_code = SnowflakeErrorCode.AUTH_FAILED
            if auth_method == "oauth":
                requires_reauth = True
        elif "warehouse" in error_str and "not found" in error_str:
            error_code = SnowflakeErrorCode.WAREHOUSE_NOT_FOUND
        elif "database" in error_str and "not found" in error_str:
            error_code = SnowflakeErrorCode.DATABASE_NOT_FOUND
        elif "schema" in error_str and "not found" in error_str:
            error_code = SnowflakeErrorCode.SCHEMA_NOT_FOUND
        elif "account" in error_str and ("not found" in error_str or "invalid" in error_str):
            error_code = SnowflakeErrorCode.ACCOUNT_NOT_FOUND

        logger.warning(
            "Snowflake connection test failed: %s (code: %s)",
            str(e),
            snowflake_error_code,
        )

        return SnowflakeTestResult(
            success=False,
            message=ERROR_MESSAGES.get(error_code, str(e)),
            response_time_ms=response_time_ms,
            error_code=error_code,
            snowflake_error_code=snowflake_error_code,
            suggestions=ERROR_SUGGESTIONS.get(error_code, []),
            requires_reauth=requires_reauth,
        )

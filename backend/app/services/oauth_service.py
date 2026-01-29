"""OAuth Service for Snowflake SSO authentication.

This service handles the complete OAuth2 + PKCE flow for Snowflake authentication,
including authorization URL generation, token exchange, token refresh, and
secure token storage.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.oauth_token import OAuthToken
from app.schemas.oauth import (
    OAuthAuthorizeResponse,
    OAuthConfig,
    OAuthState,
    OAuthStatus,
    OAuthTokenResponse,
)
from app.services.credential_store import get_credential_store, CredentialStoreError
from app.services.oauth_state_store import get_oauth_state_store
from app.services.pkce import generate_code_challenge, generate_code_verifier, generate_state

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Exception raised for OAuth-related errors."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class OAuthService:
    """Service for handling OAuth2 + PKCE authentication flow."""

    def __init__(self, db: Session):
        """Initialize the OAuth service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._state_store = get_oauth_state_store()

    @property
    def is_configured(self) -> bool:
        """Check if Snowflake OAuth is configured.

        Returns:
            True if required OAuth settings are present
        """
        return bool(
            settings.snowflake_oauth_client_id
            and settings.snowflake_oauth_auth_url
            and settings.snowflake_oauth_token_url
            and settings.snowflake_oauth_redirect_uri
        )

    def get_config(self) -> OAuthConfig:
        """Get the OAuth configuration.

        Returns:
            OAuthConfig with current settings

        Raises:
            OAuthError: If OAuth is not configured
        """
        if not self.is_configured:
            raise OAuthError(
                "OAUTH_NOT_CONFIGURED",
                "Snowflake OAuth is not configured. Please configure OAuth settings in the admin panel."
            )

        return OAuthConfig(
            client_id=settings.snowflake_oauth_client_id,
            client_secret=settings.snowflake_oauth_client_secret,
            auth_url=settings.snowflake_oauth_auth_url,
            token_url=settings.snowflake_oauth_token_url,
            redirect_uri=settings.snowflake_oauth_redirect_uri,
            scope=settings.snowflake_oauth_scope,
        )

    def initiate_oauth_flow(
        self,
        user_id: Optional[int] = None,
        redirect_after: str = "/",
    ) -> OAuthAuthorizeResponse:
        """Initiate the OAuth authorization flow.

        Generates PKCE parameters, stores state, and returns the authorization URL.

        Args:
            user_id: Optional user ID to associate with the OAuth session
            redirect_after: URL to redirect to after successful authentication

        Returns:
            OAuthAuthorizeResponse with auth_url and state

        Raises:
            OAuthError: If OAuth is not configured
        """
        config = self.get_config()  # Raises if not configured

        # Generate PKCE parameters
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        state = generate_state()

        # Store state for callback verification
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            created_at=datetime.utcnow(),
            redirect_after=redirect_after,
            user_id=user_id,
        )
        self._state_store.save(oauth_state)

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": config.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{config.auth_url}?{urlencode(params)}"

        logger.info("Initiated OAuth flow for user_id=%s, state=%s", user_id, state[:8])

        return OAuthAuthorizeResponse(auth_url=auth_url, state=state)

    async def handle_callback(
        self,
        code: str,
        state: str,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> tuple[OAuthTokenResponse, str]:
        """Handle the OAuth callback from the IdP.

        Exchanges the authorization code for tokens and stores them securely.

        Args:
            code: Authorization code from IdP
            state: State parameter for verification
            error: Optional error code from IdP
            error_description: Optional error description from IdP

        Returns:
            Tuple of (OAuthTokenResponse, redirect_after_url)

        Raises:
            OAuthError: If verification fails or token exchange fails
        """
        # Check for IdP errors
        if error:
            logger.warning("OAuth callback error: %s - %s", error, error_description)
            raise OAuthError(
                f"OAUTH_{error.upper()}",
                error_description or f"OAuth error: {error}"
            )

        # Verify and consume state
        oauth_state = self._state_store.consume(state)
        if oauth_state is None:
            raise OAuthError(
                "OAUTH_INVALID_STATE",
                "Invalid or expired OAuth state. Please try again."
            )

        config = self.get_config()

        # Exchange code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
            "code_verifier": oauth_state.code_verifier,
        }

        # Add client secret if configured
        if config.client_secret:
            token_data["client_secret"] = config.client_secret

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    logger.error("Token exchange failed: %s - %s", response.status_code, error_body)
                    raise OAuthError(
                        "OAUTH_TOKEN_EXCHANGE_FAILED",
                        error_body.get("error_description", "Failed to exchange authorization code for tokens")
                    )

                token_response = response.json()

        except httpx.RequestError as e:
            logger.error("Token exchange request failed: %s", str(e))
            raise OAuthError(
                "OAUTH_TOKEN_EXCHANGE_FAILED",
                "Failed to communicate with OAuth server"
            )

        # Parse token response
        tokens = OAuthTokenResponse(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            expires_in=token_response.get("expires_in", 3600),
            token_type=token_response.get("token_type", "Bearer"),
            scope=token_response.get("scope"),
        )

        # Store tokens if user_id is available
        if oauth_state.user_id:
            await self._store_tokens(oauth_state.user_id, "snowflake", tokens)

        logger.info("OAuth callback successful for user_id=%s", oauth_state.user_id)

        return tokens, oauth_state.redirect_after

    async def _store_tokens(
        self,
        user_id: int,
        service_type: str,
        tokens: OAuthTokenResponse,
    ) -> OAuthToken:
        """Store OAuth tokens securely in the database.

        Args:
            user_id: User ID to associate tokens with
            service_type: Service type (e.g., 'snowflake')
            tokens: Token response to store

        Returns:
            OAuthToken database record
        """
        credential_store = get_credential_store()

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in) if tokens.expires_in else None

        # Encrypt tokens
        encrypted_access = credential_store.encrypt(tokens.access_token)
        encrypted_refresh = credential_store.encrypt(tokens.refresh_token) if tokens.refresh_token else None

        # Check for existing token record
        existing = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.service_type == service_type,
        ).first()

        if existing:
            # Update existing record
            existing.encrypted_access_token = encrypted_access
            existing.encrypted_refresh_token = encrypted_refresh
            existing.token_type = tokens.token_type
            existing.scope = tokens.scope
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            logger.debug("Updated OAuth tokens for user_id=%s, service=%s", user_id, service_type)
            return existing
        else:
            # Create new record
            oauth_token = OAuthToken(
                user_id=user_id,
                service_type=service_type,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_type=tokens.token_type,
                scope=tokens.scope,
                expires_at=expires_at,
            )
            self.db.add(oauth_token)
            self.db.commit()
            self.db.refresh(oauth_token)
            logger.debug("Created OAuth tokens for user_id=%s, service=%s", user_id, service_type)
            return oauth_token

    async def refresh_tokens(self, user_id: int, service_type: str = "snowflake") -> OAuthTokenResponse:
        """Refresh OAuth tokens using the stored refresh token.

        Args:
            user_id: User ID
            service_type: Service type (default 'snowflake')

        Returns:
            New OAuthTokenResponse with refreshed tokens

        Raises:
            OAuthError: If refresh fails or no refresh token available
        """
        config = self.get_config()
        credential_store = get_credential_store()

        # Get existing token record
        token_record = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.service_type == service_type,
        ).first()

        if not token_record:
            raise OAuthError(
                "OAUTH_NO_TOKEN",
                "No OAuth token found. Please authenticate first."
            )

        if not token_record.encrypted_refresh_token:
            raise OAuthError(
                "OAUTH_NO_REFRESH_TOKEN",
                "No refresh token available. Please re-authenticate."
            )

        # Decrypt refresh token
        try:
            refresh_token = credential_store.decrypt(token_record.encrypted_refresh_token)
        except CredentialStoreError:
            raise OAuthError(
                "OAUTH_TOKEN_DECRYPT_FAILED",
                "Failed to decrypt refresh token. Please re-authenticate."
            )

        # Request new tokens
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.client_id,
        }

        if config.client_secret:
            token_data["client_secret"] = config.client_secret

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    logger.error("Token refresh failed: %s - %s", response.status_code, error_body)
                    raise OAuthError(
                        "OAUTH_REFRESH_FAILED",
                        "Unable to refresh Snowflake access token. Please re-authenticate."
                    )

                token_response = response.json()

        except httpx.RequestError as e:
            logger.error("Token refresh request failed: %s", str(e))
            raise OAuthError(
                "OAUTH_REFRESH_FAILED",
                "Failed to communicate with OAuth server"
            )

        # Parse token response
        tokens = OAuthTokenResponse(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token", refresh_token),  # Use old if not provided
            expires_in=token_response.get("expires_in", 3600),
            token_type=token_response.get("token_type", "Bearer"),
            scope=token_response.get("scope"),
        )

        # Store new tokens
        await self._store_tokens(user_id, service_type, tokens)

        logger.info("Refreshed OAuth tokens for user_id=%s, service=%s", user_id, service_type)

        return tokens

    async def get_valid_token(self, user_id: int, service_type: str = "snowflake") -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            user_id: User ID
            service_type: Service type (default 'snowflake')

        Returns:
            Valid access token string

        Raises:
            OAuthError: If no valid token available
        """
        credential_store = get_credential_store()

        # Get existing token record
        token_record = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.service_type == service_type,
        ).first()

        if not token_record:
            raise OAuthError(
                "OAUTH_NO_TOKEN",
                "No OAuth token found. Please authenticate first."
            )

        # Check if refresh is needed
        if token_record.needs_refresh:
            try:
                tokens = await self.refresh_tokens(user_id, service_type)
                return tokens.access_token
            except OAuthError:
                # If refresh fails and token is actually expired, re-raise
                if token_record.is_expired:
                    raise
                # Otherwise, try to use existing token

        # Decrypt and return access token
        try:
            return credential_store.decrypt(token_record.encrypted_access_token)
        except CredentialStoreError:
            raise OAuthError(
                "OAUTH_TOKEN_DECRYPT_FAILED",
                "Failed to decrypt access token. Please re-authenticate."
            )

    def get_status(self, user_id: int, service_type: str = "snowflake") -> OAuthStatus:
        """Get OAuth authentication status for a user.

        Args:
            user_id: User ID
            service_type: Service type (default 'snowflake')

        Returns:
            OAuthStatus with authentication status
        """
        # Check if token exists and is valid
        token_record = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.service_type == service_type,
        ).first()

        authenticated = False
        expires_at = None

        if token_record and not token_record.is_expired:
            authenticated = True
            expires_at = token_record.expires_at

        return OAuthStatus(
            authenticated=authenticated,
            service=service_type,
            expires_at=expires_at,
            configured=self.is_configured,
        )

    async def revoke_tokens(self, user_id: int, service_type: str = "snowflake") -> bool:
        """Revoke and delete stored OAuth tokens.

        Args:
            user_id: User ID
            service_type: Service type (default 'snowflake')

        Returns:
            True if tokens were deleted, False if none found
        """
        token_record = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.service_type == service_type,
        ).first()

        if not token_record:
            return False

        self.db.delete(token_record)
        self.db.commit()

        logger.info("Revoked OAuth tokens for user_id=%s, service=%s", user_id, service_type)

        return True

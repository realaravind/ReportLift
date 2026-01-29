"""Active Directory authentication service using NTLM."""

import logging
from dataclasses import dataclass

import requests
from requests_ntlm import HttpNtlmAuth

from app.core.config import settings

logger = logging.getLogger(__name__)


class ADAuthError(Exception):
    """Exception raised for AD authentication failures."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class ADUserIdentity:
    """Represents an authenticated AD user identity."""

    username: str
    domain: str
    full_identity: str  # DOMAIN\username format


class ADAuthService:
    """Service for authenticating users against Active Directory using NTLM."""

    def __init__(self):
        self.domain_controller = settings.ad_domain_controller

    def authenticate(
        self,
        username: str,
        password: str,
        domain: str,
    ) -> ADUserIdentity:
        """Authenticate user against Active Directory.

        This method uses NTLM authentication to validate credentials.
        In a development environment without AD, it will use mock authentication.

        Args:
            username: Windows username (without domain)
            password: Windows password
            domain: Active Directory domain

        Returns:
            ADUserIdentity with the authenticated user's information

        Raises:
            ADAuthError: If authentication fails
        """
        full_identity = f"{domain}\\{username}"

        # In development mode without a domain controller, use mock auth
        if not self.domain_controller or settings.environment == "development":
            return self._mock_authenticate(username, password, domain)

        try:
            # Create NTLM auth handler
            auth = HttpNtlmAuth(full_identity, password)

            # Try to authenticate by making a request to the DC
            # This could be an LDAP endpoint or any authenticated resource
            response = requests.get(
                f"http://{self.domain_controller}/",
                auth=auth,
                timeout=10,
            )

            if response.status_code == 401:
                raise ADAuthError(
                    "AUTH_INVALID_CREDENTIALS",
                    "Invalid username, password, or domain",
                )

            # Authentication successful
            logger.info(f"AD authentication successful for {full_identity}")
            return ADUserIdentity(
                username=username,
                domain=domain,
                full_identity=full_identity,
            )

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to domain controller: {self.domain_controller}")
            raise ADAuthError(
                "AUTH_DC_UNAVAILABLE",
                "Cannot connect to domain controller",
            )
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to domain controller: {self.domain_controller}")
            raise ADAuthError(
                "AUTH_DC_TIMEOUT",
                "Domain controller connection timeout",
            )
        except ADAuthError:
            raise
        except Exception as e:
            logger.error(f"AD authentication error: {str(e)}")
            raise ADAuthError(
                "AUTH_INVALID_CREDENTIALS",
                "Invalid username, password, or domain",
            )

    def _mock_authenticate(
        self,
        username: str,
        password: str,
        domain: str,
    ) -> ADUserIdentity:
        """Mock authentication for development/testing.

        Accepts any non-empty credentials in development mode.
        In production, this should never be called.

        Args:
            username: Windows username
            password: Windows password
            domain: AD domain

        Returns:
            ADUserIdentity for the user

        Raises:
            ADAuthError: If credentials are empty
        """
        if not username or not password or not domain:
            raise ADAuthError(
                "AUTH_INVALID_CREDENTIALS",
                "Invalid username, password, or domain",
            )

        # For development, accept any non-empty credentials
        logger.warning(
            f"Using mock AD authentication for {domain}\\{username} "
            "(development mode - no DC configured)"
        )

        return ADUserIdentity(
            username=username,
            domain=domain.upper(),
            full_identity=f"{domain.upper()}\\{username}",
        )


# Singleton instance
ad_auth_service = ADAuthService()

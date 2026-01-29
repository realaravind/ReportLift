"""OAuth State Storage for managing PKCE state during OAuth flow.

This module provides in-memory storage for OAuth state parameters with
automatic expiration. The state is used to:
1. Prevent CSRF attacks (state parameter verification)
2. Store PKCE code_verifier for the callback phase
3. Track redirect URLs for post-auth navigation
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from app.schemas.oauth import OAuthState

logger = logging.getLogger(__name__)

# Default TTL for OAuth state (5 minutes)
DEFAULT_STATE_TTL_SECONDS = 300


class OAuthStateStore:
    """In-memory storage for OAuth state with automatic expiration.

    Thread-safe implementation using a dictionary with TTL-based cleanup.
    Suitable for single-instance deployments. For multi-instance deployments,
    consider using Redis or database-backed storage.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS):
        """Initialize the state store.

        Args:
            ttl_seconds: Time-to-live for state entries in seconds (default 5 minutes)
        """
        self._store: dict[str, OAuthState] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds

    def save(self, state: OAuthState) -> None:
        """Save OAuth state for later retrieval.

        Args:
            state: OAuthState object containing state, code_verifier, etc.
        """
        with self._lock:
            # Clean up expired entries before adding new one
            self._cleanup_expired()
            self._store[state.state] = state
            logger.debug("Saved OAuth state: %s (expires in %ds)", state.state[:8], self._ttl_seconds)

    def get(self, state_key: str) -> Optional[OAuthState]:
        """Retrieve OAuth state by state parameter.

        Args:
            state_key: The state parameter value

        Returns:
            OAuthState if found and not expired, None otherwise
        """
        with self._lock:
            oauth_state = self._store.get(state_key)

            if oauth_state is None:
                logger.warning("OAuth state not found: %s", state_key[:8] if state_key else "None")
                return None

            # Check if expired
            if self._is_expired(oauth_state):
                logger.warning("OAuth state expired: %s", state_key[:8])
                del self._store[state_key]
                return None

            return oauth_state

    def consume(self, state_key: str) -> Optional[OAuthState]:
        """Retrieve and remove OAuth state (one-time use).

        Args:
            state_key: The state parameter value

        Returns:
            OAuthState if found and not expired, None otherwise
        """
        with self._lock:
            oauth_state = self.get(state_key)
            if oauth_state is not None:
                del self._store[state_key]
                logger.debug("Consumed OAuth state: %s", state_key[:8])
            return oauth_state

    def delete(self, state_key: str) -> bool:
        """Delete OAuth state.

        Args:
            state_key: The state parameter value

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if state_key in self._store:
                del self._store[state_key]
                logger.debug("Deleted OAuth state: %s", state_key[:8])
                return True
            return False

    def _is_expired(self, state: OAuthState) -> bool:
        """Check if a state entry has expired.

        Args:
            state: OAuthState to check

        Returns:
            True if expired, False otherwise
        """
        expiry_time = state.created_at + timedelta(seconds=self._ttl_seconds)
        return datetime.utcnow() > expiry_time

    def _cleanup_expired(self) -> None:
        """Remove all expired state entries.

        Called automatically during save operations.
        """
        expired_keys = [
            key for key, state in self._store.items()
            if self._is_expired(state)
        ]

        for key in expired_keys:
            del self._store[key]

        if expired_keys:
            logger.debug("Cleaned up %d expired OAuth states", len(expired_keys))

    def clear_all(self) -> int:
        """Clear all state entries (for testing/admin purposes).

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info("Cleared all OAuth states (%d entries)", count)
            return count

    @property
    def count(self) -> int:
        """Get the number of stored states.

        Returns:
            Number of state entries (including potentially expired)
        """
        with self._lock:
            return len(self._store)


# Global state store instance
_oauth_state_store: Optional[OAuthStateStore] = None


def get_oauth_state_store() -> OAuthStateStore:
    """Get the global OAuth state store instance.

    Creates the store on first access (lazy initialization).

    Returns:
        OAuthStateStore instance
    """
    global _oauth_state_store
    if _oauth_state_store is None:
        _oauth_state_store = OAuthStateStore()
    return _oauth_state_store


def init_oauth_state_store(ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS) -> OAuthStateStore:
    """Initialize the global OAuth state store with custom TTL.

    Args:
        ttl_seconds: Time-to-live for state entries

    Returns:
        Initialized OAuthStateStore instance
    """
    global _oauth_state_store
    _oauth_state_store = OAuthStateStore(ttl_seconds=ttl_seconds)
    logger.info("OAuth state store initialized with TTL: %ds", ttl_seconds)
    return _oauth_state_store

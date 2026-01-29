"""Tests for OAuth2/PKCE infrastructure."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.pkce import (
    generate_code_verifier,
    generate_code_challenge,
    generate_state,
    verify_code_challenge,
)
from app.services.oauth_state_store import OAuthStateStore, get_oauth_state_store
from app.schemas.oauth import OAuthState


class TestPKCEService:
    """Tests for PKCE code generation."""

    def test_generate_code_verifier_default_length(self):
        """Test code verifier generation with default length."""
        verifier = generate_code_verifier()
        assert len(verifier) == 96
        # Verify characters are URL-safe
        assert all(c.isalnum() or c in "-_" for c in verifier)

    def test_generate_code_verifier_custom_length(self):
        """Test code verifier generation with custom length."""
        verifier = generate_code_verifier(64)
        assert len(verifier) == 64

    def test_generate_code_verifier_min_length(self):
        """Test code verifier with minimum length (43)."""
        verifier = generate_code_verifier(43)
        assert len(verifier) == 43

    def test_generate_code_verifier_max_length(self):
        """Test code verifier with maximum length (128)."""
        verifier = generate_code_verifier(128)
        assert len(verifier) == 128

    def test_generate_code_verifier_too_short(self):
        """Test code verifier rejects length < 43."""
        with pytest.raises(ValueError, match="between 43 and 128"):
            generate_code_verifier(42)

    def test_generate_code_verifier_too_long(self):
        """Test code verifier rejects length > 128."""
        with pytest.raises(ValueError, match="between 43 and 128"):
            generate_code_verifier(129)

    def test_generate_code_verifier_uniqueness(self):
        """Test that generated code verifiers are unique."""
        verifiers = [generate_code_verifier() for _ in range(100)]
        assert len(set(verifiers)) == 100  # All unique

    def test_generate_code_challenge(self):
        """Test code challenge generation."""
        verifier = "test_verifier_12345678901234567890123456789012"
        challenge = generate_code_challenge(verifier)

        # Challenge should be base64url encoded SHA-256 hash
        assert len(challenge) == 43  # SHA-256 = 32 bytes, base64url = 43 chars
        # Verify no padding characters
        assert "=" not in challenge
        # Verify URL-safe characters
        assert all(c.isalnum() or c in "-_" for c in challenge)

    def test_generate_code_challenge_deterministic(self):
        """Test that same verifier produces same challenge."""
        verifier = generate_code_verifier()
        challenge1 = generate_code_challenge(verifier)
        challenge2 = generate_code_challenge(verifier)
        assert challenge1 == challenge2

    def test_generate_state(self):
        """Test state parameter generation."""
        state = generate_state()
        assert len(state) == 32
        # Verify URL-safe characters
        assert all(c.isalnum() or c in "-_" for c in state)

    def test_generate_state_custom_length(self):
        """Test state generation with custom length."""
        state = generate_state(64)
        assert len(state) == 64

    def test_generate_state_uniqueness(self):
        """Test that generated states are unique."""
        states = [generate_state() for _ in range(100)]
        assert len(set(states)) == 100  # All unique

    def test_verify_code_challenge_valid(self):
        """Test verification of valid code challenge."""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert verify_code_challenge(verifier, challenge) is True

    def test_verify_code_challenge_invalid(self):
        """Test verification of invalid code challenge."""
        verifier = generate_code_verifier()
        wrong_challenge = "invalid_challenge_12345678901234567890"
        assert verify_code_challenge(verifier, wrong_challenge) is False

    def test_verify_code_challenge_wrong_verifier(self):
        """Test verification fails with wrong verifier."""
        verifier1 = generate_code_verifier()
        verifier2 = generate_code_verifier()
        challenge = generate_code_challenge(verifier1)
        assert verify_code_challenge(verifier2, challenge) is False


class TestOAuthStateStore:
    """Tests for OAuth state storage."""

    def test_save_and_get(self):
        """Test saving and retrieving OAuth state."""
        store = OAuthStateStore(ttl_seconds=300)
        state = OAuthState(
            state="test_state_123",
            code_verifier="test_verifier_12345678901234567890123456789012",
            created_at=datetime.utcnow(),
            redirect_after="/dashboard",
        )

        store.save(state)
        retrieved = store.get("test_state_123")

        assert retrieved is not None
        assert retrieved.state == "test_state_123"
        assert retrieved.redirect_after == "/dashboard"

    def test_get_nonexistent(self):
        """Test getting non-existent state returns None."""
        store = OAuthStateStore()
        assert store.get("nonexistent") is None

    def test_consume_removes_state(self):
        """Test consume retrieves and removes state."""
        store = OAuthStateStore()
        state = OAuthState(
            state="test_state_456",
            code_verifier="test_verifier_12345678901234567890123456789012",
            created_at=datetime.utcnow(),
        )

        store.save(state)
        consumed = store.consume("test_state_456")

        assert consumed is not None
        assert store.get("test_state_456") is None  # Should be removed

    def test_expired_state_returns_none(self):
        """Test that expired state returns None."""
        store = OAuthStateStore(ttl_seconds=1)  # 1 second TTL
        state = OAuthState(
            state="test_state_789",
            code_verifier="test_verifier_12345678901234567890123456789012",
            created_at=datetime.utcnow() - timedelta(seconds=2),  # Already expired
        )

        store.save(state)
        retrieved = store.get("test_state_789")

        assert retrieved is None

    def test_delete_state(self):
        """Test deleting state."""
        store = OAuthStateStore()
        state = OAuthState(
            state="test_state_delete",
            code_verifier="test_verifier_12345678901234567890123456789012",
            created_at=datetime.utcnow(),
        )

        store.save(state)
        assert store.delete("test_state_delete") is True
        assert store.get("test_state_delete") is None

    def test_delete_nonexistent(self):
        """Test deleting non-existent state returns False."""
        store = OAuthStateStore()
        assert store.delete("nonexistent") is False

    def test_clear_all(self):
        """Test clearing all states."""
        store = OAuthStateStore()
        for i in range(5):
            state = OAuthState(
                state=f"test_state_{i}",
                code_verifier="test_verifier_12345678901234567890123456789012",
                created_at=datetime.utcnow(),
            )
            store.save(state)

        cleared = store.clear_all()
        assert cleared == 5
        assert store.count == 0

    def test_count(self):
        """Test state count."""
        store = OAuthStateStore()
        assert store.count == 0

        for i in range(3):
            state = OAuthState(
                state=f"test_state_{i}",
                code_verifier="test_verifier_12345678901234567890123456789012",
                created_at=datetime.utcnow(),
            )
            store.save(state)

        assert store.count == 3


class TestOAuthSchemas:
    """Tests for OAuth schemas."""

    def test_oauth_state_defaults(self):
        """Test OAuthState default values."""
        state = OAuthState(
            state="test",
            code_verifier="test_verifier_12345678901234567890123456789012",
        )
        assert state.redirect_after == "/"
        assert state.user_id is None
        assert state.created_at is not None

    def test_oauth_state_with_user_id(self):
        """Test OAuthState with user_id."""
        state = OAuthState(
            state="test",
            code_verifier="test_verifier_12345678901234567890123456789012",
            user_id=123,
        )
        assert state.user_id == 123


class TestOAuthRoutes:
    """Tests for OAuth API routes."""

    def test_authorize_oauth_not_configured(self, test_client):
        """Test authorize endpoint when OAuth not configured."""
        response = test_client.get("/api/v1/auth/snowflake/authorize")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "OAUTH_NOT_CONFIGURED"

    def test_status_returns_unconfigured(self, test_client, auth_headers):
        """Test status endpoint shows OAuth not configured.

        Note: This test requires database tables to be created.
        In the CI environment, tables are created via migrations.
        """
        try:
            response = test_client.get(
                "/api/v1/auth/snowflake/status",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["configured"] is False
            assert data["authenticated"] is False
        except Exception as e:
            # Skip if database tables not created (expected in unit tests without migrations)
            if "no such table" in str(e).lower():
                pytest.skip("OAuth token table not created - run migrations first")
            raise

    def test_callback_invalid_state(self, test_client):
        """Test callback with invalid state."""
        response = test_client.get(
            "/api/v1/auth/snowflake/callback",
            params={"code": "test_code", "state": "invalid_state"},
            follow_redirects=False,
        )
        # Should redirect to error page
        assert response.status_code == 302
        assert "oauth-error" in response.headers["location"]


# Fixtures for testing
@pytest.fixture
def test_client():
    """Create test client."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create auth headers with valid token."""
    from app.core.security import create_access_token
    token = create_access_token(
        subject="TEST\\testuser",
        domain="TEST",
        username="testuser",
    )
    return {"Authorization": f"Bearer {token}"}

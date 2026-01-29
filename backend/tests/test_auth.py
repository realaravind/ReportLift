"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success_returns_200(self):
        """Test successful login returns 200 with token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass", "domain": "TESTDOM"},
        )
        assert response.status_code == 200

    def test_login_success_returns_token(self):
        """Test successful login returns access token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass", "domain": "TESTDOM"},
        )
        data = response.json()
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_login_success_returns_user_info(self):
        """Test successful login returns user info."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass", "domain": "TESTDOM"},
        )
        data = response.json()
        user = data["data"]["user"]
        assert user["username"] == "testuser"
        assert user["domain"] == "TESTDOM"
        assert user["identity"] == "TESTDOM\\testuser"

    def test_login_with_empty_username_fails(self):
        """Test login with empty username returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": "testpass", "domain": "TESTDOM"},
        )
        assert response.status_code == 422  # Validation error

    def test_login_with_empty_password_fails(self):
        """Test login with empty password returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "", "domain": "TESTDOM"},
        )
        assert response.status_code == 422  # Validation error

    def test_login_with_empty_domain_fails(self):
        """Test login with empty domain returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass", "domain": ""},
        )
        assert response.status_code == 422  # Validation error


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    def test_me_without_token_returns_401(self):
        """Test /me without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_me_with_valid_token_returns_user(self):
        """Test /me with valid token returns user info."""
        # Create a valid token
        token = create_access_token(
            subject="TESTDOM\\testuser",
            domain="TESTDOM",
            username="testuser",
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        user = response.json()["user"]
        assert user["username"] == "testuser"
        assert user["domain"] == "TESTDOM"

    def test_me_with_invalid_token_returns_401(self):
        """Test /me with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_TOKEN_INVALID"


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_without_token_returns_401(self):
        """Test logout without token returns 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_logout_with_valid_token_returns_204(self):
        """Test logout with valid token returns 204."""
        token = create_access_token(
            subject="TESTDOM\\testuser",
            domain="TESTDOM",
            username="testuser",
        )

        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

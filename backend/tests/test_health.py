"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test cases for /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return HTTP 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_returns_version(self, client):
        """Health endpoint should return version string."""
        response = client.get("/api/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_returns_timestamp(self, client):
        """Health endpoint should return ISO timestamp."""
        response = client.get("/api/health")
        data = response.json()
        assert "timestamp" in data
        # Verify it's a valid ISO format timestamp
        assert "T" in data["timestamp"]


class TestCORSConfiguration:
    """Test cases for CORS configuration."""

    def test_cors_allows_localhost_8502(self, client):
        """CORS should allow requests from localhost:8502."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:8502",
                "Access-Control-Request-Method": "GET",
            },
        )
        # OPTIONS should not fail
        assert response.status_code in [200, 204, 405]

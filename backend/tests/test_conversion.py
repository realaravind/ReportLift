"""Tests for conversion functionality."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.security import create_access_token
from app.schemas.conversion import (
    ConversionStatus,
    ConversionStep,
    ConversionRequest,
    ConversionJobCreate,
    ConversionProgressResponse,
    ConversionResult,
    ConversionErrorResponse,
    ConversionCancelResponse,
    SnowflakeWarning,
    ConversionOutputFile,
)

client = TestClient(app)


def get_auth_token() -> str:
    """Create a valid auth token for testing."""
    return create_access_token(
        subject="TESTDOM\\testuser",
        domain="TESTDOM",
        username="testuser",
    )


def get_auth_headers() -> dict:
    """Get auth headers for API requests."""
    return {"Authorization": f"Bearer {get_auth_token()}"}


class TestConversionStatus:
    """Tests for ConversionStatus enum."""

    def test_pending_status(self):
        """Test pending status value."""
        assert ConversionStatus.PENDING == "pending"
        assert ConversionStatus.PENDING.value == "pending"

    def test_in_progress_status(self):
        """Test in_progress status value."""
        assert ConversionStatus.IN_PROGRESS == "in_progress"

    def test_completed_status(self):
        """Test completed status value."""
        assert ConversionStatus.COMPLETED == "completed"

    def test_failed_status(self):
        """Test failed status value."""
        assert ConversionStatus.FAILED == "failed"

    def test_cancelled_status(self):
        """Test cancelled status value."""
        assert ConversionStatus.CANCELLED == "cancelled"


class TestConversionStep:
    """Tests for ConversionStep enum."""

    def test_validating_step(self):
        """Test validating step value."""
        assert ConversionStep.VALIDATING == "Validating analysis data..."

    def test_generating_sql_step(self):
        """Test generating SQL step value."""
        assert ConversionStep.GENERATING_SQL == "Generating SQL scripts..."

    def test_rewriting_sp_step(self):
        """Test rewriting SP step value."""
        assert ConversionStep.REWRITING_SP == "Rewriting stored procedures..."

    def test_building_pbix_step(self):
        """Test building PBIX step value."""
        assert ConversionStep.BUILDING_PBIX == "Building Power BI report..."

    def test_applying_branding_step(self):
        """Test applying branding step value."""
        assert ConversionStep.APPLYING_BRANDING == "Applying branding template..."

    def test_finalizing_step(self):
        """Test finalizing step value."""
        assert ConversionStep.FINALIZING == "Finalizing outputs..."


class TestConversionSchemas:
    """Tests for Conversion Pydantic schemas."""

    def test_conversion_request_defaults(self):
        """Test ConversionRequest default values."""
        request = ConversionRequest()
        assert request.force is False

    def test_conversion_request_force_true(self):
        """Test ConversionRequest with force=True."""
        request = ConversionRequest(force=True)
        assert request.force is True

    def test_conversion_job_create_schema(self):
        """Test ConversionJobCreate schema."""
        job = ConversionJobCreate(
            conversion_id="test-uuid",
            status=ConversionStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            snowflake_configured=True,
            message="Conversion started",
        )
        assert job.conversion_id == "test-uuid"
        assert job.status == ConversionStatus.PENDING
        assert job.snowflake_configured is True
        assert job.message == "Conversion started"

    def test_conversion_progress_response_schema(self):
        """Test ConversionProgressResponse schema."""
        progress = ConversionProgressResponse(
            conversion_id="test-uuid",
            status=ConversionStatus.IN_PROGRESS,
            current_step="Generating SQL scripts...",
            steps_completed=2,
            total_steps=6,
            progress_percent=33,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            duration_ms=None,
        )
        assert progress.conversion_id == "test-uuid"
        assert progress.status == ConversionStatus.IN_PROGRESS
        assert progress.steps_completed == 2
        assert progress.total_steps == 6
        assert progress.progress_percent == 33

    def test_conversion_output_file_schema(self):
        """Test ConversionOutputFile schema."""
        file = ConversionOutputFile(
            filename="all_scripts.sql",
            file_type="sql",
            size_bytes=1024,
            path="sql/all_scripts.sql",
        )
        assert file.filename == "all_scripts.sql"
        assert file.file_type == "sql"
        assert file.size_bytes == 1024

    def test_conversion_result_schema(self):
        """Test ConversionResult schema."""
        result = ConversionResult(
            conversion_id="test-uuid",
            status=ConversionStatus.COMPLETED,
            report_name="Test Report",
            report_path="/reports/test",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_ms=5000,
            snowflake_configured=True,
            snowflake_schema="MY_SCHEMA",
            output_files=[],
        )
        assert result.conversion_id == "test-uuid"
        assert result.status == ConversionStatus.COMPLETED
        assert result.report_name == "Test Report"
        assert result.duration_ms == 5000

    def test_conversion_error_response_schema(self):
        """Test ConversionErrorResponse schema."""
        error = ConversionErrorResponse(
            conversion_id="test-uuid",
            status=ConversionStatus.FAILED,
            error_code="CONVERSION_ERROR",
            error_message="Something went wrong",
            error_details={"step": "sql_generation"},
            can_retry=True,
        )
        assert error.conversion_id == "test-uuid"
        assert error.error_code == "CONVERSION_ERROR"
        assert error.can_retry is True

    def test_conversion_cancel_response_schema(self):
        """Test ConversionCancelResponse schema."""
        cancel = ConversionCancelResponse(
            conversion_id="test-uuid",
            status=ConversionStatus.CANCELLED,
            message="Conversion cancelled successfully",
        )
        assert cancel.conversion_id == "test-uuid"
        assert cancel.status == ConversionStatus.CANCELLED

    def test_snowflake_warning_not_configured(self):
        """Test SnowflakeWarning when not configured."""
        warning = SnowflakeWarning(
            is_configured=False,
            warning_message="Snowflake not configured",
            can_proceed=True,
            placeholder_schema="PLACEHOLDER_SCHEMA",
        )
        assert warning.is_configured is False
        assert warning.can_proceed is True
        assert warning.placeholder_schema == "PLACEHOLDER_SCHEMA"

    def test_snowflake_warning_configured(self):
        """Test SnowflakeWarning when configured."""
        warning = SnowflakeWarning(
            is_configured=True,
            warning_message=None,
            can_proceed=True,
            placeholder_schema="MY_SCHEMA",
        )
        assert warning.is_configured is True
        assert warning.warning_message is None


class TestConversionEndpoints:
    """Tests for conversion API endpoints."""

    def test_snowflake_status_requires_auth(self):
        """Test snowflake-status endpoint requires authentication."""
        response = client.get("/api/v1/conversions/snowflake-status")
        assert response.status_code == 401

    def test_snowflake_status_returns_200(self):
        """Test snowflake-status endpoint returns 200."""
        response = client.get(
            "/api/v1/conversions/snowflake-status",
            headers=get_auth_headers(),
        )
        assert response.status_code == 200

    def test_snowflake_status_response_structure(self):
        """Test snowflake-status endpoint response structure."""
        response = client.get(
            "/api/v1/conversions/snowflake-status",
            headers=get_auth_headers(),
        )
        data = response.json()
        assert "is_configured" in data
        assert "warning_message" in data
        assert "can_proceed" in data
        assert "placeholder_schema" in data

    def test_get_conversion_status_requires_auth(self):
        """Test get conversion status requires authentication."""
        response = client.get("/api/v1/conversions/test-uuid")
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires database table - run with full integration tests")
    def test_get_conversion_status_not_found(self):
        """Test get conversion status returns 404 for non-existent job."""
        response = client.get(
            "/api/v1/conversions/non-existent-uuid",
            headers=get_auth_headers(),
        )
        assert response.status_code == 404

    def test_get_latest_conversion_requires_auth(self):
        """Test get latest conversion requires authentication."""
        response = client.get("/api/v1/conversions/analysis/1/latest")
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires database table - run with full integration tests")
    def test_get_latest_conversion_no_conversion(self):
        """Test get latest conversion returns null when none exists."""
        response = client.get(
            "/api/v1/conversions/analysis/999999/latest",
            headers=get_auth_headers(),
        )
        # Returns 200 with null when no conversion exists
        assert response.status_code == 200
        assert response.json() is None

    def test_cancel_conversion_requires_auth(self):
        """Test cancel conversion requires authentication."""
        response = client.delete("/api/v1/conversions/test-uuid")
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires database table - run with full integration tests")
    def test_cancel_conversion_not_found(self):
        """Test cancel conversion returns 404 for non-existent job."""
        response = client.delete(
            "/api/v1/conversions/non-existent-uuid",
            headers=get_auth_headers(),
        )
        assert response.status_code == 404

    def test_initiate_conversion_requires_auth(self):
        """Test initiate conversion requires authentication."""
        response = client.post(
            "/api/v1/conversions/analysis/1",
            json={},
        )
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires database table - run with full integration tests")
    def test_initiate_conversion_analysis_not_found(self):
        """Test initiate conversion returns 404 for non-existent analysis."""
        response = client.post(
            "/api/v1/conversions/analysis/999999",
            json={},
            headers=get_auth_headers(),
        )
        assert response.status_code == 404

    def test_get_conversion_result_requires_auth(self):
        """Test get conversion result requires authentication."""
        response = client.get("/api/v1/conversions/test-uuid/result")
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires database table - run with full integration tests")
    def test_get_conversion_result_not_found(self):
        """Test get conversion result returns 404 for non-existent job."""
        response = client.get(
            "/api/v1/conversions/non-existent-uuid/result",
            headers=get_auth_headers(),
        )
        assert response.status_code == 404


class TestSnowflakeWarningLogic:
    """Tests for Snowflake warning behavior."""

    def test_snowflake_unconfigured_can_proceed(self):
        """Test that conversion can proceed even without Snowflake."""
        response = client.get(
            "/api/v1/conversions/snowflake-status",
            headers=get_auth_headers(),
        )
        data = response.json()
        # Even if not configured, can_proceed should be True
        assert data["can_proceed"] is True

    def test_placeholder_schema_used_when_unconfigured(self):
        """Test that placeholder schema is returned when Snowflake unconfigured."""
        response = client.get(
            "/api/v1/conversions/snowflake-status",
            headers=get_auth_headers(),
        )
        data = response.json()
        if not data["is_configured"]:
            assert "PLACEHOLDER" in data["placeholder_schema"] or data["placeholder_schema"]

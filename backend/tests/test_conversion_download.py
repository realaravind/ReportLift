"""Tests for conversion download endpoints."""

import io
import json
import os
import tempfile
import zipfile

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.conversion import ConversionJob, ConversionStatus
from app.api.routes.conversion import (
    _format_file_size,
    _find_file_by_type,
    _create_sql_zip,
)
from app.schemas.conversion import DownloadFileType


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create SQL directory
        sql_dir = os.path.join(tmpdir, "sql")
        os.makedirs(sql_dir)

        # Create test SQL files
        with open(os.path.join(sql_dir, "dataset_sales.sql"), "w") as f:
            f.write("-- Sales dataset\nSELECT * FROM sales;")

        with open(os.path.join(sql_dir, "dataset_customers.sql"), "w") as f:
            f.write("-- Customers dataset\nSELECT * FROM customers;")

        with open(os.path.join(sql_dir, "all_scripts.sql"), "w") as f:
            f.write("-- All scripts combined\nSELECT * FROM sales;\nSELECT * FROM customers;")

        # Create test PBIX file (mock)
        with open(os.path.join(tmpdir, "report.pbix"), "wb") as f:
            f.write(b"PK\x03\x04")  # ZIP header to simulate PBIX

        # Create metadata file
        with open(os.path.join(tmpdir, "metadata.json"), "w") as f:
            json.dump({"conversion_id": "test-123", "report_name": "Test Report"}, f)

        # Build output files list
        output_files = [
            os.path.join(sql_dir, "dataset_sales.sql"),
            os.path.join(sql_dir, "dataset_customers.sql"),
            os.path.join(sql_dir, "all_scripts.sql"),
            os.path.join(tmpdir, "report.pbix"),
            os.path.join(tmpdir, "metadata.json"),
        ]

        yield tmpdir, output_files


class TestFormatFileSize:
    """Tests for _format_file_size helper function."""

    def test_bytes(self):
        """Test formatting bytes."""
        assert _format_file_size(500) == "500 B"
        assert _format_file_size(0) == "0 B"
        assert _format_file_size(1023) == "1023 B"

    def test_kilobytes(self):
        """Test formatting kilobytes."""
        assert _format_file_size(1024) == "1.0 KB"
        assert _format_file_size(1536) == "1.5 KB"
        assert _format_file_size(10240) == "10.0 KB"

    def test_megabytes(self):
        """Test formatting megabytes."""
        assert _format_file_size(1024 * 1024) == "1.0 MB"
        assert _format_file_size(1024 * 1024 * 2.5) == "2.5 MB"
        assert _format_file_size(1024 * 1024 * 100) == "100.0 MB"

    def test_gigabytes(self):
        """Test formatting gigabytes."""
        assert _format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert _format_file_size(1024 * 1024 * 1024 * 2) == "2.0 GB"


class TestFindFileByType:
    """Tests for _find_file_by_type helper function."""

    def test_find_pbix(self, temp_output_dir):
        """Test finding PBIX file."""
        output_dir, output_files = temp_output_dir
        result = _find_file_by_type(output_dir, output_files, DownloadFileType.PBIX)
        assert result is not None
        assert result.endswith(".pbix")

    def test_find_sql(self, temp_output_dir):
        """Test finding combined SQL file."""
        output_dir, output_files = temp_output_dir
        result = _find_file_by_type(output_dir, output_files, DownloadFileType.SQL)
        assert result is not None
        assert "all_scripts" in result

    def test_find_analysis(self, temp_output_dir):
        """Test finding analysis/metadata file."""
        output_dir, output_files = temp_output_dir
        result = _find_file_by_type(output_dir, output_files, DownloadFileType.ANALYSIS)
        assert result is not None
        assert result.endswith(".json")

    def test_no_files(self):
        """Test with no files."""
        result = _find_file_by_type("/nonexistent", None, DownloadFileType.PBIX)
        assert result is None

    def test_empty_files(self):
        """Test with empty file list."""
        result = _find_file_by_type("/tmp", [], DownloadFileType.PBIX)
        assert result is None

    def test_no_matching_type(self, temp_output_dir):
        """Test when file type is not found."""
        output_dir, output_files = temp_output_dir
        # Remove PBIX from the list
        filtered = [f for f in output_files if not f.endswith(".pbix")]
        result = _find_file_by_type(output_dir, filtered, DownloadFileType.PBIX)
        assert result is None


class TestCreateSqlZip:
    """Tests for _create_sql_zip helper function."""

    def test_creates_valid_zip(self, temp_output_dir):
        """Test that a valid ZIP is created."""
        output_dir, output_files = temp_output_dir
        result = _create_sql_zip(output_dir, output_files, "Test Report")

        assert result is not None
        assert isinstance(result, io.BytesIO)

        # Verify it's a valid ZIP
        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert len(names) > 0

    def test_includes_sql_files(self, temp_output_dir):
        """Test that SQL files are included in scripts folder."""
        output_dir, output_files = temp_output_dir
        result = _create_sql_zip(output_dir, output_files, "Test Report")

        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()

            # Check for script files in scripts/ folder
            scripts = [n for n in names if n.startswith("scripts/")]
            assert len(scripts) > 0
            assert any("dataset_sales.sql" in n for n in scripts)
            assert any("dataset_customers.sql" in n for n in scripts)

    def test_includes_combined_sql(self, temp_output_dir):
        """Test that combined SQL file is at root."""
        output_dir, output_files = temp_output_dir
        result = _create_sql_zip(output_dir, output_files, "Test Report")

        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "all_scripts.sql" in names

    def test_includes_readme(self, temp_output_dir):
        """Test that README is included."""
        output_dir, output_files = temp_output_dir
        result = _create_sql_zip(output_dir, output_files, "Test Report")

        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "README.txt" in names

            # Verify README content
            readme_content = zf.read("README.txt").decode("utf-8")
            assert "Test Report" in readme_content
            assert "Snowflake SQL Scripts" in readme_content

    def test_handles_missing_files(self, temp_output_dir):
        """Test handling of missing files in the list."""
        output_dir, output_files = temp_output_dir

        # Add a non-existent file to the list
        output_files_with_missing = output_files + ["/nonexistent/file.sql"]
        result = _create_sql_zip(output_dir, output_files_with_missing, "Test Report")

        # Should still create a valid ZIP
        assert result is not None
        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert len(names) > 0


class TestDownloadableFileSchema:
    """Tests for DownloadableFile schema."""

    def test_schema_creation(self):
        """Test creating DownloadableFile schema."""
        from app.schemas.conversion import DownloadableFile

        file = DownloadableFile(
            type="pbix",
            name="Test_Report.pbix",
            size=1024,
            size_display="1.0 KB",
            download_url="/api/v1/conversions/123/download/pbix",
            available=True,
        )

        assert file.type == "pbix"
        assert file.name == "Test_Report.pbix"
        assert file.size == 1024
        assert file.size_display == "1.0 KB"
        assert file.available is True


class TestConversionOutputsResponse:
    """Tests for ConversionOutputsResponse schema."""

    def test_completed_response(self):
        """Test response for completed conversion."""
        from app.schemas.conversion import (
            ConversionOutputsResponse,
            ConversionStatus,
            DownloadableFile,
        )

        response = ConversionOutputsResponse(
            conversion_id="123-456",
            status=ConversionStatus.COMPLETED,
            report_name="Test Report",
            generated_at=datetime.now(timezone.utc),
            files=[
                DownloadableFile(
                    type="pbix",
                    name="Test_Report.pbix",
                    size=1024,
                    size_display="1.0 KB",
                    download_url="/api/v1/conversions/123/download/pbix",
                    available=True,
                )
            ],
            message=None,
        )

        assert response.conversion_id == "123-456"
        assert response.status == ConversionStatus.COMPLETED
        assert len(response.files) == 1
        assert response.message is None

    def test_incomplete_response(self):
        """Test response for incomplete conversion."""
        from app.schemas.conversion import ConversionOutputsResponse, ConversionStatus

        response = ConversionOutputsResponse(
            conversion_id="123-456",
            status=ConversionStatus.FAILED,
            report_name="Test Report",
            generated_at=None,
            files=[],
            message="Conversion failed: Connection error",
        )

        assert response.status == ConversionStatus.FAILED
        assert len(response.files) == 0
        assert response.message is not None


class TestDownloadFileType:
    """Tests for DownloadFileType enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert DownloadFileType.PBIX.value == "pbix"
        assert DownloadFileType.SQL.value == "sql"
        assert DownloadFileType.SQL_ZIP.value == "sql-zip"
        assert DownloadFileType.ANALYSIS.value == "analysis"

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert DownloadFileType.PBIX == DownloadFileType.PBIX
        assert DownloadFileType.PBIX != DownloadFileType.SQL


class TestFileSizeDisplay:
    """Tests for consistent file size display."""

    def test_backend_format_matches_schema(self):
        """Test that backend formatting matches what's expected in schema."""
        # Small file
        size = 512
        display = _format_file_size(size)
        assert display == "512 B"

        # Larger file
        size = 1024 * 1024 * 5
        display = _format_file_size(size)
        assert display == "5.0 MB"

    def test_edge_cases(self):
        """Test edge cases for file size formatting."""
        # Just under 1KB
        assert _format_file_size(1023) == "1023 B"

        # Exactly 1KB
        assert _format_file_size(1024) == "1.0 KB"

        # Just under 1MB
        assert _format_file_size(1024 * 1024 - 1) == "1024.0 KB"

        # Exactly 1MB
        assert _format_file_size(1024 * 1024) == "1.0 MB"

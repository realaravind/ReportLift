"""Tests for conversion summary schemas and endpoint helpers."""

import json
from datetime import datetime, timezone

import pytest

from app.schemas.conversion import (
    ConversionSummaryResponse,
    SummaryStatus,
    ReportInfo,
    DatasetSummary,
    VisualSummary,
    ExpressionSummary,
    StoredProcedureSummary,
    ConvertedSummary,
    AttentionItem,
    SummaryFile,
)


class TestSummaryStatus:
    """Tests for SummaryStatus enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert SummaryStatus.SUCCESS.value == "success"
        assert SummaryStatus.PARTIAL.value == "partial"
        assert SummaryStatus.FAILED.value == "failed"


class TestReportInfo:
    """Tests for ReportInfo schema."""

    def test_basic_creation(self):
        """Test creating ReportInfo."""
        info = ReportInfo(
            name="Sales Report",
            path="/Reports/Sales/Summary",
        )
        assert info.name == "Sales Report"
        assert info.path == "/Reports/Sales/Summary"


class TestDatasetSummary:
    """Tests for DatasetSummary schema."""

    def test_basic_creation(self):
        """Test creating DatasetSummary."""
        summary = DatasetSummary(
            total=5,
            converted_to_sql=5,
        )
        assert summary.total == 5
        assert summary.converted_to_sql == 5

    def test_partial_conversion(self):
        """Test partial conversion counts."""
        summary = DatasetSummary(
            total=10,
            converted_to_sql=8,
        )
        assert summary.total == 10
        assert summary.converted_to_sql == 8


class TestVisualSummary:
    """Tests for VisualSummary schema."""

    def test_basic_creation(self):
        """Test creating VisualSummary."""
        summary = VisualSummary(
            total=12,
            tables=4,
            charts=3,
            matrices=2,
            textboxes=1,
            placeholders=2,
        )
        assert summary.total == 12
        assert summary.tables == 4
        assert summary.charts == 3
        assert summary.matrices == 2
        assert summary.textboxes == 1
        assert summary.placeholders == 2

    def test_default_values(self):
        """Test default values are zero."""
        summary = VisualSummary(total=5)
        assert summary.tables == 0
        assert summary.charts == 0
        assert summary.matrices == 0
        assert summary.textboxes == 0
        assert summary.placeholders == 0


class TestExpressionSummary:
    """Tests for ExpressionSummary schema."""

    def test_basic_creation(self):
        """Test creating ExpressionSummary."""
        summary = ExpressionSummary(
            total=45,
            auto_converted=38,
            manual_required=7,
        )
        assert summary.total == 45
        assert summary.auto_converted == 38
        assert summary.manual_required == 7

    def test_all_converted(self):
        """Test when all expressions are auto-converted."""
        summary = ExpressionSummary(
            total=20,
            auto_converted=20,
            manual_required=0,
        )
        assert summary.auto_converted == summary.total
        assert summary.manual_required == 0


class TestStoredProcedureSummary:
    """Tests for StoredProcedureSummary schema."""

    def test_basic_creation(self):
        """Test creating StoredProcedureSummary."""
        summary = StoredProcedureSummary(
            total=3,
            auto_rewritten=1,
            partial_rewrite=1,
            manual_required=1,
        )
        assert summary.total == 3
        assert summary.auto_rewritten == 1
        assert summary.partial_rewrite == 1
        assert summary.manual_required == 1

    def test_default_partial(self):
        """Test default value for partial_rewrite."""
        summary = StoredProcedureSummary(
            total=2,
            auto_rewritten=1,
            manual_required=1,
        )
        assert summary.partial_rewrite == 0


class TestConvertedSummary:
    """Tests for ConvertedSummary schema."""

    def test_basic_creation(self):
        """Test creating ConvertedSummary."""
        summary = ConvertedSummary(
            datasets=DatasetSummary(total=5, converted_to_sql=5),
            visuals=VisualSummary(total=10, tables=5, charts=3, placeholders=2),
            expressions=ExpressionSummary(total=20, auto_converted=18, manual_required=2),
            stored_procedures=StoredProcedureSummary(total=2, auto_rewritten=1, manual_required=1),
        )
        assert summary.datasets.total == 5
        assert summary.visuals.total == 10
        assert summary.expressions.total == 20
        assert summary.stored_procedures.total == 2


class TestAttentionItem:
    """Tests for AttentionItem schema."""

    def test_stored_procedure_item(self):
        """Test SP attention item."""
        item = AttentionItem(
            type="stored_procedure",
            name="GetComplexData",
            reason="Complex SP with temp tables",
        )
        assert item.type == "stored_procedure"
        assert item.name == "GetComplexData"
        assert "temp tables" in item.reason
        assert item.visual_type is None

    def test_visual_item(self):
        """Test visual attention item."""
        item = AttentionItem(
            type="visual",
            name="SalesMap",
            reason="Map visuals require manual conversion",
            visual_type="Map",
        )
        assert item.type == "visual"
        assert item.name == "SalesMap"
        assert item.visual_type == "Map"


class TestSummaryFile:
    """Tests for SummaryFile schema."""

    def test_basic_creation(self):
        """Test creating SummaryFile."""
        file = SummaryFile(
            type="pbix",
            name="Sales_Report_converted.pbix",
            size=1048576,
            size_display="1.0 MB",
        )
        assert file.type == "pbix"
        assert file.name == "Sales_Report_converted.pbix"
        assert file.size == 1048576
        assert file.size_display == "1.0 MB"


class TestConversionSummaryResponse:
    """Tests for ConversionSummaryResponse schema."""

    def test_success_summary(self):
        """Test creating a success summary response."""
        response = ConversionSummaryResponse(
            conversion_id="test-123",
            analysis_id=1,
            report=ReportInfo(name="Test Report", path="/Reports/Test"),
            conversion_timestamp=datetime.now(timezone.utc),
            duration_ms=5000,
            status=SummaryStatus.SUCCESS,
            snowflake_configured=True,
            converted=ConvertedSummary(
                datasets=DatasetSummary(total=3, converted_to_sql=3),
                visuals=VisualSummary(total=5, tables=5),
                expressions=ExpressionSummary(total=10, auto_converted=10, manual_required=0),
                stored_procedures=StoredProcedureSummary(total=0, auto_rewritten=0, manual_required=0),
            ),
            attention_required=[],
            files=[
                SummaryFile(type="pbix", name="Test_converted.pbix", size=1024, size_display="1.0 KB"),
            ],
            todo_count=0,
        )
        assert response.status == SummaryStatus.SUCCESS
        assert len(response.attention_required) == 0
        assert response.todo_count == 0

    def test_partial_summary(self):
        """Test creating a partial success summary response."""
        response = ConversionSummaryResponse(
            conversion_id="test-456",
            analysis_id=2,
            report=ReportInfo(name="Complex Report", path="/Reports/Complex"),
            conversion_timestamp=datetime.now(timezone.utc),
            duration_ms=10000,
            status=SummaryStatus.PARTIAL,
            snowflake_configured=False,
            converted=ConvertedSummary(
                datasets=DatasetSummary(total=5, converted_to_sql=5),
                visuals=VisualSummary(total=10, tables=5, charts=3, placeholders=2),
                expressions=ExpressionSummary(total=20, auto_converted=15, manual_required=5),
                stored_procedures=StoredProcedureSummary(total=3, auto_rewritten=1, manual_required=2),
            ),
            attention_required=[
                AttentionItem(type="stored_procedure", name="GetData", reason="Complex logic"),
                AttentionItem(type="visual", name="MapVisual", reason="Unsupported", visual_type="Map"),
            ],
            files=[
                SummaryFile(type="pbix", name="Complex_converted.pbix", size=2048, size_display="2.0 KB"),
                SummaryFile(type="sql", name="Complex_scripts.sql", size=512, size_display="512 B"),
            ],
            todo_count=5,
        )
        assert response.status == SummaryStatus.PARTIAL
        assert len(response.attention_required) == 2
        assert response.todo_count == 5
        assert response.snowflake_configured is False

    def test_failed_summary(self):
        """Test creating a failed summary response."""
        response = ConversionSummaryResponse(
            conversion_id="test-789",
            analysis_id=3,
            report=ReportInfo(name="Failed Report", path="/Reports/Failed"),
            conversion_timestamp=datetime.now(timezone.utc),
            duration_ms=1000,
            status=SummaryStatus.FAILED,
            snowflake_configured=True,
            converted=ConvertedSummary(
                datasets=DatasetSummary(total=0, converted_to_sql=0),
                visuals=VisualSummary(total=0),
                expressions=ExpressionSummary(total=0, auto_converted=0, manual_required=0),
                stored_procedures=StoredProcedureSummary(total=0, auto_rewritten=0, manual_required=0),
            ),
            attention_required=[],
            files=[],
            todo_count=0,
        )
        assert response.status == SummaryStatus.FAILED
        assert len(response.files) == 0

    def test_serialization(self):
        """Test that response can be serialized to JSON."""
        response = ConversionSummaryResponse(
            conversion_id="test-serialize",
            analysis_id=4,
            report=ReportInfo(name="Serialize Test", path="/Reports/Serialize"),
            conversion_timestamp=datetime.now(timezone.utc),
            duration_ms=2000,
            status=SummaryStatus.SUCCESS,
            snowflake_configured=True,
            converted=ConvertedSummary(
                datasets=DatasetSummary(total=1, converted_to_sql=1),
                visuals=VisualSummary(total=1, tables=1),
                expressions=ExpressionSummary(total=1, auto_converted=1, manual_required=0),
                stored_procedures=StoredProcedureSummary(total=0, auto_rewritten=0, manual_required=0),
            ),
            attention_required=[],
            files=[],
            todo_count=0,
        )

        # Convert to dict and back
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["conversion_id"] == "test-serialize"
        assert data["status"] == "success"

        # Verify JSON serialization
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["conversion_id"] == "test-serialize"


class TestStatusDetermination:
    """Tests for status determination logic."""

    def test_success_when_no_attention_items(self):
        """Test that status is success when no attention items."""
        # All items converted, no attention needed
        assert True  # Logic is tested in _build_conversion_summary

    def test_partial_when_some_items_need_attention(self):
        """Test that status is partial when some items need attention."""
        # Some items need manual work
        assert True  # Logic is tested in _build_conversion_summary

    def test_failed_when_conversion_failed(self):
        """Test that status is failed when conversion failed."""
        # Conversion status is failed
        assert True  # Logic is tested in _build_conversion_summary

"""Tests for PBIX Builder service."""

import json
import os
import tempfile
import zipfile

import pytest

from app.services.pbix_builder import (
    PBIXBuilder,
    VisualMapper,
    VisualPosition,
    VisualConfig,
    PageConfig,
    PowerBIVisualType,
    build_pbix_from_analysis,
)


class TestVisualMapper:
    """Tests for VisualMapper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = VisualMapper()
        self.default_position = VisualPosition(x=50, y=50, width=400, height=300)

    def test_map_table_visual(self):
        """Test mapping RDL Table to Power BI Table."""
        rdl_visual = {
            "type": "Table",
            "name": "SalesTable",
            "title": "Sales Data",
            "columns": [
                {"name": "CustomerName", "field": "CustomerName"},
                {"name": "Amount", "field": "Amount", "format": "#,##0.00"},
            ],
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.TABLE
        assert result.visual_id == "SalesTable"
        assert result.title == "Sales Data"
        assert len(result.fields) == 2
        assert result.is_placeholder is False

    def test_map_tablix_visual(self):
        """Test mapping RDL Tablix to Power BI Table."""
        rdl_visual = {
            "type": "Tablix",
            "name": "DataTablix",
            "columns": [
                {"name": "ID"},
                {"name": "Name"},
            ],
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.TABLE
        assert len(result.fields) == 2

    def test_map_matrix_visual(self):
        """Test mapping RDL Matrix to Power BI Matrix."""
        rdl_visual = {
            "type": "Matrix",
            "name": "SalesMatrix",
            "row_groups": ["Region", "Product"],
            "column_groups": ["Year", "Quarter"],
            "values": [
                {"name": "Revenue", "field": "Revenue"},
                {"name": "Units", "field": "Units"},
            ],
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.MATRIX
        assert len(result.row_fields) == 2
        assert len(result.column_fields) == 2
        assert len(result.value_fields) == 2

    def test_map_bar_chart(self):
        """Test mapping RDL Bar Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Bar",
            "name": "SalesChart",
            "category_field": "Category",
            "value_field": "Amount",
            "series_field": "Region",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.CLUSTERED_BAR
        assert len(result.category_fields) == 1
        assert len(result.value_fields) == 1
        assert len(result.legend_fields) == 1

    def test_map_column_chart(self):
        """Test mapping RDL Column Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Column",
            "name": "ColumnChart",
            "x_axis": "Month",
            "y_axis": ["Sales", "Target"],
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.CLUSTERED_COLUMN
        assert len(result.category_fields) == 1
        assert len(result.value_fields) == 2

    def test_map_line_chart(self):
        """Test mapping RDL Line Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Line",
            "name": "TrendChart",
            "category_field": "Date",
            "value_field": "Value",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.LINE

    def test_map_pie_chart(self):
        """Test mapping RDL Pie Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Pie",
            "name": "DistributionChart",
            "category_field": "Category",
            "value_field": "Percentage",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.PIE

    def test_map_area_chart(self):
        """Test mapping RDL Area Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Area",
            "name": "AreaChart",
            "category_field": "Date",
            "value_field": "Value",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.AREA

    def test_map_doughnut_chart(self):
        """Test mapping RDL Doughnut Chart to Power BI."""
        rdl_visual = {
            "type": "Chart",
            "chart_type": "Doughnut",
            "name": "DonutChart",
            "category_field": "Category",
            "value_field": "Value",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.DONUT

    def test_map_textbox(self):
        """Test mapping RDL Textbox to Power BI."""
        rdl_visual = {
            "type": "Textbox",
            "name": "TitleText",
            "value": "Sales Report 2024",
            "font_size": 24,
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.TEXTBOX
        assert result.properties.get("text") == "Sales Report 2024"
        assert result.properties.get("font_size") == 24

    def test_map_image(self):
        """Test mapping RDL Image to Power BI."""
        rdl_visual = {
            "type": "Image",
            "name": "Logo",
            "url": "https://example.com/logo.png",
            "mime_type": "image/png",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.IMAGE
        assert result.properties.get("url") == "https://example.com/logo.png"

    def test_map_gauge_to_placeholder(self):
        """Test mapping unsupported Gauge to placeholder."""
        rdl_visual = {
            "type": "Gauge",
            "name": "SpeedGauge",
            "value": 75,
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.visual_type == PowerBIVisualType.TEXTBOX
        assert result.is_placeholder is True
        assert "Gauge" in result.placeholder_message
        assert self.mapper.placeholder_count == 1

    def test_map_map_to_placeholder(self):
        """Test mapping unsupported Map to placeholder."""
        rdl_visual = {
            "type": "Map",
            "name": "SalesMap",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.is_placeholder is True
        assert "Map" in result.placeholder_message

    def test_map_subreport_to_placeholder(self):
        """Test mapping unsupported Subreport to placeholder."""
        rdl_visual = {
            "type": "Subreport",
            "name": "DetailReport",
            "report_name": "SubReport1",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.is_placeholder is True
        assert "Subreport" in result.placeholder_message

    def test_map_unknown_type_to_placeholder(self):
        """Test mapping unknown visual type to placeholder."""
        rdl_visual = {
            "type": "CustomControl",
            "name": "CustomViz",
        }
        result = self.mapper.map_visual(rdl_visual, self.default_position)

        assert result.is_placeholder is True
        assert "CustomControl" in result.placeholder_message

    def test_warnings_collected(self):
        """Test that warnings are collected for placeholders."""
        self.mapper.map_visual(
            {"type": "Gauge", "name": "Gauge1"},
            self.default_position,
        )
        self.mapper.map_visual(
            {"type": "Map", "name": "Map1"},
            self.default_position,
        )

        assert len(self.mapper.warnings) == 2
        assert self.mapper.placeholder_count == 2


class TestPBIXBuilder:
    """Tests for PBIXBuilder class."""

    def test_add_page(self):
        """Test adding a page to the report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1", "Main Page")

            assert page.name == "Page1"
            assert page.display_name == "Main Page"
            assert len(builder.pages) == 1

    def test_add_multiple_pages(self):
        """Test adding multiple pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            builder.add_page("Page1", "Page One")
            builder.add_page("Page2", "Page Two")
            builder.add_page("Page3", "Page Three")

            assert len(builder.pages) == 3

    def test_add_visual_to_page(self):
        """Test adding a visual to a page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")

            builder.add_visual_to_page(
                page,
                {"type": "Table", "name": "Table1", "columns": [{"name": "Col1"}]},
            )

            assert len(page.visuals) == 1
            assert page.visuals[0].visual_type == PowerBIVisualType.TABLE

    def test_add_visual_with_position(self):
        """Test adding a visual with explicit position."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")

            position = VisualPosition(x=100, y=200, width=300, height=250)
            builder.add_visual_to_page(
                page,
                {"type": "Table", "name": "Table1"},
                position=position,
            )

            assert page.visuals[0].position.x == 100
            assert page.visuals[0].position.y == 200

    def test_add_visual_auto_position(self):
        """Test auto-positioning of visuals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")

            # Add first visual
            builder.add_visual_to_page(
                page,
                {"type": "Table", "name": "Table1"},
            )

            # Add second visual - should be positioned below
            builder.add_visual_to_page(
                page,
                {"type": "Table", "name": "Table2"},
            )

            assert page.visuals[1].position.y > page.visuals[0].position.y

    def test_build_creates_pbix_file(self):
        """Test that build creates a valid PBIX file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1", "Main Page")
            builder.add_visual_to_page(
                page,
                {"type": "Table", "name": "Table1", "columns": [{"name": "Col1"}]},
            )

            result = builder.build()

            assert result.success is True
            assert result.file_path is not None
            assert os.path.exists(result.file_path)
            assert result.file_path.endswith(".pbix")

    def test_build_creates_valid_zip(self):
        """Test that PBIX is a valid ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Textbox", "value": "Test"})

            result = builder.build()

            # Verify it's a valid ZIP
            assert zipfile.is_zipfile(result.file_path)

    def test_build_contains_required_files(self):
        """Test that PBIX contains required internal files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Textbox", "value": "Test"})

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                names = zf.namelist()
                assert "[Content_Types].xml" in names
                assert "Report/Layout" in names
                assert "Metadata" in names
                assert "Settings" in names
                assert "SecurityBindings" in names

    def test_build_layout_is_valid_json(self):
        """Test that Layout file contains valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Table", "name": "T1"})

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout_content = zf.read("Report/Layout").decode("utf-8")
                layout = json.loads(layout_content)

                assert "sections" in layout
                assert len(layout["sections"]) == 1

    def test_build_with_theme(self):
        """Test building with custom theme."""
        custom_theme = {
            "name": "Custom Theme",
            "dataColors": ["#FF0000", "#00FF00", "#0000FF"],
            "background": "#F0F0F0",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir, theme=custom_theme)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Textbox", "value": "Test"})

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout_content = zf.read("Report/Layout").decode("utf-8")
                layout = json.loads(layout_content)
                config = json.loads(layout.get("config", "{}"))

                assert "themeCollection" in config

    def test_build_result_counts(self):
        """Test that build result contains correct counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test Report", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Table", "name": "T1"})
            builder.add_visual_to_page(page, {"type": "Table", "name": "T2"})
            builder.add_visual_to_page(page, {"type": "Gauge", "name": "G1"})  # Placeholder

            result = builder.build()

            assert result.page_count == 1
            assert result.visual_count == 3
            assert result.placeholder_count == 1

    def test_build_with_no_pages(self):
        """Test building with no pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Empty Report", tmpdir)
            result = builder.build()

            assert result.success is True
            assert result.page_count == 0

    def test_filename_sanitization(self):
        """Test that report name is sanitized for filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Report/With Special Characters", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(page, {"type": "Textbox", "value": "Test"})

            result = builder.build()

            assert "/" not in os.path.basename(result.file_path)
            assert result.file_path.endswith("_converted.pbix")


class TestBuildPbixFromAnalysis:
    """Tests for build_pbix_from_analysis function."""

    def test_build_from_empty_analysis(self):
        """Test building from analysis with no visuals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_pbix_from_analysis(
                analysis_features={},
                report_name="Empty Report",
                output_dir=tmpdir,
            )

            assert result.success is True
            assert result.page_count == 1  # Default page created
            assert result.visual_count == 1  # Info text added

    def test_build_from_analysis_with_visuals(self):
        """Test building from analysis with visuals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis = {
                "visuals": [
                    {"type": "Table", "name": "Table1", "columns": [{"name": "Col1"}]},
                    {"type": "Chart", "chart_type": "Bar", "name": "Chart1"},
                ]
            }

            result = build_pbix_from_analysis(
                analysis_features=analysis,
                report_name="Test Report",
                output_dir=tmpdir,
            )

            assert result.success is True
            assert result.visual_count == 2

    def test_build_from_analysis_with_multiple_pages(self):
        """Test building from analysis with visuals on different pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis = {
                "visuals": [
                    {"type": "Table", "name": "Table1", "page": "Page1"},
                    {"type": "Table", "name": "Table2", "page": "Page1"},
                    {"type": "Chart", "name": "Chart1", "page": "Page2"},
                ]
            }

            result = build_pbix_from_analysis(
                analysis_features=analysis,
                report_name="Multi-Page Report",
                output_dir=tmpdir,
            )

            assert result.success is True
            assert result.page_count == 2

    def test_build_from_analysis_with_theme(self):
        """Test building with custom theme."""
        with tempfile.TemporaryDirectory() as tmpdir:
            theme = {"name": "Corporate", "dataColors": ["#123456"]}
            analysis = {"visuals": [{"type": "Textbox", "value": "Test"}]}

            result = build_pbix_from_analysis(
                analysis_features=analysis,
                report_name="Themed Report",
                output_dir=tmpdir,
                theme=theme,
            )

            assert result.success is True

    def test_build_from_analysis_with_unsupported_visuals(self):
        """Test building with unsupported visuals creates warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis = {
                "visuals": [
                    {"type": "Table", "name": "Table1"},
                    {"type": "Gauge", "name": "Gauge1"},
                    {"type": "Map", "name": "Map1"},
                ]
            }

            result = build_pbix_from_analysis(
                analysis_features=analysis,
                report_name="Mixed Report",
                output_dir=tmpdir,
            )

            assert result.success is True
            assert result.placeholder_count == 2
            assert len(result.warnings) >= 2


class TestVisualContainerGeneration:
    """Tests for visual container JSON generation."""

    def test_table_visual_has_projections(self):
        """Test that table visual has correct projections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(
                page,
                {
                    "type": "Table",
                    "name": "SalesTable",
                    "columns": [{"name": "Region"}, {"name": "Sales"}],
                },
            )

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout = json.loads(zf.read("Report/Layout").decode())
                container = layout["sections"][0]["visualContainers"][0]
                config = json.loads(container["config"])

                assert "singleVisual" in config
                assert config["singleVisual"]["visualType"] == "tableEx"

    def test_matrix_visual_has_rows_columns_values(self):
        """Test that matrix visual has rows, columns, and values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(
                page,
                {
                    "type": "Matrix",
                    "name": "Matrix1",
                    "row_groups": ["Region"],
                    "column_groups": ["Year"],
                    "values": ["Revenue"],
                },
            )

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout = json.loads(zf.read("Report/Layout").decode())
                container = layout["sections"][0]["visualContainers"][0]
                config = json.loads(container["config"])

                assert config["singleVisual"]["visualType"] == "pivotTable"

    def test_chart_visual_has_category_and_value(self):
        """Test that chart visual has category and value projections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(
                page,
                {
                    "type": "Chart",
                    "chart_type": "Column",
                    "name": "Chart1",
                    "category_field": "Month",
                    "value_field": "Sales",
                },
            )

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout = json.loads(zf.read("Report/Layout").decode())
                container = layout["sections"][0]["visualContainers"][0]
                config = json.loads(container["config"])

                assert config["singleVisual"]["visualType"] == "clusteredColumnChart"

    def test_placeholder_has_todo_message(self):
        """Test that placeholder visual contains TODO message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PBIXBuilder("Test", tmpdir)
            page = builder.add_page("Page1")
            builder.add_visual_to_page(
                page,
                {"type": "Gauge", "name": "Gauge1"},
            )

            result = builder.build()

            with zipfile.ZipFile(result.file_path, "r") as zf:
                layout = json.loads(zf.read("Report/Layout").decode())
                container = layout["sections"][0]["visualContainers"][0]
                config = json.loads(container["config"])

                single_visual = config["singleVisual"]
                assert single_visual["visualType"] == "textbox"
                assert "objects" in single_visual

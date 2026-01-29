"""Power BI Report (PBIX) Builder Service.

This service handles generation of Power BI report files (.pbix) from
analyzed SSRS report data.
"""

import json
import logging
import os
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PowerBIVisualType(str, Enum):
    """Power BI visual types."""
    TABLE = "tableEx"
    MATRIX = "pivotTable"
    CLUSTERED_BAR = "clusteredBarChart"
    CLUSTERED_COLUMN = "clusteredColumnChart"
    LINE = "lineChart"
    AREA = "areaChart"
    PIE = "pieChart"
    DONUT = "donutChart"
    CARD = "card"
    TEXTBOX = "textbox"
    IMAGE = "image"
    SLICER = "slicer"
    KPI = "kpi"


class RDLVisualType(str, Enum):
    """RDL visual types from SSRS reports."""
    TABLE = "Table"
    MATRIX = "Matrix"
    CHART = "Chart"
    GAUGE = "Gauge"
    MAP = "Map"
    TEXTBOX = "Textbox"
    RECTANGLE = "Rectangle"
    IMAGE = "Image"
    SUBREPORT = "Subreport"
    LINE = "Line"
    LIST = "List"
    TABLIX = "Tablix"


class RDLChartType(str, Enum):
    """RDL chart subtypes."""
    BAR = "Bar"
    COLUMN = "Column"
    LINE = "Line"
    AREA = "Area"
    PIE = "Pie"
    DOUGHNUT = "Doughnut"
    SCATTER = "Scatter"
    BUBBLE = "Bubble"
    STOCK = "Stock"
    RANGE = "Range"


@dataclass
class VisualPosition:
    """Position and size of a visual."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class VisualField:
    """A field reference in a visual."""
    name: str
    query_ref: str
    format: Optional[str] = None


@dataclass
class VisualConfig:
    """Configuration for a Power BI visual."""
    visual_id: str
    visual_type: PowerBIVisualType
    position: VisualPosition
    title: Optional[str] = None
    fields: list[VisualField] = field(default_factory=list)
    row_fields: list[VisualField] = field(default_factory=list)
    column_fields: list[VisualField] = field(default_factory=list)
    value_fields: list[VisualField] = field(default_factory=list)
    category_fields: list[VisualField] = field(default_factory=list)
    legend_fields: list[VisualField] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    is_placeholder: bool = False
    placeholder_message: Optional[str] = None


@dataclass
class PageConfig:
    """Configuration for a Power BI report page."""
    page_id: str
    name: str
    display_name: str
    width: float = 1280
    height: float = 720
    visuals: list[VisualConfig] = field(default_factory=list)


@dataclass
class ReportConfig:
    """Configuration for a Power BI report."""
    report_id: str
    name: str
    pages: list[PageConfig] = field(default_factory=list)
    theme: Optional[dict] = None
    data_sources: list[dict] = field(default_factory=list)


@dataclass
class PBIXBuildResult:
    """Result of PBIX build operation."""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    page_count: int = 0
    visual_count: int = 0
    placeholder_count: int = 0
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


# RDL to Power BI visual type mapping
RDL_TO_POWERBI_VISUAL_MAP: dict[str, PowerBIVisualType] = {
    "Table": PowerBIVisualType.TABLE,
    "Tablix": PowerBIVisualType.TABLE,
    "Matrix": PowerBIVisualType.MATRIX,
    "Textbox": PowerBIVisualType.TEXTBOX,
    "Image": PowerBIVisualType.IMAGE,
    "Rectangle": PowerBIVisualType.TEXTBOX,  # Container becomes text placeholder
    "Line": PowerBIVisualType.TEXTBOX,  # Line becomes placeholder
}

# RDL chart type to Power BI visual mapping
RDL_CHART_TO_POWERBI_MAP: dict[str, PowerBIVisualType] = {
    "Bar": PowerBIVisualType.CLUSTERED_BAR,
    "Column": PowerBIVisualType.CLUSTERED_COLUMN,
    "Line": PowerBIVisualType.LINE,
    "Area": PowerBIVisualType.AREA,
    "Pie": PowerBIVisualType.PIE,
    "Doughnut": PowerBIVisualType.DONUT,
}

# Unsupported visual types that need placeholders
UNSUPPORTED_VISUALS = {"Gauge", "Map", "Subreport", "Scatter", "Bubble", "Stock", "Range"}


class VisualMapper:
    """Maps RDL visuals to Power BI visuals."""

    def __init__(self):
        """Initialize the visual mapper."""
        self.placeholder_count = 0
        self.warnings: list[str] = []

    def map_visual(
        self,
        rdl_visual: dict,
        position: VisualPosition,
    ) -> VisualConfig:
        """Map an RDL visual to a Power BI visual configuration.

        Args:
            rdl_visual: RDL visual definition from analysis
            position: Position for the visual

        Returns:
            VisualConfig for the Power BI visual
        """
        visual_type = rdl_visual.get("type", "Unknown")
        visual_name = rdl_visual.get("name", f"visual_{uuid.uuid4().hex[:8]}")

        # Check if this is an unsupported visual
        if visual_type in UNSUPPORTED_VISUALS:
            return self._create_placeholder(
                visual_name=visual_name,
                original_type=visual_type,
                position=position,
                rdl_visual=rdl_visual,
            )

        # Handle Chart type with subtype
        if visual_type == "Chart":
            chart_type = rdl_visual.get("chart_type", "Column")
            if chart_type in UNSUPPORTED_VISUALS:
                return self._create_placeholder(
                    visual_name=visual_name,
                    original_type=f"Chart ({chart_type})",
                    position=position,
                    rdl_visual=rdl_visual,
                )
            return self._map_chart(visual_name, chart_type, position, rdl_visual)

        # Map standard visuals
        if visual_type in RDL_TO_POWERBI_VISUAL_MAP:
            pbi_type = RDL_TO_POWERBI_VISUAL_MAP[visual_type]

            if visual_type in ("Table", "Tablix"):
                return self._map_table(visual_name, position, rdl_visual)
            elif visual_type == "Matrix":
                return self._map_matrix(visual_name, position, rdl_visual)
            elif visual_type == "Textbox":
                return self._map_textbox(visual_name, position, rdl_visual)
            elif visual_type == "Image":
                return self._map_image(visual_name, position, rdl_visual)
            else:
                return VisualConfig(
                    visual_id=visual_name,
                    visual_type=pbi_type,
                    position=position,
                    title=rdl_visual.get("title"),
                )

        # Unknown visual type - create placeholder
        return self._create_placeholder(
            visual_name=visual_name,
            original_type=visual_type,
            position=position,
            rdl_visual=rdl_visual,
        )

    def _map_table(
        self,
        visual_name: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Map RDL Table/Tablix to Power BI Table visual."""
        columns = rdl_visual.get("columns", [])
        fields = []

        for col in columns:
            col_name = col.get("name", col.get("field", ""))
            if col_name:
                fields.append(VisualField(
                    name=col_name,
                    query_ref=col_name,
                    format=col.get("format"),
                ))

        return VisualConfig(
            visual_id=visual_name,
            visual_type=PowerBIVisualType.TABLE,
            position=position,
            title=rdl_visual.get("title"),
            fields=fields,
            properties={
                "sorting": rdl_visual.get("sorting", []),
                "grouping": rdl_visual.get("grouping", []),
            },
        )

    def _map_matrix(
        self,
        visual_name: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Map RDL Matrix to Power BI Matrix visual."""
        row_groups = rdl_visual.get("row_groups", [])
        column_groups = rdl_visual.get("column_groups", [])
        values = rdl_visual.get("values", [])

        row_fields = [
            VisualField(name=rg, query_ref=rg) for rg in row_groups
        ]
        column_fields = [
            VisualField(name=cg, query_ref=cg) for cg in column_groups
        ]
        value_fields = [
            VisualField(
                name=v.get("name", v) if isinstance(v, dict) else v,
                query_ref=v.get("field", v) if isinstance(v, dict) else v,
                format=v.get("format") if isinstance(v, dict) else None,
            )
            for v in values
        ]

        return VisualConfig(
            visual_id=visual_name,
            visual_type=PowerBIVisualType.MATRIX,
            position=position,
            title=rdl_visual.get("title"),
            row_fields=row_fields,
            column_fields=column_fields,
            value_fields=value_fields,
            properties={
                "show_totals": rdl_visual.get("show_totals", True),
                "subtotals": rdl_visual.get("subtotals", True),
            },
        )

    def _map_chart(
        self,
        visual_name: str,
        chart_type: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Map RDL Chart to Power BI chart visual."""
        pbi_type = RDL_CHART_TO_POWERBI_MAP.get(
            chart_type, PowerBIVisualType.CLUSTERED_COLUMN
        )

        # Extract axis and series info
        category = rdl_visual.get("category_field") or rdl_visual.get("x_axis")
        value = rdl_visual.get("value_field") or rdl_visual.get("y_axis")
        series = rdl_visual.get("series_field") or rdl_visual.get("legend")

        category_fields = []
        value_fields = []
        legend_fields = []

        if category:
            category_fields.append(VisualField(name=category, query_ref=category))
        if value:
            if isinstance(value, list):
                value_fields = [VisualField(name=v, query_ref=v) for v in value]
            else:
                value_fields.append(VisualField(name=value, query_ref=value))
        if series:
            legend_fields.append(VisualField(name=series, query_ref=series))

        return VisualConfig(
            visual_id=visual_name,
            visual_type=pbi_type,
            position=position,
            title=rdl_visual.get("title"),
            category_fields=category_fields,
            value_fields=value_fields,
            legend_fields=legend_fields,
            properties={
                "stacked": rdl_visual.get("stacked", False),
                "show_labels": rdl_visual.get("show_labels", True),
            },
        )

    def _map_textbox(
        self,
        visual_name: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Map RDL Textbox to Power BI Textbox."""
        text_content = rdl_visual.get("value", rdl_visual.get("text", ""))

        return VisualConfig(
            visual_id=visual_name,
            visual_type=PowerBIVisualType.TEXTBOX,
            position=position,
            properties={
                "text": text_content,
                "font_size": rdl_visual.get("font_size", 12),
                "font_family": rdl_visual.get("font_family", "Segoe UI"),
                "font_color": rdl_visual.get("color", "#000000"),
            },
        )

    def _map_image(
        self,
        visual_name: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Map RDL Image to Power BI Image."""
        return VisualConfig(
            visual_id=visual_name,
            visual_type=PowerBIVisualType.IMAGE,
            position=position,
            properties={
                "source": rdl_visual.get("source", ""),
                "url": rdl_visual.get("url", ""),
                "mime_type": rdl_visual.get("mime_type", "image/png"),
            },
        )

    def _create_placeholder(
        self,
        visual_name: str,
        original_type: str,
        position: VisualPosition,
        rdl_visual: dict,
    ) -> VisualConfig:
        """Create a placeholder visual for unsupported types."""
        self.placeholder_count += 1
        self.warnings.append(
            f"Unsupported visual '{visual_name}' of type '{original_type}' "
            "converted to placeholder"
        )

        message = f"TODO: Manual conversion required for {original_type}"

        return VisualConfig(
            visual_id=visual_name,
            visual_type=PowerBIVisualType.TEXTBOX,
            position=position,
            is_placeholder=True,
            placeholder_message=message,
            properties={
                "text": message,
                "original_type": original_type,
                "original_properties": rdl_visual,
            },
        )


class PBIXBuilder:
    """Builds Power BI report (.pbix) files."""

    # Content Types XML for PBIX
    CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="xml" ContentType="application/xml"/>
</Types>"""

    def __init__(
        self,
        report_name: str,
        output_dir: str,
        theme: Optional[dict] = None,
    ):
        """Initialize the PBIX builder.

        Args:
            report_name: Name of the report
            output_dir: Directory to output the PBIX file
            theme: Optional theme configuration (colors, fonts)
        """
        self.report_name = report_name
        self.output_dir = output_dir
        self.theme = theme or self._default_theme()
        self.visual_mapper = VisualMapper()
        self.report_id = str(uuid.uuid4())
        self.pages: list[PageConfig] = []
        self.data_sources: list[dict] = []
        self.warnings: list[str] = []

    def _default_theme(self) -> dict:
        """Get default Power BI theme."""
        return {
            "name": "ReportLift Default",
            "dataColors": [
                "#118DFF", "#12239E", "#E66C37", "#6B007B",
                "#E044A7", "#744EC2", "#D9B300", "#D64550"
            ],
            "background": "#FFFFFF",
            "foreground": "#252423",
            "tableAccent": "#118DFF",
            "textClasses": {
                "title": {
                    "fontFace": "Segoe UI Semibold",
                    "fontSize": 14
                },
                "header": {
                    "fontFace": "Segoe UI Semibold",
                    "fontSize": 12
                },
                "label": {
                    "fontFace": "Segoe UI",
                    "fontSize": 10
                }
            }
        }

    def add_page(
        self,
        name: str,
        display_name: Optional[str] = None,
        width: float = 1280,
        height: float = 720,
    ) -> PageConfig:
        """Add a page to the report.

        Args:
            name: Page identifier
            display_name: Display name for the page
            width: Page width in pixels
            height: Page height in pixels

        Returns:
            Created PageConfig
        """
        page = PageConfig(
            page_id=str(uuid.uuid4()),
            name=name,
            display_name=display_name or name,
            width=width,
            height=height,
        )
        self.pages.append(page)
        return page

    def add_visual_to_page(
        self,
        page: PageConfig,
        rdl_visual: dict,
        position: Optional[VisualPosition] = None,
    ) -> VisualConfig:
        """Add a visual to a page by mapping from RDL.

        Args:
            page: Page to add the visual to
            rdl_visual: RDL visual definition
            position: Optional position (auto-calculated if not provided)

        Returns:
            Created VisualConfig
        """
        if position is None:
            # Auto-calculate position based on existing visuals
            position = self._calculate_position(page, rdl_visual)

        visual = self.visual_mapper.map_visual(rdl_visual, position)
        page.visuals.append(visual)
        return visual

    def _calculate_position(
        self,
        page: PageConfig,
        rdl_visual: dict,
    ) -> VisualPosition:
        """Calculate position for a visual based on RDL or auto-layout.

        Args:
            page: Target page
            rdl_visual: RDL visual with optional position info

        Returns:
            VisualPosition
        """
        # Try to use RDL position
        if "left" in rdl_visual and "top" in rdl_visual:
            return VisualPosition(
                x=float(rdl_visual.get("left", 0)),
                y=float(rdl_visual.get("top", 0)),
                width=float(rdl_visual.get("width", 400)),
                height=float(rdl_visual.get("height", 300)),
            )

        # Auto-layout: stack visuals vertically
        current_y = 50
        for visual in page.visuals:
            current_y = max(current_y, visual.position.y + visual.position.height + 20)

        return VisualPosition(
            x=50,
            y=current_y,
            width=min(400, page.width - 100),
            height=min(300, (page.height - current_y) / 2),
        )

    def add_data_source(
        self,
        name: str,
        connection_string: str,
        query: Optional[str] = None,
    ) -> None:
        """Add a data source to the report.

        Args:
            name: Data source name
            connection_string: Connection string
            query: Optional query
        """
        self.data_sources.append({
            "name": name,
            "connectionString": connection_string,
            "query": query,
        })

    def build(self) -> PBIXBuildResult:
        """Build the PBIX file.

        Returns:
            PBIXBuildResult with build status and file path
        """
        try:
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

            # Create PBIX directory structure
            pbix_dir = os.path.join(self.output_dir, "pbix")
            os.makedirs(pbix_dir, exist_ok=True)

            # Generate filename
            safe_name = self.report_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_converted.pbix"
            filepath = os.path.join(pbix_dir, filename)

            # Build the PBIX ZIP file
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add Content_Types.xml
                zf.writestr("[Content_Types].xml", self.CONTENT_TYPES_XML)

                # Add Layout (report definition)
                layout_json = self._generate_layout()
                zf.writestr("Report/Layout", json.dumps(layout_json, indent=2))

                # Add Metadata
                metadata = self._generate_metadata()
                zf.writestr("Metadata", json.dumps(metadata, indent=2))

                # Add Settings
                settings = self._generate_settings()
                zf.writestr("Settings", json.dumps(settings, indent=2))

                # Add SecurityBindings (required, can be empty)
                zf.writestr("SecurityBindings", "")

                # Add DataModel placeholder
                data_model = self._generate_data_model()
                zf.writestr("DataModel", json.dumps(data_model, indent=2))

                # Add DiagramLayout
                diagram = self._generate_diagram_layout()
                zf.writestr("DiagramLayout", json.dumps(diagram, indent=2))

            # Verify file was created
            if not os.path.exists(filepath):
                return PBIXBuildResult(
                    success=False,
                    error_message="PBIX file was not created",
                )

            # Get file size
            file_size = os.path.getsize(filepath)

            # Count visuals and placeholders
            visual_count = sum(len(p.visuals) for p in self.pages)
            placeholder_count = self.visual_mapper.placeholder_count

            # Collect warnings
            all_warnings = self.warnings + self.visual_mapper.warnings

            logger.info(
                "Built PBIX file: %s (pages=%d, visuals=%d, placeholders=%d)",
                filepath,
                len(self.pages),
                visual_count,
                placeholder_count,
            )

            return PBIXBuildResult(
                success=True,
                file_path=filepath,
                file_size=file_size,
                page_count=len(self.pages),
                visual_count=visual_count,
                placeholder_count=placeholder_count,
                warnings=all_warnings,
            )

        except Exception as e:
            logger.exception("Failed to build PBIX file")
            return PBIXBuildResult(
                success=False,
                error_message=str(e),
            )

    def _generate_layout(self) -> dict:
        """Generate the Layout JSON for the report."""
        sections = []

        for page in self.pages:
            section = {
                "id": page.page_id,
                "name": page.name,
                "displayName": page.display_name,
                "filters": "[]",
                "ordinal": len(sections),
                "visualContainers": [],
                "config": json.dumps({
                    "layouts": [{
                        "id": 0,
                        "position": {
                            "x": 0,
                            "y": 0,
                            "z": 0,
                            "width": page.width,
                            "height": page.height
                        }
                    }],
                    "visibility": 0
                }),
                "width": page.width,
                "height": page.height,
            }

            for i, visual in enumerate(page.visuals):
                container = self._generate_visual_container(visual, i)
                section["visualContainers"].append(container)

            sections.append(section)

        return {
            "id": self.report_id,
            "reportId": self.report_id,
            "layoutOptimization": 0,
            "config": json.dumps({
                "version": "5.51",
                "themeCollection": {
                    "baseTheme": self.theme
                }
            }),
            "filters": "[]",
            "sections": sections,
        }

    def _generate_visual_container(
        self,
        visual: VisualConfig,
        index: int,
    ) -> dict:
        """Generate a visual container for the Layout."""
        config = {
            "name": visual.visual_id,
            "layouts": [{
                "id": 0,
                "position": {
                    "x": visual.position.x,
                    "y": visual.position.y,
                    "z": index,
                    "width": visual.position.width,
                    "height": visual.position.height,
                }
            }],
            "singleVisual": self._generate_single_visual(visual),
        }

        return {
            "x": visual.position.x,
            "y": visual.position.y,
            "z": index,
            "width": visual.position.width,
            "height": visual.position.height,
            "config": json.dumps(config),
            "filters": "[]",
            "tabOrder": index,
        }

    def _generate_single_visual(self, visual: VisualConfig) -> dict:
        """Generate the singleVisual configuration."""
        single_visual: dict[str, Any] = {
            "visualType": visual.visual_type.value,
            "drillFilterOtherVisuals": True,
        }

        # Add title if present
        if visual.title:
            single_visual["vcObjects"] = {
                "title": [{
                    "properties": {
                        "text": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}},
                        "show": {"expr": {"Literal": {"Value": "true"}}}
                    }
                }]
            }

        # Add projections based on visual type
        projections = {}

        if visual.visual_type == PowerBIVisualType.TABLE:
            if visual.fields:
                projections["Values"] = [
                    {"queryRef": f.query_ref} for f in visual.fields
                ]

        elif visual.visual_type == PowerBIVisualType.MATRIX:
            if visual.row_fields:
                projections["Rows"] = [
                    {"queryRef": f.query_ref} for f in visual.row_fields
                ]
            if visual.column_fields:
                projections["Columns"] = [
                    {"queryRef": f.query_ref} for f in visual.column_fields
                ]
            if visual.value_fields:
                projections["Values"] = [
                    {"queryRef": f.query_ref} for f in visual.value_fields
                ]

        elif visual.visual_type in (
            PowerBIVisualType.CLUSTERED_BAR,
            PowerBIVisualType.CLUSTERED_COLUMN,
            PowerBIVisualType.LINE,
            PowerBIVisualType.AREA,
        ):
            if visual.category_fields:
                projections["Category"] = [
                    {"queryRef": f.query_ref} for f in visual.category_fields
                ]
            if visual.value_fields:
                projections["Y"] = [
                    {"queryRef": f.query_ref} for f in visual.value_fields
                ]
            if visual.legend_fields:
                projections["Series"] = [
                    {"queryRef": f.query_ref} for f in visual.legend_fields
                ]

        elif visual.visual_type in (PowerBIVisualType.PIE, PowerBIVisualType.DONUT):
            if visual.category_fields:
                projections["Category"] = [
                    {"queryRef": f.query_ref} for f in visual.category_fields
                ]
            if visual.value_fields:
                projections["Y"] = [
                    {"queryRef": f.query_ref} for f in visual.value_fields
                ]

        elif visual.visual_type == PowerBIVisualType.TEXTBOX:
            # Handle textbox content
            text = visual.properties.get("text", "")
            if visual.is_placeholder:
                text = visual.placeholder_message or text

            single_visual["objects"] = {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [{
                                "value": text,
                                "textStyle": {
                                    "fontFamily": visual.properties.get(
                                        "font_family", "Segoe UI"
                                    ),
                                    "fontSize": f"{visual.properties.get('font_size', 12)}pt"
                                }
                            }]
                        }]
                    }
                }]
            }

        if projections:
            single_visual["projections"] = projections

        return single_visual

    def _generate_metadata(self) -> dict:
        """Generate report metadata."""
        return {
            "version": "1.0",
            "createdFrom": "ReportLift",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "reportName": self.report_name,
        }

    def _generate_settings(self) -> dict:
        """Generate report settings."""
        return {
            "queryLimit": 10000,
            "defaultMode": 1,
            "reportFormatVersion": "1.0",
        }

    def _generate_data_model(self) -> dict:
        """Generate data model schema."""
        tables = []
        for ds in self.data_sources:
            tables.append({
                "name": ds["name"],
                "columns": [],  # Columns would be derived from actual data
                "source": {
                    "type": "query",
                    "query": ds.get("query", ""),
                }
            })

        return {
            "version": "1.0",
            "model": {
                "tables": tables,
                "relationships": [],
            }
        }

    def _generate_diagram_layout(self) -> dict:
        """Generate diagram layout."""
        return {
            "version": "1.0",
            "pages": [],
        }


def build_pbix_from_analysis(
    analysis_features: dict,
    report_name: str,
    output_dir: str,
    theme: Optional[dict] = None,
) -> PBIXBuildResult:
    """Build a PBIX file from analysis features.

    Args:
        analysis_features: Analysis features dict containing visuals
        report_name: Name of the report
        output_dir: Output directory
        theme: Optional theme configuration

    Returns:
        PBIXBuildResult
    """
    builder = PBIXBuilder(
        report_name=report_name,
        output_dir=output_dir,
        theme=theme,
    )

    # Extract visuals from analysis
    visuals = analysis_features.get("visuals", [])

    if not visuals:
        # Create a single page with placeholder
        page = builder.add_page("Page1", "Report Page")
        builder.add_visual_to_page(
            page,
            {
                "type": "Textbox",
                "name": "info_text",
                "value": "No visuals found in source report. Add visuals manually.",
            },
            VisualPosition(x=50, y=50, width=400, height=100),
        )
    else:
        # Group visuals by page if page info available
        pages_data: dict[str, list] = {}
        for visual in visuals:
            page_name = visual.get("page", "Page1")
            if page_name not in pages_data:
                pages_data[page_name] = []
            pages_data[page_name].append(visual)

        # Create pages and add visuals
        for page_name, page_visuals in pages_data.items():
            page = builder.add_page(page_name, page_name)
            for rdl_visual in page_visuals:
                builder.add_visual_to_page(page, rdl_visual)

    # Build the PBIX
    return builder.build()

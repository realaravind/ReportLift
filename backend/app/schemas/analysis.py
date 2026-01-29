"""Analysis Pydantic schemas for RDL feature extraction."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Type of query in a dataset."""

    EMBEDDED_SQL = "embedded_sql"
    STORED_PROCEDURE = "stored_procedure"
    SHARED_DATASET = "shared_dataset"


class VisualType(str, Enum):
    """Type of visual element in a report."""

    TABLIX = "tablix"
    TABLE = "table"
    MATRIX = "matrix"
    CHART = "chart"
    GAUGE = "gauge"
    MAP = "map"
    SUBREPORT = "subreport"
    TEXTBOX = "textbox"
    IMAGE = "image"
    RECTANGLE = "rectangle"
    LINE = "line"
    LIST = "list"


class ExpressionCategory(str, Enum):
    """Category of an expression based on complexity."""

    FIELD_REFERENCE = "field_reference"
    SIMPLE_AGGREGATE = "simple_aggregate"
    COMPLEX_AGGREGATE = "complex_aggregate"
    LOOKUP = "lookup"
    CUSTOM_CODE = "custom_code"
    RUNNING_VALUE = "running_value"
    ROW_NUMBER = "row_number"
    PREVIOUS = "previous"
    UNKNOWN = "unknown"


class DatasetParameter(BaseModel):
    """A parameter used in a dataset query."""

    name: str
    data_type: str | None = None
    default_value: str | None = None


class DatasetField(BaseModel):
    """A field returned by a dataset."""

    name: str
    data_type: str | None = None
    source_field: str | None = None


class DatasetFeature(BaseModel):
    """Features extracted from a report dataset."""

    name: str
    query_type: QueryType
    stored_procedure_name: str | None = None
    command_text: str | None = None
    data_source_name: str | None = None
    parameter_count: int = 0
    field_count: int = 0
    parameters: list[DatasetParameter] = Field(default_factory=list)
    fields: list[DatasetField] = Field(default_factory=list)


class GroupingInfo(BaseModel):
    """Information about grouping in a Tablix."""

    name: str
    expression: str | None = None
    is_recursive: bool = False


class VisualFeature(BaseModel):
    """Features extracted from a visual element."""

    type: VisualType
    name: str
    dataset_name: str | None = None
    row_groups: int = 0
    column_groups: int = 0
    has_recursive_group: bool = False
    nested_item_count: int = 0
    row_group_details: list[GroupingInfo] = Field(default_factory=list)
    column_group_details: list[GroupingInfo] = Field(default_factory=list)
    subreport_path: str | None = None  # For subreports


class ExpressionFeature(BaseModel):
    """Features extracted from an expression."""

    expression: str
    category: ExpressionCategory
    location: str  # XPath or description of where found
    item_name: str | None = None
    function_calls: list[str] = Field(default_factory=list)


class CustomCodeFunction(BaseModel):
    """A function defined in custom VB.NET code."""

    name: str
    parameters: list[str] = Field(default_factory=list)
    is_public: bool = True
    line_count: int = 0


class LayoutFeature(BaseModel):
    """Layout features of the report."""

    page_width: str | None = None  # e.g., "8.5in"
    page_height: str | None = None  # e.g., "11in"
    page_width_inches: float | None = None
    page_height_inches: float | None = None
    orientation: str = "Portrait"  # Portrait or Landscape
    has_header: bool = False
    has_footer: bool = False
    header_height: str | None = None
    footer_height: str | None = None
    column_count: int = 1
    left_margin: str | None = None
    right_margin: str | None = None
    top_margin: str | None = None
    bottom_margin: str | None = None


class AnalysisFeatures(BaseModel):
    """Complete feature extraction from an RDL file."""

    # Metadata
    rdl_version: str
    report_name: str | None = None
    report_description: str | None = None
    author: str | None = None

    # Extracted features
    datasets: list[DatasetFeature] = Field(default_factory=list)
    visuals: list[VisualFeature] = Field(default_factory=list)
    expressions: list[ExpressionFeature] = Field(default_factory=list)
    layout: LayoutFeature | None = None

    # Custom code
    custom_code: str | None = None
    custom_code_functions: list[CustomCodeFunction] = Field(default_factory=list)

    # Report parameters (not dataset parameters)
    report_parameters: list[DatasetParameter] = Field(default_factory=list)

    # Data sources
    data_sources: list[str] = Field(default_factory=list)

    # Summary counts for quick reference
    dataset_count: int = 0
    stored_procedure_count: int = 0
    visual_count: int = 0
    expression_count: int = 0
    subreport_count: int = 0
    running_value_count: int = 0
    custom_code_function_count: int = 0
    parameter_count: int = 0
    chart_count: int = 0
    table_count: int = 0
    matrix_count: int = 0
    map_count: int = 0
    gauge_count: int = 0

    # Feature flags
    has_custom_code: bool = False
    has_stored_procedures: bool = False
    has_subreports: bool = False
    has_recursive_groups: bool = False
    has_lookup_expressions: bool = False
    has_running_values: bool = False

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for backward compatibility with scoring.

        This maintains compatibility with the existing _calculate_score and
        _classify_report functions during the transition period.
        """
        return {
            "data_sources": len(self.data_sources),
            "datasets": self.dataset_count,
            "parameters": self.parameter_count,
            "tables": self.table_count,
            "matrices": self.matrix_count,
            "charts": self.chart_count,
            "subreports": self.subreport_count,
            "custom_code": self.has_custom_code,
            "expressions": self.expression_count,
            "stored_procedures": self.stored_procedure_count,
            "has_grouping": any(
                v.row_groups > 0 or v.column_groups > 0 for v in self.visuals
            ),
            "has_sorting": False,  # TODO: detect sorting
            "has_filters": False,  # TODO: detect filters
            "page_breaks": 0,  # TODO: detect page breaks
            "images": sum(1 for v in self.visuals if v.type == VisualType.IMAGE),
            "rectangles": sum(1 for v in self.visuals if v.type == VisualType.RECTANGLE),
            "textboxes": sum(1 for v in self.visuals if v.type == VisualType.TEXTBOX),
            "lines": sum(1 for v in self.visuals if v.type == VisualType.LINE),
        }


class RDLParseError(Exception):
    """Exception raised when RDL parsing fails."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        details: str | None = None,
    ):
        self.message = message
        self.line_number = line_number
        self.column = column
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.line_number is not None:
            parts.append(f"line {self.line_number}")
        if self.column is not None:
            parts.append(f"column {self.column}")
        if self.details:
            parts.append(f"({self.details})")
        return " - ".join(parts)

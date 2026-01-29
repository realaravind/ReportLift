"""RDL Parser Service - Comprehensive RDL XML parsing and feature extraction.

This module provides a complete RDL (Report Definition Language) parser that
extracts features from SSRS report definition files for analysis and scoring.
"""

import logging
import re
from typing import Any

from lxml import etree

from app.schemas.analysis import (
    AnalysisFeatures,
    CustomCodeFunction,
    DatasetFeature,
    DatasetField,
    DatasetParameter,
    ExpressionCategory,
    ExpressionFeature,
    GroupingInfo,
    LayoutFeature,
    QueryType,
    RDLParseError,
    VisualFeature,
    VisualType,
)

logger = logging.getLogger(__name__)

# RDL namespace mappings for different SSRS versions
RDL_NAMESPACES = {
    "2005": "http://schemas.microsoft.com/sqlserver/reporting/2005/01/reportdefinition",
    "2008": "http://schemas.microsoft.com/sqlserver/reporting/2008/01/reportdefinition",
    "2010": "http://schemas.microsoft.com/sqlserver/reporting/2010/01/reportdefinition",
    "2016": "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition",
}

# Expression detection patterns
EXPRESSION_PATTERNS = {
    ExpressionCategory.FIELD_REFERENCE: re.compile(
        r"^=Fields!(\w+)\.Value$", re.IGNORECASE
    ),
    ExpressionCategory.SIMPLE_AGGREGATE: re.compile(
        r"^=(Sum|Count|Avg|Min|Max|First|Last)\(Fields!", re.IGNORECASE
    ),
    ExpressionCategory.RUNNING_VALUE: re.compile(r"RunningValue\(", re.IGNORECASE),
    ExpressionCategory.LOOKUP: re.compile(
        r"(Lookup|LookupSet|MultiLookup)\(", re.IGNORECASE
    ),
    ExpressionCategory.CUSTOM_CODE: re.compile(r"Code\.\w+\(", re.IGNORECASE),
    ExpressionCategory.ROW_NUMBER: re.compile(r"RowNumber\(", re.IGNORECASE),
    ExpressionCategory.PREVIOUS: re.compile(r"Previous\(", re.IGNORECASE),
}

# VB function extraction pattern
VB_FUNCTION_PATTERN = re.compile(
    r"(?:Public\s+|Private\s+)?(?:Shared\s+)?Function\s+(\w+)\s*\(([^)]*)\)",
    re.IGNORECASE | re.MULTILINE,
)


class RDLParser:
    """Parses RDL XML files and extracts analysis features."""

    def __init__(self, rdl_content: str | bytes):
        """Initialize the parser with RDL content.

        Args:
            rdl_content: RDL XML content as string or bytes

        Raises:
            RDLParseError: If the XML cannot be parsed
        """
        self.rdl_content = rdl_content
        self.tree: etree._Element | None = None
        self.namespace: str = ""
        self.ns: dict[str, str] = {}
        self.version: str = "unknown"

        self._parse_xml()
        self._detect_namespace()

    def _parse_xml(self) -> None:
        """Parse the XML content."""
        try:
            if isinstance(self.rdl_content, str):
                content = self.rdl_content.encode("utf-8")
            else:
                content = self.rdl_content

            # Remove BOM if present
            if content.startswith(b"\xef\xbb\xbf"):
                content = content[3:]

            self.tree = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            raise RDLParseError(
                message="Invalid RDL XML format",
                line_number=e.lineno if hasattr(e, "lineno") else None,
                column=e.offset if hasattr(e, "offset") else None,
                details=str(e),
            ) from e
        except Exception as e:
            raise RDLParseError(
                message="Failed to parse RDL content",
                details=str(e),
            ) from e

    def _detect_namespace(self) -> None:
        """Detect the RDL namespace version from the root element."""
        if self.tree is None:
            raise RDLParseError("XML tree not initialized")

        # Get namespace from root element
        root_ns = self.tree.nsmap.get(None)
        if not root_ns:
            # Try to get from tag
            if self.tree.tag.startswith("{"):
                root_ns = self.tree.tag.split("}")[0][1:]

        if not root_ns:
            raise RDLParseError("No RDL namespace found in document")

        # Detect version from namespace
        for version, ns_uri in RDL_NAMESPACES.items():
            if ns_uri == root_ns:
                self.version = version
                self.namespace = ns_uri
                self.ns = {"rd": ns_uri}
                return

        # Unknown namespace - use it anyway
        logger.warning("Unknown RDL namespace: %s", root_ns)
        self.namespace = root_ns
        self.ns = {"rd": root_ns}
        self.version = "unknown"

    def _find(self, xpath: str) -> list[etree._Element]:
        """Find elements using XPath with namespace."""
        if self.tree is None:
            return []
        try:
            return self.tree.xpath(xpath, namespaces=self.ns)
        except Exception:
            # Try without namespace
            return self.tree.xpath(xpath.replace("rd:", ""))

    def _find_all(self, tag: str) -> list[etree._Element]:
        """Find all elements with a tag, handling namespace."""
        if self.tree is None:
            return []
        # Try with namespace first
        results = self.tree.findall(f".//{{{self.namespace}}}{tag}")
        if not results:
            # Try with XPath using namespace wildcard
            try:
                results = self.tree.xpath(f".//*[local-name()='{tag}']")
            except Exception:
                # Fallback: iterate and match tag names
                results = []
                for elem in self.tree.iter():
                    elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if elem_tag == tag:
                        results.append(elem)
        return results

    def _get_text(self, element: etree._Element, tag: str) -> str | None:
        """Get text content of a child element."""
        child = element.find(f"{{{self.namespace}}}{tag}")
        if child is None:
            # Try wildcard
            for c in element:
                if c.tag.endswith(f"}}{tag}") or c.tag == tag:
                    return c.text
            return None
        return child.text

    def _get_element(
        self, parent: etree._Element, tag: str
    ) -> etree._Element | None:
        """Get a child element by tag."""
        child = parent.find(f"{{{self.namespace}}}{tag}")
        if child is None:
            for c in parent:
                if c.tag.endswith(f"}}{tag}") or c.tag == tag:
                    return c
        return child

    def extract_datasets(self) -> list[DatasetFeature]:
        """Extract dataset features from the RDL."""
        datasets = []

        for ds_elem in self._find_all("DataSet"):
            name = ds_elem.get("Name", "Unknown")

            # Get query information
            query_elem = self._get_element(ds_elem, "Query")
            query_type = QueryType.EMBEDDED_SQL
            command_text = None
            sp_name = None
            data_source_name = None

            if query_elem is not None:
                # Get data source reference
                data_source_name = self._get_text(query_elem, "DataSourceName")

                # Get command type
                cmd_type = self._get_text(query_elem, "CommandType")
                command_text = self._get_text(query_elem, "CommandText")

                if cmd_type and cmd_type.lower() == "storedprocedure":
                    query_type = QueryType.STORED_PROCEDURE
                    sp_name = command_text
                elif command_text:
                    # Check if it's an EXEC statement
                    text_upper = command_text.upper().strip()
                    if text_upper.startswith("EXEC ") or text_upper.startswith(
                        "EXECUTE "
                    ):
                        query_type = QueryType.STORED_PROCEDURE
                        # Extract SP name
                        match = re.search(
                            r"EXEC(?:UTE)?\s+(\[?[\w.]+\]?)", command_text, re.IGNORECASE
                        )
                        if match:
                            sp_name = match.group(1).strip("[]")

            # Check for shared dataset reference
            shared_ds = self._get_element(ds_elem, "SharedDataSet")
            if shared_ds is not None:
                query_type = QueryType.SHARED_DATASET
                shared_ref = self._get_element(shared_ds, "SharedDataSetReference")
                if shared_ref is not None and shared_ref.text:
                    sp_name = shared_ref.text

            # Extract parameters
            parameters = []
            query_params = self._get_element(ds_elem, "QueryParameters")
            if query_params is None and query_elem is not None:
                query_params = self._get_element(query_elem, "QueryParameters")

            if query_params is not None:
                for param_elem in query_params:
                    if param_elem.tag.endswith("QueryParameter"):
                        param_name = param_elem.get("Name", "")
                        param_value = self._get_text(param_elem, "Value")
                        parameters.append(
                            DatasetParameter(
                                name=param_name,
                                default_value=param_value,
                            )
                        )

            # Extract fields
            fields = []
            fields_elem = self._get_element(ds_elem, "Fields")
            if fields_elem is not None:
                for field_elem in fields_elem:
                    if field_elem.tag.endswith("Field"):
                        field_name = field_elem.get("Name", "")
                        data_field = self._get_text(field_elem, "DataField")
                        type_name = self._get_text(field_elem, "TypeName")
                        fields.append(
                            DatasetField(
                                name=field_name,
                                data_type=type_name,
                                source_field=data_field,
                            )
                        )

            datasets.append(
                DatasetFeature(
                    name=name,
                    query_type=query_type,
                    stored_procedure_name=sp_name,
                    command_text=command_text[:500] if command_text else None,
                    data_source_name=data_source_name,
                    parameter_count=len(parameters),
                    field_count=len(fields),
                    parameters=parameters,
                    fields=fields,
                )
            )

        return datasets

    def extract_visuals(self) -> list[VisualFeature]:
        """Extract visual element features from the RDL."""
        visuals = []

        # Map of RDL elements to visual types
        visual_mappings = [
            ("Tablix", VisualType.TABLIX),
            ("Table", VisualType.TABLE),
            ("Matrix", VisualType.MATRIX),
            ("Chart", VisualType.CHART),
            ("Gauge", VisualType.GAUGE),
            ("Map", VisualType.MAP),
            ("Subreport", VisualType.SUBREPORT),
            ("Textbox", VisualType.TEXTBOX),
            ("Image", VisualType.IMAGE),
            ("Rectangle", VisualType.RECTANGLE),
            ("Line", VisualType.LINE),
            ("List", VisualType.LIST),
        ]

        for tag, visual_type in visual_mappings:
            for elem in self._find_all(tag):
                name = elem.get("Name", f"Unnamed{tag}")

                # Get dataset name if applicable
                dataset_name = self._get_text(elem, "DataSetName")

                # For Tablix, extract grouping information
                row_groups = []
                col_groups = []
                has_recursive = False

                if tag in ("Tablix", "Table", "Matrix", "List"):
                    # Row groups
                    row_hierarchy = self._get_element(elem, "TablixRowHierarchy")
                    if row_hierarchy is not None:
                        row_groups = self._extract_groups(row_hierarchy)

                    # Column groups
                    col_hierarchy = self._get_element(elem, "TablixColumnHierarchy")
                    if col_hierarchy is not None:
                        col_groups = self._extract_groups(col_hierarchy)

                    # Check for recursive groups
                    has_recursive = any(g.is_recursive for g in row_groups + col_groups)

                # Count nested items for rectangles
                nested_count = 0
                if tag == "Rectangle":
                    report_items = self._get_element(elem, "ReportItems")
                    if report_items is not None:
                        nested_count = len(list(report_items))

                # Get subreport path
                subreport_path = None
                if tag == "Subreport":
                    subreport_path = self._get_text(elem, "ReportName")

                visuals.append(
                    VisualFeature(
                        type=visual_type,
                        name=name,
                        dataset_name=dataset_name,
                        row_groups=len(row_groups),
                        column_groups=len(col_groups),
                        has_recursive_group=has_recursive,
                        nested_item_count=nested_count,
                        row_group_details=row_groups,
                        column_group_details=col_groups,
                        subreport_path=subreport_path,
                    )
                )

        return visuals

    def _extract_groups(self, hierarchy: etree._Element) -> list[GroupingInfo]:
        """Extract grouping information from a hierarchy element."""
        groups = []

        # Find all TablixMember elements recursively
        for member in hierarchy.iter():
            if not member.tag.endswith("TablixMember"):
                continue

            group_elem = self._get_element(member, "Group")
            if group_elem is not None:
                group_name = group_elem.get("Name", "")

                # Get group expression
                group_exprs = self._get_element(group_elem, "GroupExpressions")
                expression = None
                if group_exprs is not None:
                    expr_elem = self._get_element(group_exprs, "GroupExpression")
                    if expr_elem is not None:
                        expression = expr_elem.text

                # Check for recursion
                is_recursive = False
                parent_elem = self._get_element(group_elem, "Parent")
                if parent_elem is not None and parent_elem.text:
                    is_recursive = True

                groups.append(
                    GroupingInfo(
                        name=group_name,
                        expression=expression,
                        is_recursive=is_recursive,
                    )
                )

        return groups

    def extract_expressions(self) -> list[ExpressionFeature]:
        """Extract expression features from the RDL."""
        expressions = []

        if self.tree is None:
            return expressions

        # Iterate through all elements looking for expressions
        for elem in self.tree.iter():
            if elem.text and elem.text.strip().startswith("="):
                expr_text = elem.text.strip()
                category = self._categorize_expression(expr_text)

                # Get location info
                location = self._get_element_path(elem)

                # Get parent item name if available
                item_name = self._get_parent_item_name(elem)

                # Extract function calls
                func_calls = self._extract_function_calls(expr_text)

                expressions.append(
                    ExpressionFeature(
                        expression=expr_text[:500],  # Truncate long expressions
                        category=category,
                        location=location,
                        item_name=item_name,
                        function_calls=func_calls,
                    )
                )

        return expressions

    def _categorize_expression(self, expr: str) -> ExpressionCategory:
        """Categorize an expression based on its content."""
        # Check patterns in order of specificity
        for category, pattern in EXPRESSION_PATTERNS.items():
            if pattern.search(expr):
                return category

        # Check for complex aggregate (aggregate with filter)
        if re.search(r"(Sum|Count|Avg|Min|Max)\([^)]+,[^)]+\)", expr, re.IGNORECASE):
            return ExpressionCategory.COMPLEX_AGGREGATE

        # Default to field reference for simple expressions
        if re.match(r"^=Fields!\w+\.", expr, re.IGNORECASE):
            return ExpressionCategory.FIELD_REFERENCE

        return ExpressionCategory.UNKNOWN

    def _extract_function_calls(self, expr: str) -> list[str]:
        """Extract function names called in an expression."""
        # Match function calls like Sum(), Code.MyFunc(), etc.
        pattern = r"(\w+(?:\.\w+)?)\s*\("
        matches = re.findall(pattern, expr)
        return list(set(matches))

    def _get_element_path(self, elem: etree._Element) -> str:
        """Get a simplified path to an element for location reference."""
        parts = []
        current = elem
        for _ in range(5):  # Limit depth
            if current is None:
                break
            tag = current.tag.split("}")[-1] if "}" in current.tag else current.tag
            name = current.get("Name", "")
            if name:
                parts.append(f"{tag}[@Name='{name}']")
            else:
                parts.append(tag)
            current = current.getparent()

        return "/".join(reversed(parts))

    def _get_parent_item_name(self, elem: etree._Element) -> str | None:
        """Get the name of the nearest parent report item."""
        current = elem.getparent()
        report_items = {
            "Tablix",
            "Table",
            "Matrix",
            "Chart",
            "Gauge",
            "Textbox",
            "Rectangle",
            "Subreport",
        }

        while current is not None:
            tag = current.tag.split("}")[-1] if "}" in current.tag else current.tag
            if tag in report_items:
                return current.get("Name")
            current = current.getparent()

        return None

    def extract_custom_code(self) -> tuple[str | None, list[CustomCodeFunction]]:
        """Extract custom VB.NET code and its functions."""
        code_elements = self._find_all("Code")

        code_text = None
        functions = []

        for code_elem in code_elements:
            if code_elem.text and code_elem.text.strip():
                code_text = code_elem.text.strip()

                # Extract functions from the code
                for match in VB_FUNCTION_PATTERN.finditer(code_text):
                    func_name = match.group(1)
                    params_str = match.group(2).strip()
                    params = [p.strip() for p in params_str.split(",") if p.strip()]

                    # Count lines in function (approximate)
                    func_start = match.end()
                    end_match = re.search(
                        r"End\s+Function", code_text[func_start:], re.IGNORECASE
                    )
                    line_count = 0
                    if end_match:
                        func_body = code_text[func_start : func_start + end_match.start()]
                        line_count = len(
                            [l for l in func_body.split("\n") if l.strip()]
                        )

                    functions.append(
                        CustomCodeFunction(
                            name=func_name,
                            parameters=params,
                            is_public="Public" in match.group(0)
                            or "Private" not in match.group(0),
                            line_count=line_count,
                        )
                    )

                break  # Only use first code block

        return code_text, functions

    def extract_layout(self) -> LayoutFeature:
        """Extract layout features from the RDL."""
        layout = LayoutFeature()

        # Find Page element
        page_elements = self._find_all("Page")
        page = page_elements[0] if page_elements else None

        if page is not None:
            layout.page_width = self._get_text(page, "PageWidth")
            layout.page_height = self._get_text(page, "PageHeight")
            layout.left_margin = self._get_text(page, "LeftMargin")
            layout.right_margin = self._get_text(page, "RightMargin")
            layout.top_margin = self._get_text(page, "TopMargin")
            layout.bottom_margin = self._get_text(page, "BottomMargin")
            columns = self._get_text(page, "Columns")
            if columns:
                try:
                    layout.column_count = int(columns)
                except ValueError:
                    pass

        # Try alternative locations for dimensions
        if not layout.page_width:
            layout.page_width = self._get_text(self.tree, "PageWidth") if self.tree is not None else None
        if not layout.page_height:
            layout.page_height = self._get_text(self.tree, "PageHeight") if self.tree is not None else None

        # Convert dimensions to inches for comparison
        if layout.page_width:
            layout.page_width_inches = self._parse_dimension(layout.page_width)
        if layout.page_height:
            layout.page_height_inches = self._parse_dimension(layout.page_height)

        # Determine orientation
        if layout.page_width_inches and layout.page_height_inches:
            if layout.page_width_inches > layout.page_height_inches:
                layout.orientation = "Landscape"
            else:
                layout.orientation = "Portrait"

        # Check for header and footer
        header_elements = self._find_all("PageHeader")
        footer_elements = self._find_all("PageFooter")

        layout.has_header = len(header_elements) > 0
        layout.has_footer = len(footer_elements) > 0

        if header_elements:
            layout.header_height = self._get_text(header_elements[0], "Height")
        if footer_elements:
            layout.footer_height = self._get_text(footer_elements[0], "Height")

        return layout

    def _parse_dimension(self, dim: str) -> float | None:
        """Parse a dimension string (e.g., '8.5in') to inches."""
        if not dim:
            return None

        match = re.match(r"([\d.]+)\s*(in|cm|mm|pt)?", dim.lower())
        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2) or "in"

        # Convert to inches
        if unit == "cm":
            return value / 2.54
        elif unit == "mm":
            return value / 25.4
        elif unit == "pt":
            return value / 72
        return value

    def extract_report_parameters(self) -> list[DatasetParameter]:
        """Extract report-level parameters."""
        parameters = []

        for param_elem in self._find_all("ReportParameter"):
            name = param_elem.get("Name", "")
            data_type = self._get_text(param_elem, "DataType")

            # Get default value
            default_values = self._get_element(param_elem, "DefaultValue")
            default_value = None
            if default_values is not None:
                values = self._get_element(default_values, "Values")
                if values is not None:
                    value_elem = self._get_element(values, "Value")
                    if value_elem is not None:
                        default_value = value_elem.text

            parameters.append(
                DatasetParameter(
                    name=name,
                    data_type=data_type,
                    default_value=default_value,
                )
            )

        return parameters

    def extract_data_sources(self) -> list[str]:
        """Extract data source names."""
        sources = []

        for ds_elem in self._find_all("DataSource"):
            name = ds_elem.get("Name")
            if name:
                sources.append(name)

        return sources

    def extract_report_metadata(self) -> dict[str, str | None]:
        """Extract report metadata like name, description, author."""
        metadata: dict[str, str | None] = {
            "name": None,
            "description": None,
            "author": None,
        }

        if self.tree is None:
            return metadata

        # Try to get from root attributes or child elements
        metadata["name"] = self._get_text(self.tree, "Name") or self.tree.get("Name")
        metadata["description"] = self._get_text(self.tree, "Description")
        metadata["author"] = self._get_text(self.tree, "Author")

        return metadata

    def parse(self) -> AnalysisFeatures:
        """Parse the RDL and extract all features.

        Returns:
            AnalysisFeatures with all extracted data
        """
        # Extract all features
        datasets = self.extract_datasets()
        visuals = self.extract_visuals()
        expressions = self.extract_expressions()
        layout = self.extract_layout()
        custom_code, custom_code_functions = self.extract_custom_code()
        report_params = self.extract_report_parameters()
        data_sources = self.extract_data_sources()
        metadata = self.extract_report_metadata()

        # Calculate counts
        sp_count = sum(
            1 for d in datasets if d.query_type == QueryType.STORED_PROCEDURE
        )
        subreport_count = sum(1 for v in visuals if v.type == VisualType.SUBREPORT)
        running_value_count = sum(
            1
            for e in expressions
            if e.category == ExpressionCategory.RUNNING_VALUE
        )
        chart_count = sum(1 for v in visuals if v.type == VisualType.CHART)
        table_count = sum(
            1 for v in visuals if v.type in (VisualType.TABLE, VisualType.TABLIX)
        )
        matrix_count = sum(1 for v in visuals if v.type == VisualType.MATRIX)
        map_count = sum(1 for v in visuals if v.type == VisualType.MAP)
        gauge_count = sum(1 for v in visuals if v.type == VisualType.GAUGE)

        # Feature flags
        has_recursive = any(v.has_recursive_group for v in visuals)
        has_lookup = any(
            e.category == ExpressionCategory.LOOKUP for e in expressions
        )

        return AnalysisFeatures(
            rdl_version=self.version,
            report_name=metadata.get("name"),
            report_description=metadata.get("description"),
            author=metadata.get("author"),
            datasets=datasets,
            visuals=visuals,
            expressions=expressions,
            layout=layout,
            custom_code=custom_code,
            custom_code_functions=custom_code_functions,
            report_parameters=report_params,
            data_sources=data_sources,
            # Counts
            dataset_count=len(datasets),
            stored_procedure_count=sp_count,
            visual_count=len(visuals),
            expression_count=len(expressions),
            subreport_count=subreport_count,
            running_value_count=running_value_count,
            custom_code_function_count=len(custom_code_functions),
            parameter_count=len(report_params),
            chart_count=chart_count,
            table_count=table_count,
            matrix_count=matrix_count,
            map_count=map_count,
            gauge_count=gauge_count,
            # Flags
            has_custom_code=bool(custom_code),
            has_stored_procedures=sp_count > 0,
            has_subreports=subreport_count > 0,
            has_recursive_groups=has_recursive,
            has_lookup_expressions=has_lookup,
            has_running_values=running_value_count > 0,
        )


def parse_rdl(rdl_content: str | bytes) -> AnalysisFeatures:
    """Convenience function to parse RDL content.

    Args:
        rdl_content: RDL XML content as string or bytes

    Returns:
        AnalysisFeatures with all extracted data

    Raises:
        RDLParseError: If parsing fails
    """
    parser = RDLParser(rdl_content)
    return parser.parse()

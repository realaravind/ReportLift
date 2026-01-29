"""TODO Generator Service - Creates actionable TODO items from analysis results."""

import logging
from uuid import UUID, uuid4

from app.schemas.analysis import AnalysisFeatures, VisualFeature, VisualType
from app.schemas.code_analysis import (
    CodeAnalysisResult,
    ExpressionAnalysis,
    ExpressionConversionCategory,
    SPComplexity,
    StoredProcedureAnalysis,
    VBFunctionAnalysis,
    VBPatternCategory,
)
from app.schemas.todo import (
    TodoCategory,
    TodoItem,
    TodoItemCreate,
    TodoListResponse,
    TodoPriority,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Guidance Templates
# =============================================================================

SP_GUIDANCE = {
    SPComplexity.SIMPLE: """This stored procedure appears simple with few parameters. Steps to convert:
1. Identify the core SELECT statement within the SP
2. Replace parameter references with Snowflake session variables or Power BI parameters
3. Update SQL Server-specific functions to Snowflake equivalents
4. Test the resulting query against sample data""",
    SPComplexity.MODERATE: """This stored procedure has moderate complexity. Consider:
1. Extract the main SELECT statement(s)
2. If multiple SELECTs exist, consider UNION or CTEs
3. Convert any temp table logic to CTEs
4. Replace parameters with session variables or Power BI parameters
5. Thoroughly test with edge cases""",
    SPComplexity.COMPLEX: """This stored procedure has complex logic requiring careful analysis:
1. Document the business logic and expected outputs
2. Consider breaking into multiple queries if needed
3. Cursors must be replaced with set-based operations
4. Dynamic SQL needs manual rewriting
5. Consider using AI-assisted conversion for better results
6. Extensive testing is required after conversion""",
}

EXPRESSION_GUIDANCE = {
    "lookup": """Lookup expressions need conversion to DAX RELATED or LOOKUPVALUE:
- If data is in the same model: Use RELATED([Column])
- If cross-table lookup: Use LOOKUPVALUE([ResultColumn], [SearchColumn], [SearchValue])
- Ensure proper relationships exist between tables""",
    "lookupset": """LookupSet expressions require DAX CONCATENATEX with filtering:
- Use CONCATENATEX(FILTER(Table, Condition), [Column], ", ")
- Consider if all values are needed or just the first/last
- Performance may vary with large datasets""",
    "multilookup": """MultiLookup expressions need custom DAX measures:
- Create a measure that handles multiple value matching
- Consider using SWITCH or nested IF statements
- May need a supporting calculated column""",
    "previous": """Previous() expressions need DAX with EARLIER or calculated columns:
- For row-by-row comparisons: Create a calculated column with EARLIER()
- For running comparisons: Use CALCULATE with FILTER
- Consider the sort order requirements""",
    "running_value": """RunningValue requires Power BI window functions (DAX):
- Consider WINDOW functions in Power BI (2023+)
- Alternative: Create a calculated column with EARLIER()
- For cumulative sums: Use CALCULATE with FILTER(ALL())""",
    "row_number_scoped": """RowNumber with scope requires DAX INDEX or RANKX:
- Use RANKX for ranking within groups
- INDEX function (Power BI 2023+) provides row numbering
- Ensure sort order matches the original SSRS behavior""",
    "custom_code": """Custom VB code must be rewritten as DAX measures:
1. Identify what the function calculates
2. Create a new DAX measure with equivalent logic
3. DAX does not support procedural code - restructure as calculations
4. Test with known inputs/outputs from SSRS""",
    "aggregate_with_scope": """Aggregates with scope need DAX CALCULATE with filters:
- Use CALCULATE(SUM([Column]), FILTER(Table, Condition))
- Scope translates to filter context in DAX
- Consider using ALLEXCEPT for partial scope""",
    "report_items": """ReportItems references have no direct DAX equivalent:
- If referencing another textbox value, restructure as a measure
- Consider bookmarks or parameters for cross-visual references
- May need to restructure report layout""",
    "globals": """Globals references map to Power BI built-in functions:
- Globals!PageNumber -> Not available in visuals; use paginated reports
- Globals!TotalPages -> Not available in standard Power BI
- Globals!ExecutionTime -> Use NOW() function
- Globals!ReportName -> Use a parameter or hardcoded value""",
    "user": """User references map to Power BI user functions:
- User!UserID -> Use USERPRINCIPALNAME() or USERNAME()
- For RLS: Use USERPRINCIPALNAME() in security filters
- Note: Results differ between Service and Desktop""",
    "default": """This expression needs manual review and conversion:
1. Analyze the expression logic
2. Identify DAX equivalents for each function
3. Test the converted expression with sample data""",
}

SUBREPORT_GUIDANCE = """Subreports must be converted separately:
1. Locate and analyze the subreport RDL file
2. Convert subreport independently using this tool
3. In Power BI, consider:
   - Embedding as a separate page with drill-through
   - Using bookmarks for navigation
   - Creating a paginated report if exact layout needed
4. Parameter passing requires careful mapping to Power BI filters"""

VISUAL_GUIDANCE = {
    VisualType.MAP: """SSRS Map visuals are not directly supported in Power BI Desktop:
- Use Power BI's built-in Map or Filled Map visuals
- Consider Azure Maps visual for advanced scenarios
- Data may need geocoding (latitude/longitude)
- Shape maps require TopoJSON files for custom regions""",
    VisualType.GAUGE: """SSRS Gauge visuals require recreation in Power BI:
- Use Power BI's Gauge visual for single-value KPIs
- Consider KPI visual for target comparisons
- Card visuals work well for simple metrics
- Custom visuals available in AppSource for advanced gauges""",
}

VB_PATTERN_GUIDANCE = {
    VBPatternCategory.DATE_FORMATTING: "Uses date formatting - consider DAX FORMAT() and DATE functions",
    VBPatternCategory.STRING_MANIPULATION: "Uses string manipulation - map to DAX text functions (LEFT, RIGHT, MID, etc.)",
    VBPatternCategory.MATH_OPERATIONS: "Uses math operations - most have direct DAX equivalents (ROUND, ABS, etc.)",
    VBPatternCategory.CONDITIONAL_LOGIC: "Uses conditional logic - convert to DAX IF() or SWITCH()",
    VBPatternCategory.NULL_HANDLING: "Handles null values - use DAX ISBLANK() or COALESCE()",
    VBPatternCategory.ERROR_HANDLING: "Has error handling - DAX uses IFERROR() for error handling",
    VBPatternCategory.COLLECTION_OPERATIONS: "Uses collections - may need significant restructuring for DAX",
}


# =============================================================================
# TODO Generator Service
# =============================================================================


class TodoGenerator:
    """Generates actionable TODO items from analysis results."""

    def generate_todos(
        self,
        analysis_id: UUID,
        features: AnalysisFeatures,
        code_analysis: CodeAnalysisResult,
    ) -> list[TodoItemCreate]:
        """Generate TODO items from analysis results.

        Args:
            analysis_id: UUID of the analysis record
            features: Parsed RDL features
            code_analysis: Code analysis results

        Returns:
            List of TodoItemCreate objects sorted by priority
        """
        todos: list[TodoItemCreate] = []

        # Stored procedures (High priority)
        todos.extend(
            self._generate_sp_todos(analysis_id, code_analysis.stored_procedures)
        )

        # Custom VB code (High priority)
        todos.extend(
            self._generate_custom_code_todos(analysis_id, code_analysis.vb_functions)
        )

        # Expressions requiring attention (High for manual, Medium for partial)
        todos.extend(
            self._generate_expression_todos(analysis_id, code_analysis.expressions)
        )

        # Subreports (Medium priority)
        todos.extend(self._generate_subreport_todos(analysis_id, features.visuals))

        # Unsupported visuals (Medium priority)
        todos.extend(self._generate_visual_todos(analysis_id, features.visuals))

        # Sort by priority (High first), then by category
        priority_order = {
            TodoPriority.HIGH: 0,
            TodoPriority.MEDIUM: 1,
            TodoPriority.LOW: 2,
        }
        todos.sort(key=lambda t: (priority_order[t.priority], t.category.value))

        logger.info("Generated %d TODO items for analysis %s", len(todos), analysis_id)
        return todos

    def _generate_sp_todos(
        self, analysis_id: UUID, sps: list[StoredProcedureAnalysis]
    ) -> list[TodoItemCreate]:
        """Generate TODOs for stored procedures."""
        todos = []
        for sp in sps:
            guidance = SP_GUIDANCE.get(sp.complexity, SP_GUIDANCE[SPComplexity.COMPLEX])
            datasets_str = ", ".join(sp.datasets_using)
            params_str = (
                f"Parameters: {', '.join(sp.parameters)}"
                if sp.parameters
                else "No parameters"
            )

            todos.append(
                TodoItemCreate(
                    analysis_id=analysis_id,
                    title=f"Convert stored procedure '{sp.name}' to SELECT statement",
                    category=TodoCategory.STORED_PROCEDURE,
                    priority=TodoPriority.HIGH,
                    location=f"Datasets: {datasets_str}",
                    item_name=sp.name,
                    guidance=guidance,
                    original_content=f"{params_str} | Complexity: {sp.complexity.value}",
                )
            )
        return todos

    def _generate_expression_todos(
        self, analysis_id: UUID, expressions: list[ExpressionAnalysis]
    ) -> list[TodoItemCreate]:
        """Generate TODOs for expressions requiring attention."""
        todos = []
        for expr in expressions:
            # Skip auto-convertible expressions
            if expr.category == ExpressionConversionCategory.AUTO:
                continue

            # Determine priority
            priority = (
                TodoPriority.HIGH
                if expr.category == ExpressionConversionCategory.MANUAL
                else TodoPriority.MEDIUM
            )

            # Get title and guidance based on pattern
            title = self._get_expression_title(expr)
            guidance = self._get_expression_guidance(expr)

            todos.append(
                TodoItemCreate(
                    analysis_id=analysis_id,
                    title=title,
                    category=TodoCategory.EXPRESSION,
                    priority=priority,
                    location=expr.location,
                    item_name=expr.item_name,
                    guidance=guidance,
                    original_content=expr.expression[:500],  # Truncate long expressions
                )
            )
        return todos

    def _generate_subreport_todos(
        self, analysis_id: UUID, visuals: list[VisualFeature]
    ) -> list[TodoItemCreate]:
        """Generate TODOs for subreports."""
        todos = []
        for visual in visuals:
            if visual.type != VisualType.SUBREPORT:
                continue

            subreport_path = (
                f" (Path: {visual.subreport_path})" if visual.subreport_path else ""
            )

            todos.append(
                TodoItemCreate(
                    analysis_id=analysis_id,
                    title=f"Convert subreport '{visual.name}' separately",
                    category=TodoCategory.SUBREPORT,
                    priority=TodoPriority.MEDIUM,
                    location="Embedded in parent report",
                    item_name=visual.name,
                    guidance=SUBREPORT_GUIDANCE,
                    original_content=f"Subreport reference{subreport_path}",
                )
            )
        return todos

    def _generate_custom_code_todos(
        self, analysis_id: UUID, functions: list[VBFunctionAnalysis]
    ) -> list[TodoItemCreate]:
        """Generate TODOs for custom VB functions."""
        todos = []
        for func in functions:
            # Build pattern hints
            pattern_hints = []
            for pattern in func.patterns_detected:
                hint = VB_PATTERN_GUIDANCE.get(pattern)
                if hint:
                    pattern_hints.append(hint)

            guidance = EXPRESSION_GUIDANCE["custom_code"]
            if pattern_hints:
                guidance += "\n\nDetected patterns:\n- " + "\n- ".join(pattern_hints)

            params_str = (
                f"Parameters: {', '.join(func.parameters)}"
                if func.parameters
                else "No parameters"
            )

            todos.append(
                TodoItemCreate(
                    analysis_id=analysis_id,
                    title=f"Convert VB function '{func.name}' to DAX measure",
                    category=TodoCategory.CUSTOM_CODE,
                    priority=TodoPriority.HIGH,
                    location="Report custom code block",
                    item_name=func.name,
                    guidance=guidance,
                    original_content=f"{params_str} | Lines: {func.line_count} | Difficulty: {func.conversion_difficulty}",
                )
            )
        return todos

    def _generate_visual_todos(
        self, analysis_id: UUID, visuals: list[VisualFeature]
    ) -> list[TodoItemCreate]:
        """Generate TODOs for unsupported visuals."""
        todos = []
        unsupported_types = {VisualType.MAP, VisualType.GAUGE}

        for visual in visuals:
            if visual.type not in unsupported_types:
                continue

            guidance = VISUAL_GUIDANCE.get(
                visual.type, "Recreate this visual manually in Power BI."
            )

            todos.append(
                TodoItemCreate(
                    analysis_id=analysis_id,
                    title=f"Recreate {visual.type.value} visual '{visual.name}' in Power BI",
                    category=TodoCategory.UNSUPPORTED_VISUAL,
                    priority=TodoPriority.MEDIUM,
                    location="Report body",
                    item_name=visual.name,
                    guidance=guidance,
                    original_content=f"Visual type: {visual.type.value}",
                )
            )
        return todos

    def _get_expression_title(self, expr: ExpressionAnalysis) -> str:
        """Generate a descriptive title for an expression TODO."""
        pattern = expr.pattern_matched or "unknown"

        title_templates = {
            "lookup": "Convert Lookup expression to DAX RELATED/LOOKUPVALUE",
            "lookupset": "Convert LookupSet expression to DAX CONCATENATEX",
            "multilookup": "Convert MultiLookup expression to DAX measure",
            "previous": "Convert Previous() expression to DAX with EARLIER",
            "running_value": "Convert RunningValue expression to DAX window function",
            "row_number_scoped": "Convert RowNumber expression to DAX RANKX/INDEX",
            "row_number_simple": "Convert RowNumber to DAX ROWNUMBER function",
            "custom_code": "Convert custom VB code call to DAX measure",
            "aggregate_with_scope": "Convert scoped aggregate to DAX CALCULATE",
            "report_items": "Restructure ReportItems reference for Power BI",
            "globals": "Replace Globals reference with Power BI equivalent",
            "user": "Replace User reference with Power BI user function",
            "iif": "Convert IIf expression to DAX IF statement",
            "switch": "Convert Switch expression to DAX SWITCH",
            "format": "Convert Format function to DAX FORMAT",
            "date_conversion": "Convert date function to DAX DATE functions",
            "date_math": "Convert date math to DAX DATEADD/DATEDIFF",
        }

        if pattern in title_templates:
            return title_templates[pattern]

        if expr.category == ExpressionConversionCategory.MANUAL:
            return f"Manually convert expression in {expr.location}"
        else:
            return f"Review and adjust expression in {expr.location}"

    def _get_expression_guidance(self, expr: ExpressionAnalysis) -> str:
        """Get guidance text for an expression."""
        pattern = expr.pattern_matched or "default"
        guidance = EXPRESSION_GUIDANCE.get(pattern, EXPRESSION_GUIDANCE["default"])

        # Add suggested DAX if available
        if expr.suggested_dax:
            guidance += f"\n\nSuggested DAX: {expr.suggested_dax}"

        return guidance


def generate_todos(
    analysis_id: UUID,
    features: AnalysisFeatures,
    code_analysis: CodeAnalysisResult,
) -> list[TodoItemCreate]:
    """Convenience function to generate TODO items.

    Args:
        analysis_id: UUID of the analysis record
        features: Parsed RDL features
        code_analysis: Code analysis results

    Returns:
        List of TodoItemCreate objects
    """
    generator = TodoGenerator()
    return generator.generate_todos(analysis_id, features, code_analysis)

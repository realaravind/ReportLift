"""Expression Analyzer - Categorizes report expressions for conversion."""

import logging
import re
from typing import Pattern

from app.schemas.analysis import AnalysisFeatures, ExpressionFeature
from app.schemas.code_analysis import ExpressionAnalysis, ExpressionConversionCategory

logger = logging.getLogger(__name__)


class ExpressionAnalyzer:
    """Analyzes and categorizes report expressions for conversion difficulty."""

    # Pattern definitions: (regex, category, pattern_name, reason)
    PATTERNS: list[tuple[Pattern[str], ExpressionConversionCategory, str, str]] = [
        # AUTO-CONVERTIBLE patterns
        (
            re.compile(r"^=Fields![\w]+\.Value$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_field",
            "Simple field reference - direct column mapping",
        ),
        (
            re.compile(r"^=Sum\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_sum",
            "Simple SUM aggregate - direct DAX SUM",
        ),
        (
            re.compile(r"^=Count\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_count",
            "Simple COUNT aggregate - direct DAX COUNT",
        ),
        (
            re.compile(r"^=Avg\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_avg",
            "Simple AVG aggregate - direct DAX AVERAGE",
        ),
        (
            re.compile(r"^=Min\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_min",
            "Simple MIN aggregate - direct DAX MIN",
        ),
        (
            re.compile(r"^=Max\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_max",
            "Simple MAX aggregate - direct DAX MAX",
        ),
        (
            re.compile(r"^=First\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_first",
            "Simple FIRST aggregate - use DAX FIRSTNONBLANK",
        ),
        (
            re.compile(r"^=Last\(Fields![\w]+\.Value\)$", re.IGNORECASE),
            ExpressionConversionCategory.AUTO,
            "simple_last",
            "Simple LAST aggregate - use DAX LASTNONBLANK",
        ),
        # PARTIAL patterns - need adjustment but have clear mappings
        (
            re.compile(r"Lookup\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "lookup",
            "Lookup expression - use RELATED or LOOKUPVALUE in DAX",
        ),
        (
            re.compile(r"LookupSet\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "lookupset",
            "LookupSet expression - requires DAX CONCATENATEX with filter",
        ),
        (
            re.compile(r"MultiLookup\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "multilookup",
            "MultiLookup expression - requires custom DAX measure",
        ),
        (
            re.compile(r"Previous\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "previous",
            "Previous expression - use DAX with EARLIER or calculated column",
        ),
        (
            re.compile(
                r"(Sum|Count|Avg|Min|Max)\s*\([^)]+,\s*[\"'][^\"']+[\"']",
                re.IGNORECASE,
            ),
            ExpressionConversionCategory.PARTIAL,
            "aggregate_with_scope",
            "Aggregate with scope - use DAX CALCULATE with filter context",
        ),
        (
            re.compile(r"IIf\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "iif",
            "IIf conditional - use DAX IF statement",
        ),
        (
            re.compile(r"Switch\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "switch",
            "Switch expression - use DAX SWITCH",
        ),
        (
            re.compile(r"Format\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "format",
            "Format function - use DAX FORMAT with appropriate format string",
        ),
        (
            re.compile(r"CDate\s*\(|DateValue\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "date_conversion",
            "Date conversion - use DAX DATE functions",
        ),
        (
            re.compile(r"DateAdd\s*\(|DateDiff\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "date_math",
            "Date math - use DAX DATEADD or DATEDIFF",
        ),
        # MANUAL patterns - require significant manual work
        (
            re.compile(r"Code\.[\w]+\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "custom_code",
            "Custom VB code call - requires manual DAX/Power Query conversion",
        ),
        (
            re.compile(r"RunningValue\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "running_value",
            "RunningValue expression - requires DAX window function or calculated column",
        ),
        (
            re.compile(r"RowNumber\s*\([\"']", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "row_number_scoped",
            "RowNumber with scope - requires DAX INDEX or RANKX",
        ),
        (
            re.compile(r"RowNumber\s*\(Nothing\)", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "row_number_simple",
            "Simple RowNumber - use DAX ROWNUMBER",
        ),
        (
            re.compile(r"Aggregate\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "aggregate_function",
            "Aggregate function - requires analysis of underlying aggregation",
        ),
        (
            re.compile(r"Level\s*\(|InScope\s*\(", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "hierarchy_function",
            "Hierarchy function - requires DAX ISINSCOPE or path functions",
        ),
        (
            re.compile(r"ReportItems!", re.IGNORECASE),
            ExpressionConversionCategory.MANUAL,
            "report_items",
            "ReportItems reference - no direct DAX equivalent",
        ),
        (
            re.compile(r"Globals!", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "globals",
            "Globals reference - map to Power BI parameters or built-in functions",
        ),
        (
            re.compile(r"User!", re.IGNORECASE),
            ExpressionConversionCategory.PARTIAL,
            "user",
            "User reference - use Power BI USERPRINCIPALNAME or similar",
        ),
    ]

    # DAX suggestion patterns for auto-convertible expressions
    DAX_SUGGESTIONS = {
        "simple_field": lambda m: f"[{m.group(1)}]" if m else None,
        "simple_sum": lambda m: f"SUM([{m.group(1)}])" if m else None,
        "simple_count": lambda m: f"COUNT([{m.group(1)}])" if m else None,
        "simple_avg": lambda m: f"AVERAGE([{m.group(1)}])" if m else None,
        "simple_min": lambda m: f"MIN([{m.group(1)}])" if m else None,
        "simple_max": lambda m: f"MAX([{m.group(1)}])" if m else None,
    }

    # Regex for extracting field names
    FIELD_EXTRACT = re.compile(r"Fields!([\w]+)\.Value", re.IGNORECASE)
    AGGREGATE_EXTRACT = re.compile(
        r"^=(Sum|Count|Avg|Min|Max)\(Fields!([\w]+)\.Value\)$", re.IGNORECASE
    )

    def analyze_expression(
        self,
        expression: str,
        location: str = "",
        item_name: str | None = None,
    ) -> ExpressionAnalysis | None:
        """Analyze a single expression and categorize it.

        Args:
            expression: The expression text
            location: Location in the report (XPath or description)
            item_name: Name of the parent report item

        Returns:
            ExpressionAnalysis or None if not an expression
        """
        if not expression or not expression.strip().startswith("="):
            return None

        expr = expression.strip()
        category, reason, pattern_name = self._categorize(expr)
        suggested_dax = self._suggest_dax(expr, pattern_name)

        return ExpressionAnalysis(
            expression=expr[:500],  # Truncate long expressions
            category=category,
            location=location,
            item_name=item_name,
            reason=reason,
            suggested_dax=suggested_dax,
            pattern_matched=pattern_name,
        )

    def analyze_expressions(
        self, expressions: list[ExpressionFeature]
    ) -> list[ExpressionAnalysis]:
        """Analyze multiple expressions from RDL parsing.

        Args:
            expressions: List of expression features from RDL

        Returns:
            List of ExpressionAnalysis results
        """
        results = []
        for expr in expressions:
            analysis = self.analyze_expression(
                expr.expression,
                expr.location,
                expr.item_name,
            )
            if analysis:
                results.append(analysis)
        return results

    def analyze_features(self, features: AnalysisFeatures) -> list[ExpressionAnalysis]:
        """Analyze expressions from analysis features.

        Args:
            features: Complete analysis features from RDL parsing

        Returns:
            List of ExpressionAnalysis
        """
        return self.analyze_expressions(features.expressions)

    def _categorize(
        self, expression: str
    ) -> tuple[ExpressionConversionCategory, str, str]:
        """Determine the category of an expression.

        Args:
            expression: The expression text

        Returns:
            Tuple of (category, reason, pattern_name)
        """
        for pattern, category, pattern_name, reason in self.PATTERNS:
            if pattern.search(expression):
                return category, reason, pattern_name

        # Default categorization for unmatched expressions
        if re.search(r"[\w]+\s*\(", expression):
            # Contains a function call - needs review
            return (
                ExpressionConversionCategory.PARTIAL,
                "Contains function call - manual review recommended",
                "unknown_function",
            )

        # Simple expression without function calls
        return (
            ExpressionConversionCategory.AUTO,
            "Simple expression - likely direct conversion",
            "simple",
        )

    def _suggest_dax(self, expression: str, pattern_name: str) -> str | None:
        """Suggest DAX equivalent for auto-convertible expressions.

        Args:
            expression: The expression text
            pattern_name: The pattern that matched

        Returns:
            Suggested DAX or None
        """
        if pattern_name == "simple_field":
            match = self.FIELD_EXTRACT.search(expression)
            if match:
                return f"[{match.group(1)}]"

        elif pattern_name in (
            "simple_sum",
            "simple_count",
            "simple_avg",
            "simple_min",
            "simple_max",
        ):
            match = self.AGGREGATE_EXTRACT.match(expression)
            if match:
                func = match.group(1).upper()
                field = match.group(2)
                if func == "AVG":
                    func = "AVERAGE"
                return f"{func}([{field}])"

        elif pattern_name == "iif":
            # Provide template
            return "IF(<condition>, <true_value>, <false_value>)"

        elif pattern_name == "switch":
            return "SWITCH(<expression>, <value1>, <result1>, ...)"

        return None


def analyze_expressions(features: AnalysisFeatures) -> list[ExpressionAnalysis]:
    """Convenience function to analyze expressions.

    Args:
        features: Analysis features from RDL parsing

    Returns:
        List of ExpressionAnalysis
    """
    analyzer = ExpressionAnalyzer()
    return analyzer.analyze_features(features)

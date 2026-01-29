"""Code Analyzer - Combined analysis of SPs, expressions, and VB code."""

import logging

from app.schemas.analysis import AnalysisFeatures
from app.schemas.code_analysis import CodeAnalysisResult
from app.services.expression_analyzer import ExpressionAnalyzer
from app.services.sp_analyzer import SPAnalyzer
from app.services.vb_analyzer import VBCodeAnalyzer

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Combined analyzer for stored procedures, expressions, and VB code."""

    def __init__(self):
        self.sp_analyzer = SPAnalyzer()
        self.expression_analyzer = ExpressionAnalyzer()
        self.vb_analyzer = VBCodeAnalyzer()

    def analyze(self, features: AnalysisFeatures) -> CodeAnalysisResult:
        """Perform complete code analysis on report features.

        Args:
            features: Analysis features from RDL parsing

        Returns:
            CodeAnalysisResult with all analysis data
        """
        # Analyze stored procedures
        stored_procedures = self.sp_analyzer.analyze_features(features)
        logger.debug("Found %d stored procedures", len(stored_procedures))

        # Analyze expressions
        expressions = self.expression_analyzer.analyze_features(features)
        logger.debug("Analyzed %d expressions", len(expressions))

        # Analyze VB code
        vb_functions = self.vb_analyzer.analyze_features(features)
        logger.debug("Found %d VB functions", len(vb_functions))

        # Build result
        result = CodeAnalysisResult(
            stored_procedures=stored_procedures,
            expressions=expressions,
            vb_functions=vb_functions,
        )

        # Calculate summaries
        result.calculate_summaries()

        logger.info(
            "Code analysis complete: %d SPs, %d expressions (%d manual), %d VB functions",
            result.sp_summary.unique_count,
            result.expression_summary.total_count,
            result.expression_summary.manual_count,
            result.vb_summary.function_count,
        )

        return result


def analyze_code(features: AnalysisFeatures) -> CodeAnalysisResult:
    """Convenience function to perform complete code analysis.

    Args:
        features: Analysis features from RDL parsing

    Returns:
        CodeAnalysisResult with all analysis data
    """
    analyzer = CodeAnalyzer()
    return analyzer.analyze(features)

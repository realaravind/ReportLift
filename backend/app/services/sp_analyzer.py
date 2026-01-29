"""Stored Procedure Analyzer - Analyzes stored procedures in report datasets."""

import logging

from app.schemas.analysis import AnalysisFeatures, DatasetFeature, QueryType
from app.schemas.code_analysis import SPComplexity, StoredProcedureAnalysis

logger = logging.getLogger(__name__)


class SPAnalyzer:
    """Analyzes stored procedures used in report datasets."""

    # Complexity thresholds based on parameter count
    COMPLEXITY_THRESHOLDS = {
        SPComplexity.SIMPLE: (0, 2),
        SPComplexity.MODERATE: (3, 5),
        SPComplexity.COMPLEX: (6, float("inf")),
    }

    def analyze_datasets(
        self, datasets: list[DatasetFeature]
    ) -> list[StoredProcedureAnalysis]:
        """Analyze all datasets for stored procedures.

        Args:
            datasets: List of dataset features from RDL parsing

        Returns:
            List of StoredProcedureAnalysis with deduplication
        """
        sp_map: dict[str, StoredProcedureAnalysis] = {}

        for dataset in datasets:
            if dataset.query_type != QueryType.STORED_PROCEDURE:
                continue

            sp_name = dataset.stored_procedure_name or dataset.name
            if not sp_name:
                continue

            # Normalize SP name (remove schema prefix for comparison)
            normalized_name = self._normalize_sp_name(sp_name)

            if normalized_name in sp_map:
                # Track additional usage
                if dataset.name not in sp_map[normalized_name].datasets_using:
                    sp_map[normalized_name].datasets_using.append(dataset.name)
            else:
                # Create new SP analysis
                param_names = [p.name for p in dataset.parameters]
                complexity = self._estimate_complexity(len(param_names))

                sp_map[normalized_name] = StoredProcedureAnalysis(
                    name=sp_name,
                    complexity=complexity,
                    parameter_count=len(param_names),
                    parameters=param_names,
                    datasets_using=[dataset.name],
                    conversion_notes=self._generate_conversion_notes(
                        complexity, len(param_names)
                    ),
                )

        return list(sp_map.values())

    def analyze_features(
        self, features: AnalysisFeatures
    ) -> list[StoredProcedureAnalysis]:
        """Analyze stored procedures from analysis features.

        Args:
            features: Complete analysis features from RDL parsing

        Returns:
            List of StoredProcedureAnalysis
        """
        return self.analyze_datasets(features.datasets)

    def _normalize_sp_name(self, sp_name: str) -> str:
        """Normalize stored procedure name for deduplication.

        Args:
            sp_name: Raw SP name (may include schema)

        Returns:
            Normalized name for comparison
        """
        # Remove common schema prefixes
        normalized = sp_name.strip()
        if "." in normalized:
            # Take the last part after the dot (procedure name)
            normalized = normalized.split(".")[-1]

        # Remove brackets if present
        normalized = normalized.strip("[]")

        return normalized.lower()

    def _estimate_complexity(self, param_count: int) -> SPComplexity:
        """Estimate SP complexity based on parameter count.

        Args:
            param_count: Number of parameters

        Returns:
            SPComplexity enum value
        """
        for complexity, (min_val, max_val) in self.COMPLEXITY_THRESHOLDS.items():
            if min_val <= param_count <= max_val:
                return complexity

        return SPComplexity.COMPLEX

    def _generate_conversion_notes(
        self, complexity: SPComplexity, param_count: int
    ) -> str:
        """Generate conversion notes based on complexity.

        Args:
            complexity: Estimated complexity
            param_count: Number of parameters

        Returns:
            Conversion guidance notes
        """
        if complexity == SPComplexity.SIMPLE:
            return (
                "Simple stored procedure. Usually straightforward SELECT rewrite. "
                "Consider using Snowflake stored procedure or inline SQL."
            )
        elif complexity == SPComplexity.MODERATE:
            return (
                f"Moderate complexity with {param_count} parameters. "
                "May involve temp tables, CTEs, or conditional logic. "
                "Review for Snowflake-specific syntax changes."
            )
        else:
            return (
                f"Complex stored procedure with {param_count} parameters. "
                "Likely contains significant business logic. "
                "Consider breaking into multiple Snowflake procedures or using JavaScript UDFs."
            )


def analyze_stored_procedures(
    features: AnalysisFeatures,
) -> list[StoredProcedureAnalysis]:
    """Convenience function to analyze stored procedures.

    Args:
        features: Analysis features from RDL parsing

    Returns:
        List of StoredProcedureAnalysis
    """
    analyzer = SPAnalyzer()
    return analyzer.analyze_features(features)

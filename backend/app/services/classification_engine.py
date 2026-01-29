"""Classification Engine - Determines report type based on features."""

import logging
from typing import Any

from app.schemas.analysis import AnalysisFeatures, VisualType
from app.schemas.classification import ReportClassification

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """Classifies reports based on their visual composition and complexity."""

    # Thresholds for classification
    TABULAR_THRESHOLD = 0.7  # >70% tables/matrices = Tabular
    ANALYTICAL_THRESHOLD = 0.5  # >50% charts/gauges = Analytical
    MIXED_MIN_RATIO = 0.3  # At least 30% of each for Mixed

    # Visual type sets for categorization
    TABULAR_TYPES = {VisualType.TABLIX, VisualType.TABLE, VisualType.MATRIX, VisualType.LIST}
    ANALYTICAL_TYPES = {VisualType.CHART, VisualType.GAUGE}
    COMPLEX_TYPES = {VisualType.MAP, VisualType.SUBREPORT}

    def classify(self, features: AnalysisFeatures) -> tuple[ReportClassification, dict[str, Any]]:
        """Classify a report based on its features.

        Args:
            features: Extracted analysis features from RDL

        Returns:
            Tuple of (classification, metadata dict with ratios and indicators)
        """
        metadata: dict[str, Any] = {
            "tabular_ratio": 0.0,
            "analytical_ratio": 0.0,
            "complexity_indicators": [],
        }

        # Check for complex indicators first (they take priority)
        complexity_indicators = self._get_complexity_indicators(features)
        metadata["complexity_indicators"] = complexity_indicators

        if complexity_indicators:
            logger.debug(
                "Report classified as Complex due to: %s",
                ", ".join(complexity_indicators),
            )
            return ReportClassification.COMPLEX, metadata

        # Calculate visual ratios
        tabular_ratio = self._calculate_tabular_ratio(features)
        analytical_ratio = self._calculate_analytical_ratio(features)

        metadata["tabular_ratio"] = tabular_ratio
        metadata["analytical_ratio"] = analytical_ratio

        # Handle empty reports
        if not features.visuals:
            if features.dataset_count > 0:
                # Has data but no visuals - likely a simple report
                return ReportClassification.SIMPLE, metadata
            return ReportClassification.SIMPLE, metadata

        # Classify based on ratios
        if tabular_ratio >= self.TABULAR_THRESHOLD and analytical_ratio < 0.1:
            return ReportClassification.TABULAR, metadata

        if analytical_ratio >= self.ANALYTICAL_THRESHOLD:
            return ReportClassification.ANALYTICAL, metadata

        if tabular_ratio >= self.MIXED_MIN_RATIO and analytical_ratio >= self.MIXED_MIN_RATIO:
            return ReportClassification.MIXED, metadata

        # Default based on majority
        if tabular_ratio > analytical_ratio:
            return ReportClassification.TABULAR, metadata
        elif analytical_ratio > tabular_ratio:
            return ReportClassification.ANALYTICAL, metadata
        else:
            return ReportClassification.MIXED, metadata

    def _get_complexity_indicators(self, features: AnalysisFeatures) -> list[str]:
        """Identify complexity indicators that mark a report as Complex.

        Args:
            features: Extracted analysis features

        Returns:
            List of complexity indicator descriptions
        """
        indicators = []

        # Check for subreports
        if features.subreport_count > 0:
            indicators.append(f"{features.subreport_count} subreport(s)")

        # Check for maps
        if features.map_count > 0:
            indicators.append(f"{features.map_count} map visual(s)")

        # Check for extensive custom code (more than 2 functions)
        if features.custom_code_function_count > 2:
            indicators.append(
                f"{features.custom_code_function_count} custom VB functions"
            )

        # Check for recursive groups
        if features.has_recursive_groups:
            recursive_count = sum(
                1 for v in features.visuals if v.has_recursive_group
            )
            indicators.append(f"{recursive_count} recursive hierarchy(s)")

        # Check for high running value count
        if features.running_value_count > 5:
            indicators.append(
                f"{features.running_value_count} RunningValue expressions"
            )

        # Check for high lookup expression count
        lookup_count = sum(
            1 for e in features.expressions
            if "lookup" in e.category.value.lower()
        )
        if lookup_count > 5:
            indicators.append(f"{lookup_count} Lookup expressions")

        return indicators

    def _calculate_tabular_ratio(self, features: AnalysisFeatures) -> float:
        """Calculate the ratio of tabular visuals to total visuals.

        Args:
            features: Extracted analysis features

        Returns:
            Ratio between 0.0 and 1.0
        """
        if not features.visuals:
            return 0.0

        # Count visuals that contribute to tabular ratio
        tabular_count = sum(
            1 for v in features.visuals if v.type in self.TABULAR_TYPES
        )
        # Exclude non-content visuals from denominator
        content_visuals = [
            v for v in features.visuals
            if v.type not in {VisualType.TEXTBOX, VisualType.IMAGE, VisualType.LINE, VisualType.RECTANGLE}
        ]

        if not content_visuals:
            return 0.0

        return tabular_count / len(content_visuals)

    def _calculate_analytical_ratio(self, features: AnalysisFeatures) -> float:
        """Calculate the ratio of analytical visuals to total visuals.

        Args:
            features: Extracted analysis features

        Returns:
            Ratio between 0.0 and 1.0
        """
        if not features.visuals:
            return 0.0

        # Count visuals that contribute to analytical ratio
        analytical_count = sum(
            1 for v in features.visuals if v.type in self.ANALYTICAL_TYPES
        )
        # Exclude non-content visuals from denominator
        content_visuals = [
            v for v in features.visuals
            if v.type not in {VisualType.TEXTBOX, VisualType.IMAGE, VisualType.LINE, VisualType.RECTANGLE}
        ]

        if not content_visuals:
            return 0.0

        return analytical_count / len(content_visuals)


def classify_report(features: AnalysisFeatures) -> tuple[ReportClassification, dict[str, Any]]:
    """Convenience function to classify a report.

    Args:
        features: Extracted analysis features from RDL

    Returns:
        Tuple of (classification, metadata)
    """
    engine = ClassificationEngine()
    return engine.classify(features)

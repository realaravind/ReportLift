"""Scoring Engine - Calculates conversion readiness score with penalties."""

import logging
from datetime import datetime, timezone

from app.schemas.analysis import (
    AnalysisFeatures,
    ExpressionCategory,
    QueryType,
    VisualType,
)
from app.schemas.classification import (
    ClassificationResult,
    ConversionStatus,
    PenaltyCategory,
    PenaltyItem,
    PenaltyWeights,
    ReportClassification,
    ScoreBreakdown,
    StatusThresholds,
)
from app.services.classification_engine import classify_report

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Calculates conversion readiness scores with weighted penalties."""

    def __init__(
        self,
        penalty_weights: PenaltyWeights | None = None,
        status_thresholds: StatusThresholds | None = None,
    ):
        """Initialize the scoring engine.

        Args:
            penalty_weights: Custom penalty weights (uses defaults if None)
            status_thresholds: Custom status thresholds (uses defaults if None)
        """
        self.weights = penalty_weights or PenaltyWeights()
        self.thresholds = status_thresholds or StatusThresholds()

    def calculate_score(self, features: AnalysisFeatures) -> ScoreBreakdown:
        """Calculate the conversion score with detailed breakdown.

        Args:
            features: Extracted analysis features from RDL

        Returns:
            ScoreBreakdown with penalties and final score
        """
        breakdown = ScoreBreakdown(base_score=100, penalties=[], final_score=100)
        category_totals: dict[PenaltyCategory, int] = {}

        # Apply stored procedure penalties
        self._apply_stored_procedure_penalties(features, breakdown, category_totals)

        # Apply subreport penalties
        self._apply_subreport_penalties(features, breakdown, category_totals)

        # Apply map penalties
        self._apply_map_penalties(features, breakdown, category_totals)

        # Apply gauge penalties
        self._apply_gauge_penalties(features, breakdown, category_totals)

        # Apply recursive group penalties
        self._apply_recursive_group_penalties(features, breakdown, category_totals)

        # Apply custom VB function penalties
        self._apply_custom_code_penalties(features, breakdown, category_totals)

        # Apply RunningValue penalties
        self._apply_running_value_penalties(features, breakdown, category_totals)

        # Apply Lookup penalties
        self._apply_lookup_penalties(features, breakdown, category_totals)

        # Apply complex expression penalties
        self._apply_complex_expression_penalties(features, breakdown, category_totals)

        # Calculate final score (minimum 0)
        total_penalty = sum(p.penalty_percent for p in breakdown.penalties)
        breakdown.final_score = max(0, breakdown.base_score - total_penalty)

        logger.debug(
            "Score calculated: base=%d, total_penalty=%d, final=%d, penalties=%d",
            breakdown.base_score,
            total_penalty,
            breakdown.final_score,
            len(breakdown.penalties),
        )

        return breakdown

    def _can_apply_penalty(
        self,
        category: PenaltyCategory,
        category_totals: dict[PenaltyCategory, int],
    ) -> int:
        """Check if more penalty can be applied for a category.

        Args:
            category: The penalty category
            category_totals: Current totals per category

        Returns:
            Maximum penalty that can still be applied (0 if capped)
        """
        current = category_totals.get(category, 0)
        max_allowed = self.weights.get_max_penalty(category)
        remaining = max_allowed - current
        return max(0, remaining)

    def _apply_penalty(
        self,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
        category: PenaltyCategory,
        item_name: str,
        reason: str,
    ) -> None:
        """Apply a penalty if under the category cap.

        Args:
            breakdown: The score breakdown to update
            category_totals: Running totals per category
            category: The penalty category
            item_name: Name of the item causing the penalty
            reason: Explanation for the penalty
        """
        remaining = self._can_apply_penalty(category, category_totals)
        if remaining <= 0:
            return

        penalty_amount = min(self.weights.get_penalty(category), remaining)

        breakdown.penalties.append(
            PenaltyItem(
                category=category,
                item_name=item_name,
                penalty_percent=penalty_amount,
                reason=reason,
            )
        )

        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += penalty_amount

    def _apply_stored_procedure_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for stored procedures."""
        for ds in features.datasets:
            if ds.query_type == QueryType.STORED_PROCEDURE:
                sp_name = ds.stored_procedure_name or ds.name
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.STORED_PROCEDURE,
                    sp_name,
                    f"Stored procedure '{sp_name}' requires SQL rewrite for Snowflake",
                )

    def _apply_subreport_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for subreports."""
        for v in features.visuals:
            if v.type == VisualType.SUBREPORT:
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.SUBREPORT,
                    v.name,
                    f"Subreport '{v.name}' requires separate conversion",
                )

    def _apply_map_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for map visuals."""
        for v in features.visuals:
            if v.type == VisualType.MAP:
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.MAP,
                    v.name,
                    f"Map visual '{v.name}' requires manual recreation in Power BI",
                )

    def _apply_gauge_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for gauge visuals."""
        for v in features.visuals:
            if v.type == VisualType.GAUGE:
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.GAUGE,
                    v.name,
                    f"Gauge visual '{v.name}' needs Power BI gauge/KPI recreation",
                )

    def _apply_recursive_group_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for recursive group hierarchies."""
        for v in features.visuals:
            if v.has_recursive_group:
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.RECURSIVE_GROUP,
                    v.name,
                    f"Recursive hierarchy in '{v.name}' requires manual DAX handling",
                )

    def _apply_custom_code_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for custom VB.NET functions."""
        for func in features.custom_code_functions:
            self._apply_penalty(
                breakdown,
                category_totals,
                PenaltyCategory.CUSTOM_VB_FUNCTION,
                func.name,
                f"Custom VB function '{func.name}' requires DAX/Power Query conversion",
            )

    def _apply_running_value_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for RunningValue expressions."""
        for expr in features.expressions:
            if expr.category == ExpressionCategory.RUNNING_VALUE:
                item_name = expr.item_name or "expression"
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.RUNNING_VALUE,
                    item_name,
                    f"RunningValue expression requires DAX running total measure",
                )

    def _apply_lookup_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for Lookup expressions."""
        for expr in features.expressions:
            if expr.category == ExpressionCategory.LOOKUP:
                item_name = expr.item_name or "expression"
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.LOOKUP,
                    item_name,
                    f"Lookup expression requires Power BI relationship modeling",
                )

    def _apply_complex_expression_penalties(
        self,
        features: AnalysisFeatures,
        breakdown: ScoreBreakdown,
        category_totals: dict[PenaltyCategory, int],
    ) -> None:
        """Apply penalties for complex aggregate expressions."""
        for expr in features.expressions:
            if expr.category == ExpressionCategory.COMPLEX_AGGREGATE:
                item_name = expr.item_name or "expression"
                self._apply_penalty(
                    breakdown,
                    category_totals,
                    PenaltyCategory.COMPLEX_EXPRESSION,
                    item_name,
                    f"Complex aggregate expression may need DAX rewrite",
                )

    def assign_status(self, score: int) -> ConversionStatus:
        """Assign conversion status based on score.

        Args:
            score: The calculated score (0-100)

        Returns:
            ConversionStatus (GREEN, YELLOW, or RED)
        """
        return self.thresholds.get_status(score)

    def analyze(self, features: AnalysisFeatures) -> ClassificationResult:
        """Perform complete analysis: classify, score, and assign status.

        Args:
            features: Extracted analysis features from RDL

        Returns:
            Complete ClassificationResult
        """
        # Classify the report
        classification, metadata = classify_report(features)

        # Calculate score
        breakdown = self.calculate_score(features)

        # Assign status
        status = self.assign_status(breakdown.final_score)

        return ClassificationResult(
            classification=classification,
            score=breakdown.final_score,
            status=status,
            breakdown=breakdown,
            analysis_timestamp=datetime.now(timezone.utc),
            tabular_ratio=metadata.get("tabular_ratio", 0.0),
            analytical_ratio=metadata.get("analytical_ratio", 0.0),
            complexity_indicators=metadata.get("complexity_indicators", []),
        )


def calculate_score(
    features: AnalysisFeatures,
    penalty_weights: PenaltyWeights | None = None,
) -> ScoreBreakdown:
    """Convenience function to calculate score.

    Args:
        features: Extracted analysis features from RDL
        penalty_weights: Optional custom penalty weights

    Returns:
        ScoreBreakdown with penalties and final score
    """
    engine = ScoringEngine(penalty_weights=penalty_weights)
    return engine.calculate_score(features)


def analyze_report(
    features: AnalysisFeatures,
    penalty_weights: PenaltyWeights | None = None,
    status_thresholds: StatusThresholds | None = None,
) -> ClassificationResult:
    """Convenience function to perform complete analysis.

    Args:
        features: Extracted analysis features from RDL
        penalty_weights: Optional custom penalty weights
        status_thresholds: Optional custom status thresholds

    Returns:
        Complete ClassificationResult
    """
    engine = ScoringEngine(
        penalty_weights=penalty_weights,
        status_thresholds=status_thresholds,
    )
    return engine.analyze(features)

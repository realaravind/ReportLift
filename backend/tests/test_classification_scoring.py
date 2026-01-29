"""Tests for Classification and Scoring Engines."""

import pytest

from app.schemas.analysis import (
    AnalysisFeatures,
    CustomCodeFunction,
    DatasetFeature,
    ExpressionCategory,
    ExpressionFeature,
    LayoutFeature,
    QueryType,
    VisualFeature,
    VisualType,
)
from app.schemas.classification import (
    ConversionStatus,
    PenaltyCategory,
    PenaltyWeights,
    ReportClassification,
    StatusThresholds,
)
from app.services.classification_engine import ClassificationEngine, classify_report
from app.services.scoring_engine import ScoringEngine, analyze_report, calculate_score


def create_empty_features() -> AnalysisFeatures:
    """Create empty AnalysisFeatures for testing."""
    return AnalysisFeatures(
        rdl_version="2016",
        datasets=[],
        visuals=[],
        expressions=[],
        layout=LayoutFeature(),
    )


def create_tabular_features() -> AnalysisFeatures:
    """Create features for a tabular report."""
    return AnalysisFeatures(
        rdl_version="2016",
        datasets=[
            DatasetFeature(
                name="MainData",
                query_type=QueryType.EMBEDDED_SQL,
                field_count=5,
            )
        ],
        visuals=[
            VisualFeature(type=VisualType.TABLIX, name="Table1", row_groups=2),
            VisualFeature(type=VisualType.TABLIX, name="Table2", row_groups=1),
            VisualFeature(type=VisualType.TEXTBOX, name="Title"),
        ],
        expressions=[
            ExpressionFeature(
                expression="=Fields!Name.Value",
                category=ExpressionCategory.FIELD_REFERENCE,
                location="Table1/Cell",
            )
        ],
        layout=LayoutFeature(page_width="8.5in", page_height="11in"),
        dataset_count=1,
        visual_count=3,
        expression_count=1,
        table_count=2,
    )


def create_analytical_features() -> AnalysisFeatures:
    """Create features for an analytical report."""
    return AnalysisFeatures(
        rdl_version="2016",
        datasets=[
            DatasetFeature(
                name="SalesData",
                query_type=QueryType.EMBEDDED_SQL,
                field_count=10,
            )
        ],
        visuals=[
            VisualFeature(type=VisualType.CHART, name="SalesChart"),
            VisualFeature(type=VisualType.CHART, name="TrendChart"),
            VisualFeature(type=VisualType.GAUGE, name="KPIGauge"),
        ],
        expressions=[
            ExpressionFeature(
                expression="=Sum(Fields!Amount.Value)",
                category=ExpressionCategory.SIMPLE_AGGREGATE,
                location="Chart",
            )
        ],
        layout=LayoutFeature(),
        dataset_count=1,
        visual_count=3,
        expression_count=1,
        chart_count=2,
        gauge_count=1,
    )


def create_mixed_features() -> AnalysisFeatures:
    """Create features for a mixed report."""
    return AnalysisFeatures(
        rdl_version="2016",
        datasets=[
            DatasetFeature(
                name="Data",
                query_type=QueryType.EMBEDDED_SQL,
                field_count=8,
            )
        ],
        visuals=[
            VisualFeature(type=VisualType.TABLIX, name="DataTable", row_groups=1),
            VisualFeature(type=VisualType.CHART, name="SummaryChart"),
        ],
        expressions=[],
        layout=LayoutFeature(),
        dataset_count=1,
        visual_count=2,
        table_count=1,
        chart_count=1,
    )


def create_complex_features() -> AnalysisFeatures:
    """Create features for a complex report."""
    return AnalysisFeatures(
        rdl_version="2016",
        datasets=[
            DatasetFeature(
                name="MainData",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="usp_GetReport",
                field_count=15,
            ),
            DatasetFeature(
                name="LookupData",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="usp_GetLookup",
                field_count=5,
            ),
        ],
        visuals=[
            VisualFeature(type=VisualType.TABLIX, name="MainTable", row_groups=3),
            VisualFeature(type=VisualType.SUBREPORT, name="DetailReport", subreport_path="/Reports/Detail"),
            VisualFeature(type=VisualType.MAP, name="RegionMap"),
        ],
        expressions=[
            ExpressionFeature(
                expression="=RunningValue(Fields!Amount.Value, Sum, Nothing)",
                category=ExpressionCategory.RUNNING_VALUE,
                location="MainTable",
                item_name="MainTable",
            ),
            ExpressionFeature(
                expression="=Code.FormatCurrency(Fields!Amount.Value)",
                category=ExpressionCategory.CUSTOM_CODE,
                location="MainTable",
                item_name="MainTable",
            ),
        ],
        custom_code="Public Function FormatCurrency...",
        custom_code_functions=[
            CustomCodeFunction(name="FormatCurrency", parameters=["value"]),
            CustomCodeFunction(name="CalculateTax", parameters=["amount", "rate"]),
            CustomCodeFunction(name="GetRegion", parameters=["code"]),
        ],
        layout=LayoutFeature(),
        dataset_count=2,
        stored_procedure_count=2,
        visual_count=3,
        expression_count=2,
        subreport_count=1,
        map_count=1,
        running_value_count=1,
        custom_code_function_count=3,
        has_custom_code=True,
        has_stored_procedures=True,
        has_subreports=True,
    )


class TestClassificationEngine:
    """Tests for the ClassificationEngine."""

    def test_empty_report_is_simple(self):
        features = create_empty_features()
        classification, metadata = classify_report(features)
        assert classification == ReportClassification.SIMPLE

    def test_tabular_report_classification(self):
        features = create_tabular_features()
        classification, metadata = classify_report(features)
        assert classification == ReportClassification.TABULAR
        assert metadata["tabular_ratio"] > 0.7

    def test_analytical_report_classification(self):
        features = create_analytical_features()
        classification, metadata = classify_report(features)
        assert classification == ReportClassification.ANALYTICAL
        assert metadata["analytical_ratio"] > 0.5

    def test_mixed_report_classification(self):
        features = create_mixed_features()
        classification, metadata = classify_report(features)
        # With one table and one chart (50/50), this could be MIXED or lean one way
        assert classification in (
            ReportClassification.MIXED,
            ReportClassification.TABULAR,
            ReportClassification.ANALYTICAL,
        )

    def test_complex_report_classification(self):
        features = create_complex_features()
        classification, metadata = classify_report(features)
        assert classification == ReportClassification.COMPLEX
        assert len(metadata["complexity_indicators"]) > 0

    def test_complexity_indicators_for_subreports(self):
        features = create_empty_features()
        features.visuals = [
            VisualFeature(
                type=VisualType.SUBREPORT,
                name="Sub1",
                subreport_path="/Reports/Sub1",
            )
        ]
        features.subreport_count = 1

        classification, metadata = classify_report(features)
        assert classification == ReportClassification.COMPLEX
        assert any("subreport" in ind.lower() for ind in metadata["complexity_indicators"])

    def test_complexity_indicators_for_maps(self):
        features = create_empty_features()
        features.visuals = [VisualFeature(type=VisualType.MAP, name="Map1")]
        features.map_count = 1

        classification, metadata = classify_report(features)
        assert classification == ReportClassification.COMPLEX
        assert any("map" in ind.lower() for ind in metadata["complexity_indicators"])

    def test_complexity_indicators_for_custom_code(self):
        features = create_empty_features()
        features.custom_code_functions = [
            CustomCodeFunction(name="Func1"),
            CustomCodeFunction(name="Func2"),
            CustomCodeFunction(name="Func3"),
        ]
        features.custom_code_function_count = 3

        classification, metadata = classify_report(features)
        assert classification == ReportClassification.COMPLEX
        assert any("custom vb" in ind.lower() for ind in metadata["complexity_indicators"])


class TestScoringEngine:
    """Tests for the ScoringEngine."""

    def test_empty_report_scores_100(self):
        features = create_empty_features()
        breakdown = calculate_score(features)
        assert breakdown.final_score == 100
        assert len(breakdown.penalties) == 0

    def test_stored_procedure_penalty(self):
        features = create_empty_features()
        features.datasets = [
            DatasetFeature(
                name="Data",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="usp_Test",
            )
        ]

        breakdown = calculate_score(features)
        assert breakdown.final_score < 100

        sp_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.STORED_PROCEDURE
        ]
        assert len(sp_penalties) == 1
        assert sp_penalties[0].penalty_percent == 15

    def test_subreport_penalty(self):
        features = create_empty_features()
        features.visuals = [
            VisualFeature(
                type=VisualType.SUBREPORT,
                name="SubReport1",
                subreport_path="/Reports/Sub",
            )
        ]

        breakdown = calculate_score(features)
        sub_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.SUBREPORT
        ]
        assert len(sub_penalties) == 1
        assert sub_penalties[0].penalty_percent == 20

    def test_custom_code_penalty(self):
        features = create_empty_features()
        features.custom_code_functions = [
            CustomCodeFunction(name="FormatValue"),
        ]

        breakdown = calculate_score(features)
        code_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.CUSTOM_VB_FUNCTION
        ]
        assert len(code_penalties) == 1
        assert code_penalties[0].penalty_percent == 25

    def test_running_value_penalty(self):
        features = create_empty_features()
        features.expressions = [
            ExpressionFeature(
                expression="=RunningValue(Fields!Amount.Value, Sum, Nothing)",
                category=ExpressionCategory.RUNNING_VALUE,
                location="Table",
                item_name="Table1",
            )
        ]

        breakdown = calculate_score(features)
        rv_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.RUNNING_VALUE
        ]
        assert len(rv_penalties) == 1
        assert rv_penalties[0].penalty_percent == 10

    def test_map_penalty(self):
        features = create_empty_features()
        features.visuals = [VisualFeature(type=VisualType.MAP, name="Map1")]

        breakdown = calculate_score(features)
        map_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.MAP
        ]
        assert len(map_penalties) == 1
        assert map_penalties[0].penalty_percent == 15

    def test_gauge_penalty(self):
        features = create_empty_features()
        features.visuals = [VisualFeature(type=VisualType.GAUGE, name="Gauge1")]

        breakdown = calculate_score(features)
        gauge_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.GAUGE
        ]
        assert len(gauge_penalties) == 1
        assert gauge_penalties[0].penalty_percent == 15

    def test_recursive_group_penalty(self):
        features = create_empty_features()
        features.visuals = [
            VisualFeature(
                type=VisualType.TABLIX,
                name="OrgChart",
                has_recursive_group=True,
            )
        ]

        breakdown = calculate_score(features)
        recursive_penalties = [
            p for p in breakdown.penalties
            if p.category == PenaltyCategory.RECURSIVE_GROUP
        ]
        assert len(recursive_penalties) == 1
        assert recursive_penalties[0].penalty_percent == 10

    def test_penalty_caps_prevent_excessive_penalties(self):
        features = create_empty_features()
        # Add 10 stored procedures (should be capped at max penalty)
        features.datasets = [
            DatasetFeature(
                name=f"Data{i}",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name=f"usp_Test{i}",
            )
            for i in range(10)
        ]

        breakdown = calculate_score(features)
        sp_total = sum(
            p.penalty_percent
            for p in breakdown.penalties
            if p.category == PenaltyCategory.STORED_PROCEDURE
        )
        # Should be capped at max_stored_procedure (45)
        assert sp_total <= 45

    def test_score_never_below_zero(self):
        features = create_complex_features()
        # Add more complexity to ensure many penalties
        features.datasets.extend([
            DatasetFeature(
                name=f"Data{i}",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name=f"usp_Test{i}",
            )
            for i in range(5)
        ])
        features.custom_code_functions.extend([
            CustomCodeFunction(name=f"Func{i}") for i in range(5)
        ])

        breakdown = calculate_score(features)
        assert breakdown.final_score >= 0

    def test_complex_report_low_score(self):
        features = create_complex_features()
        breakdown = calculate_score(features)
        # Complex reports should have significant penalties
        assert breakdown.final_score < 70


class TestStatusAssignment:
    """Tests for status assignment based on score."""

    def test_green_status_for_high_scores(self):
        engine = ScoringEngine()
        assert engine.assign_status(100) == ConversionStatus.GREEN
        assert engine.assign_status(85) == ConversionStatus.GREEN
        assert engine.assign_status(70) == ConversionStatus.GREEN

    def test_yellow_status_for_medium_scores(self):
        engine = ScoringEngine()
        assert engine.assign_status(69) == ConversionStatus.YELLOW
        assert engine.assign_status(55) == ConversionStatus.YELLOW
        assert engine.assign_status(40) == ConversionStatus.YELLOW

    def test_red_status_for_low_scores(self):
        engine = ScoringEngine()
        assert engine.assign_status(39) == ConversionStatus.RED
        assert engine.assign_status(20) == ConversionStatus.RED
        assert engine.assign_status(0) == ConversionStatus.RED

    def test_custom_thresholds(self):
        thresholds = StatusThresholds(green_min=80, yellow_min=50)
        engine = ScoringEngine(status_thresholds=thresholds)

        assert engine.assign_status(80) == ConversionStatus.GREEN
        assert engine.assign_status(79) == ConversionStatus.YELLOW
        assert engine.assign_status(50) == ConversionStatus.YELLOW
        assert engine.assign_status(49) == ConversionStatus.RED


class TestAnalyzeReport:
    """Tests for the complete analyze_report function."""

    def test_analyze_returns_complete_result(self):
        features = create_tabular_features()
        result = analyze_report(features)

        assert result.classification == ReportClassification.TABULAR
        assert result.score >= 0
        assert result.score <= 100
        assert result.status in (
            ConversionStatus.GREEN,
            ConversionStatus.YELLOW,
            ConversionStatus.RED,
        )
        assert result.breakdown is not None
        assert result.analysis_timestamp is not None

    def test_analyze_complex_report(self):
        features = create_complex_features()
        result = analyze_report(features)

        assert result.classification == ReportClassification.COMPLEX
        assert result.score < 70  # Should be yellow or red
        assert len(result.breakdown.penalties) > 0
        assert len(result.complexity_indicators) > 0

    def test_custom_weights_affect_scoring(self):
        features = create_empty_features()
        features.datasets = [
            DatasetFeature(
                name="Data",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="usp_Test",
            )
        ]

        # Default weights
        result_default = analyze_report(features)

        # Custom weights with higher penalty
        custom_weights = PenaltyWeights(stored_procedure=30)
        result_custom = analyze_report(features, penalty_weights=custom_weights)

        assert result_custom.score < result_default.score


class TestScoreBreakdown:
    """Tests for ScoreBreakdown functionality."""

    def test_total_penalty_calculation(self):
        features = create_complex_features()
        breakdown = calculate_score(features)

        expected_total = sum(p.penalty_percent for p in breakdown.penalties)
        assert breakdown.total_penalty == expected_total

    def test_penalties_by_category(self):
        features = create_complex_features()
        breakdown = calculate_score(features)

        by_category = breakdown.penalties_by_category()
        assert isinstance(by_category, dict)

        # Should have stored_procedure category
        assert "stored_procedure" in by_category

    def test_category_totals(self):
        features = create_complex_features()
        breakdown = calculate_score(features)

        totals = breakdown.category_totals()
        assert isinstance(totals, dict)

        # Verify totals sum correctly
        total_from_categories = sum(totals.values())
        assert total_from_categories == breakdown.total_penalty

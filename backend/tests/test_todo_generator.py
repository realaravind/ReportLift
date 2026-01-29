"""Unit tests for TODO generator service."""

import pytest
from uuid import uuid4

from app.schemas.analysis import (
    AnalysisFeatures,
    DatasetFeature,
    DatasetParameter,
    ExpressionCategory,
    ExpressionFeature,
    QueryType,
    VisualFeature,
    VisualType,
)
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
    EmptyTodoListResponse,
    TodoCategory,
    TodoItem,
    TodoItemCreate,
    TodoListResponse,
    TodoListSummary,
    TodoPriority,
)
from app.services.todo_generator import TodoGenerator, generate_todos


class TestTodoGenerator:
    """Tests for TODO generator service."""

    def test_generate_sp_todos(self):
        """Test TODO generation for stored procedures."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[
                StoredProcedureAnalysis(
                    name="sp_GetOrders",
                    complexity=SPComplexity.SIMPLE,
                    parameter_count=2,
                    parameters=["StartDate", "EndDate"],
                    datasets_using=["Dataset1"],
                ),
            ],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.STORED_PROCEDURE
        assert todos[0].priority == TodoPriority.HIGH
        assert "sp_GetOrders" in todos[0].title
        assert "convert" in todos[0].title.lower()
        assert "Dataset1" in todos[0].location

    def test_generate_complex_sp_todos(self):
        """Test TODO for complex stored procedures includes appropriate guidance."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[
                StoredProcedureAnalysis(
                    name="sp_ComplexReport",
                    complexity=SPComplexity.COMPLEX,
                    parameter_count=8,
                    parameters=[f"P{i}" for i in range(8)],
                    datasets_using=["MainData"],
                ),
            ],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].priority == TodoPriority.HIGH
        assert "complex" in todos[0].guidance.lower() or "Complex" in todos[0].original_content

    def test_generate_expression_todos_manual(self):
        """Test TODO generation for MANUAL expressions."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[
                ExpressionAnalysis(
                    expression="=Code.FormatCurrency(Fields!Amount.Value)",
                    category=ExpressionConversionCategory.MANUAL,
                    location="Textbox1",
                    item_name="TotalAmount",
                    reason="Custom VB code call",
                    pattern_matched="custom_code",
                ),
            ],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.EXPRESSION
        assert todos[0].priority == TodoPriority.HIGH  # MANUAL = High

    def test_generate_expression_todos_partial(self):
        """Test TODO generation for PARTIAL expressions."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[
                ExpressionAnalysis(
                    expression="=IIf(Fields!Status.Value = 1, 'Active', 'Inactive')",
                    category=ExpressionConversionCategory.PARTIAL,
                    location="Textbox2",
                    item_name="StatusText",
                    reason="IIf conditional",
                    pattern_matched="iif",
                    suggested_dax="IF(<condition>, <true_value>, <false_value>)",
                ),
            ],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.EXPRESSION
        assert todos[0].priority == TodoPriority.MEDIUM  # PARTIAL = Medium
        assert "IF" in todos[0].guidance  # DAX suggestion in guidance

    def test_skip_auto_expressions(self):
        """Test that AUTO expressions don't generate TODOs."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[
                ExpressionAnalysis(
                    expression="=Fields!Name.Value",
                    category=ExpressionConversionCategory.AUTO,
                    location="Textbox1",
                    item_name="NameField",
                    reason="Simple field reference",
                    pattern_matched="simple_field",
                ),
            ],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 0  # No TODO for AUTO expressions

    def test_generate_subreport_todos(self):
        """Test TODO generation for subreports."""
        analysis_id = uuid4()
        features = AnalysisFeatures(
            rdl_version="2016",
            visuals=[
                VisualFeature(
                    type=VisualType.SUBREPORT,
                    name="DetailSubreport",
                    subreport_path="/Reports/Details",
                ),
            ],
        )
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.SUBREPORT
        assert todos[0].priority == TodoPriority.MEDIUM
        assert "DetailSubreport" in todos[0].title
        assert "separately" in todos[0].title.lower()

    def test_generate_custom_code_todos(self):
        """Test TODO generation for VB custom code."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[
                VBFunctionAnalysis(
                    name="FormatCurrency",
                    parameters=["value"],
                    line_count=5,
                    patterns_detected=[VBPatternCategory.STRING_MANIPULATION],
                    complexity_estimate=SPComplexity.SIMPLE,
                    conversion_difficulty="low",
                ),
            ],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.CUSTOM_CODE
        assert todos[0].priority == TodoPriority.HIGH
        assert "FormatCurrency" in todos[0].title
        assert "DAX" in todos[0].title

    def test_generate_unsupported_visual_todos_map(self):
        """Test TODO generation for Map visuals."""
        analysis_id = uuid4()
        features = AnalysisFeatures(
            rdl_version="2016",
            visuals=[
                VisualFeature(
                    type=VisualType.MAP,
                    name="SalesMap",
                ),
            ],
        )
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert todos[0].category == TodoCategory.UNSUPPORTED_VISUAL
        assert todos[0].priority == TodoPriority.MEDIUM
        assert "map" in todos[0].title.lower()
        assert "SalesMap" in todos[0].title

    def test_generate_unsupported_visual_todos_gauge(self):
        """Test TODO generation for Gauge visuals."""
        analysis_id = uuid4()
        features = AnalysisFeatures(
            rdl_version="2016",
            visuals=[
                VisualFeature(
                    type=VisualType.GAUGE,
                    name="PerformanceGauge",
                ),
            ],
        )
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert "gauge" in todos[0].title.lower()
        assert "Power BI" in todos[0].guidance

    def test_supported_visuals_no_todos(self):
        """Test that supported visuals don't generate TODOs."""
        analysis_id = uuid4()
        features = AnalysisFeatures(
            rdl_version="2016",
            visuals=[
                VisualFeature(type=VisualType.TABLE, name="Table1"),
                VisualFeature(type=VisualType.MATRIX, name="Matrix1"),
                VisualFeature(type=VisualType.CHART, name="Chart1"),
                VisualFeature(type=VisualType.TEXTBOX, name="Textbox1"),
            ],
        )
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 0  # No TODOs for supported visuals

    def test_priority_sorting(self):
        """Test that TODOs are sorted by priority (High first)."""
        analysis_id = uuid4()
        features = AnalysisFeatures(
            rdl_version="2016",
            visuals=[
                VisualFeature(type=VisualType.MAP, name="Map1"),  # Medium
                VisualFeature(type=VisualType.SUBREPORT, name="Sub1"),  # Medium
            ],
        )
        code_analysis = CodeAnalysisResult(
            stored_procedures=[
                StoredProcedureAnalysis(
                    name="sp_Test",
                    complexity=SPComplexity.SIMPLE,
                    parameter_count=0,
                    datasets_using=["DS1"],
                ),  # High
            ],
            expressions=[],
            vb_functions=[
                VBFunctionAnalysis(
                    name="Func1",
                    line_count=5,
                    conversion_difficulty="low",
                ),  # High
            ],
        )
        code_analysis.calculate_summaries()

        generator = TodoGenerator()
        todos = generator.generate_todos(analysis_id, features, code_analysis)

        # Should have 4 items: 2 High (SP, VB), 2 Medium (Map, Subreport)
        assert len(todos) == 4

        # First items should be High priority
        assert todos[0].priority == TodoPriority.HIGH
        assert todos[1].priority == TodoPriority.HIGH

        # Last items should be Medium priority
        assert todos[2].priority == TodoPriority.MEDIUM
        assert todos[3].priority == TodoPriority.MEDIUM

    def test_empty_analysis_no_todos(self):
        """Test empty analysis generates no TODOs."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        todos = generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 0

    def test_convenience_function(self):
        """Test the generate_todos convenience function."""
        analysis_id = uuid4()
        features = AnalysisFeatures(rdl_version="2016")
        code_analysis = CodeAnalysisResult(
            stored_procedures=[
                StoredProcedureAnalysis(
                    name="sp_Test",
                    complexity=SPComplexity.SIMPLE,
                    parameter_count=1,
                    parameters=["Id"],
                    datasets_using=["DS1"],
                ),
            ],
            expressions=[],
            vb_functions=[],
        )
        code_analysis.calculate_summaries()

        todos = generate_todos(analysis_id, features, code_analysis)

        assert len(todos) == 1
        assert isinstance(todos[0], TodoItemCreate)


class TestTodoSchemas:
    """Tests for TODO Pydantic schemas."""

    def test_todo_item_create(self):
        """Test TodoItemCreate schema."""
        item = TodoItemCreate(
            analysis_id=uuid4(),
            title="Test TODO",
            category=TodoCategory.STORED_PROCEDURE,
            priority=TodoPriority.HIGH,
            location="Dataset1",
            item_name="sp_Test",
            guidance="Test guidance",
            original_content="Parameters: Id",
        )

        assert item.title == "Test TODO"
        assert item.category == TodoCategory.STORED_PROCEDURE
        assert item.priority == TodoPriority.HIGH

    def test_todo_list_summary(self):
        """Test TodoListSummary computed fields."""
        summary = TodoListSummary(
            total_count=10,
            high_priority_count=3,
            medium_priority_count=5,
            low_priority_count=2,
            resolved_count=4,
            unresolved_count=6,
        )

        assert summary.completion_percentage == 40.0

    def test_todo_list_summary_empty(self):
        """Test TodoListSummary with no items."""
        summary = TodoListSummary()

        assert summary.total_count == 0
        assert summary.completion_percentage == 100.0  # Empty list = complete

    def test_todo_list_response_from_items(self):
        """Test TodoListResponse.from_items class method."""
        items = [
            TodoItem(
                id=1,
                analysis_id=uuid4(),
                title="High 1",
                category=TodoCategory.STORED_PROCEDURE,
                priority=TodoPriority.HIGH,
                location="",
                guidance="",
                is_resolved=False,
            ),
            TodoItem(
                id=2,
                analysis_id=uuid4(),
                title="Medium 1",
                category=TodoCategory.EXPRESSION,
                priority=TodoPriority.MEDIUM,
                location="",
                guidance="",
                is_resolved=True,
            ),
            TodoItem(
                id=3,
                analysis_id=uuid4(),
                title="High 2",
                category=TodoCategory.CUSTOM_CODE,
                priority=TodoPriority.HIGH,
                location="",
                guidance="",
                is_resolved=False,
            ),
        ]

        response = TodoListResponse.from_items(items)

        assert response.summary.total_count == 3
        assert response.summary.high_priority_count == 2
        assert response.summary.medium_priority_count == 1
        assert response.summary.resolved_count == 1
        assert response.summary.unresolved_count == 2

        assert len(response.high_priority_items) == 2
        assert len(response.medium_priority_items) == 1
        assert len(response.low_priority_items) == 0

        # Check by_category grouping
        assert TodoCategory.STORED_PROCEDURE.value in response.by_category
        assert TodoCategory.EXPRESSION.value in response.by_category
        assert TodoCategory.CUSTOM_CODE.value in response.by_category

    def test_empty_todo_list_response(self):
        """Test EmptyTodoListResponse defaults."""
        response = EmptyTodoListResponse()

        assert response.message == "No manual work items identified"
        assert response.can_proceed_to_conversion is True


class TestGuidanceTemplates:
    """Tests for guidance template content."""

    def test_sp_guidance_varies_by_complexity(self):
        """Test that SP guidance varies by complexity."""
        from app.services.todo_generator import SP_GUIDANCE

        assert "simple" in SP_GUIDANCE[SPComplexity.SIMPLE].lower()
        assert "moderate" in SP_GUIDANCE[SPComplexity.MODERATE].lower()
        assert "complex" in SP_GUIDANCE[SPComplexity.COMPLEX].lower()

    def test_expression_guidance_has_common_patterns(self):
        """Test that expression guidance covers common patterns."""
        from app.services.todo_generator import EXPRESSION_GUIDANCE

        assert "lookup" in EXPRESSION_GUIDANCE
        assert "running_value" in EXPRESSION_GUIDANCE
        assert "custom_code" in EXPRESSION_GUIDANCE

    def test_visual_guidance_has_unsupported_types(self):
        """Test that visual guidance covers unsupported types."""
        from app.services.todo_generator import VISUAL_GUIDANCE

        assert VisualType.MAP in VISUAL_GUIDANCE
        assert VisualType.GAUGE in VISUAL_GUIDANCE

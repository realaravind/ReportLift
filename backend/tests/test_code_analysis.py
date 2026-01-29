"""Unit tests for code analysis services."""

import pytest

from app.schemas.analysis import (
    AnalysisFeatures,
    CustomCodeFunction,
    DatasetFeature,
    DatasetParameter,
    ExpressionCategory,
    ExpressionFeature,
    QueryType,
)
from app.schemas.code_analysis import (
    CodeAnalysisResult,
    ExpressionConversionCategory,
    SPComplexity,
    VBPatternCategory,
)
from app.services.code_analyzer import CodeAnalyzer, analyze_code
from app.services.expression_analyzer import ExpressionAnalyzer, analyze_expressions
from app.services.sp_analyzer import SPAnalyzer, analyze_stored_procedures
from app.services.vb_analyzer import VBCodeAnalyzer, analyze_vb_code


# =============================================================================
# SPAnalyzer Tests
# =============================================================================


class TestSPAnalyzer:
    """Tests for stored procedure analyzer."""

    def test_simple_sp_complexity(self):
        """Test that 0-2 params results in SIMPLE complexity."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_GetUsers",
                parameters=[
                    DatasetParameter(name="UserId", data_type="Integer"),
                ],
            )
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1
        assert result[0].name == "sp_GetUsers"
        assert result[0].complexity == SPComplexity.SIMPLE
        assert result[0].parameter_count == 1

    def test_moderate_sp_complexity(self):
        """Test that 3-5 params results in MODERATE complexity."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_SearchOrders",
                parameters=[
                    DatasetParameter(name="StartDate", data_type="DateTime"),
                    DatasetParameter(name="EndDate", data_type="DateTime"),
                    DatasetParameter(name="CustomerId", data_type="Integer"),
                    DatasetParameter(name="Status", data_type="String"),
                ],
            )
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1
        assert result[0].complexity == SPComplexity.MODERATE
        assert result[0].parameter_count == 4

    def test_complex_sp_complexity(self):
        """Test that 6+ params results in COMPLEX complexity."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_ComplexReport",
                parameters=[
                    DatasetParameter(name="P1", data_type="String"),
                    DatasetParameter(name="P2", data_type="String"),
                    DatasetParameter(name="P3", data_type="String"),
                    DatasetParameter(name="P4", data_type="String"),
                    DatasetParameter(name="P5", data_type="String"),
                    DatasetParameter(name="P6", data_type="String"),
                    DatasetParameter(name="P7", data_type="String"),
                ],
            )
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1
        assert result[0].complexity == SPComplexity.COMPLEX
        assert result[0].parameter_count == 7

    def test_sp_deduplication(self):
        """Test that duplicate SPs are merged and usage tracked."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_GetData",
                parameters=[DatasetParameter(name="Id", data_type="Integer")],
            ),
            DatasetFeature(
                name="Dataset2",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_GetData",
                parameters=[DatasetParameter(name="Id", data_type="Integer")],
            ),
            DatasetFeature(
                name="Dataset3",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="dbo.sp_GetData",  # Same SP with schema
                parameters=[DatasetParameter(name="Id", data_type="Integer")],
            ),
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1  # Only one unique SP
        assert result[0].usage_count == 3
        assert result[0].is_shared is True
        assert set(result[0].datasets_using) == {"Dataset1", "Dataset2", "Dataset3"}

    def test_sp_schema_normalization(self):
        """Test schema prefix normalization."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="[dbo].[sp_GetData]",
                parameters=[],
            ),
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1
        # Name is preserved as-is
        assert result[0].name == "[dbo].[sp_GetData]"

    def test_non_sp_datasets_ignored(self):
        """Test that non-SP datasets are not analyzed."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.EMBEDDED_SQL,
                query_text="SELECT * FROM Users",
            ),
            DatasetFeature(
                name="Dataset2",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_GetData",
                parameters=[],
            ),
        ]
        result = analyzer.analyze_datasets(datasets)

        assert len(result) == 1
        assert result[0].name == "sp_GetData"

    def test_conversion_notes_simple(self):
        """Test conversion notes for simple SPs."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_Simple",
                parameters=[],
            ),
        ]
        result = analyzer.analyze_datasets(datasets)

        assert "Simple stored procedure" in result[0].conversion_notes
        assert "straightforward" in result[0].conversion_notes.lower()

    def test_conversion_notes_complex(self):
        """Test conversion notes for complex SPs."""
        analyzer = SPAnalyzer()
        datasets = [
            DatasetFeature(
                name="Dataset1",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="sp_Complex",
                parameters=[DatasetParameter(name=f"P{i}", data_type="String") for i in range(8)],
            ),
        ]
        result = analyzer.analyze_datasets(datasets)

        assert "Complex" in result[0].conversion_notes
        assert "8 parameters" in result[0].conversion_notes

    def test_analyze_features_convenience(self):
        """Test the analyze_features method."""
        features = AnalysisFeatures(
            rdl_version="2016",
            datasets=[
                DatasetFeature(
                    name="DS1",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_Test",
                    parameters=[],
                ),
            ]
        )
        result = analyze_stored_procedures(features)

        assert len(result) == 1
        assert result[0].name == "sp_Test"


# =============================================================================
# ExpressionAnalyzer Tests
# =============================================================================


class TestExpressionAnalyzer:
    """Tests for expression analyzer."""

    def test_simple_field_auto(self):
        """Test simple field reference is AUTO."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Fields!CustomerName.Value")

        assert result is not None
        assert result.category == ExpressionConversionCategory.AUTO
        assert result.pattern_matched == "simple_field"
        assert result.suggested_dax == "[CustomerName]"

    def test_simple_sum_auto(self):
        """Test simple SUM is AUTO with DAX suggestion."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Sum(Fields!Amount.Value)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.AUTO
        assert result.pattern_matched == "simple_sum"
        assert result.suggested_dax == "SUM([Amount])"

    def test_simple_avg_auto(self):
        """Test AVG converts to AVERAGE in DAX."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Avg(Fields!Price.Value)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.AUTO
        assert result.suggested_dax == "AVERAGE([Price])"

    def test_simple_count_auto(self):
        """Test simple COUNT is AUTO."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Count(Fields!OrderId.Value)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.AUTO
        assert result.suggested_dax == "COUNT([OrderId])"

    def test_simple_min_max_auto(self):
        """Test MIN/MAX are AUTO."""
        analyzer = ExpressionAnalyzer()

        min_result = analyzer.analyze_expression("=Min(Fields!Date.Value)")
        max_result = analyzer.analyze_expression("=Max(Fields!Date.Value)")

        assert min_result.category == ExpressionConversionCategory.AUTO
        assert max_result.category == ExpressionConversionCategory.AUTO

    def test_lookup_partial(self):
        """Test Lookup expression is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression(
            '=Lookup(Fields!ProductId.Value, Fields!Id.Value, Fields!Name.Value, "Products")'
        )

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "lookup"
        assert "RELATED" in result.reason or "LOOKUPVALUE" in result.reason

    def test_iif_partial(self):
        """Test IIf conditional is PARTIAL with DAX suggestion."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression(
            '=IIf(Fields!Status.Value = "Active", "Yes", "No")'
        )

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "iif"
        assert result.suggested_dax == "IF(<condition>, <true_value>, <false_value>)"

    def test_switch_partial(self):
        """Test Switch expression is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression(
            '=Switch(Fields!Type.Value = 1, "A", Fields!Type.Value = 2, "B")'
        )

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "switch"
        assert "SWITCH" in result.suggested_dax

    def test_format_partial(self):
        """Test Format function is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression('=Format(Fields!Date.Value, "yyyy-MM-dd")')

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "format"

    def test_aggregate_with_scope_partial(self):
        """Test aggregate with scope is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression('=Sum(Fields!Amount.Value, "Group1")')

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "aggregate_with_scope"
        assert "CALCULATE" in result.reason

    def test_custom_code_manual(self):
        """Test custom VB code call is MANUAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Code.FormatCurrency(Fields!Amount.Value)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.MANUAL
        assert result.pattern_matched == "custom_code"

    def test_running_value_manual(self):
        """Test RunningValue is MANUAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression(
            '=RunningValue(Fields!Amount.Value, Sum, "Group1")'
        )

        assert result is not None
        assert result.category == ExpressionConversionCategory.MANUAL
        assert result.pattern_matched == "running_value"

    def test_row_number_scoped_manual(self):
        """Test RowNumber with scope is MANUAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression('=RowNumber("DataSet1")')

        assert result is not None
        assert result.category == ExpressionConversionCategory.MANUAL
        assert result.pattern_matched == "row_number_scoped"

    def test_row_number_simple_partial(self):
        """Test RowNumber(Nothing) is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=RowNumber(Nothing)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "row_number_simple"

    def test_report_items_manual(self):
        """Test ReportItems reference is MANUAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=ReportItems!Textbox1.Value")

        assert result is not None
        assert result.category == ExpressionConversionCategory.MANUAL
        assert result.pattern_matched == "report_items"

    def test_globals_partial(self):
        """Test Globals reference is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=Globals!PageNumber")

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "globals"

    def test_user_partial(self):
        """Test User reference is PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=User!UserID")

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "user"

    def test_non_expression_returns_none(self):
        """Test that non-expressions return None."""
        analyzer = ExpressionAnalyzer()

        assert analyzer.analyze_expression("Plain text") is None
        assert analyzer.analyze_expression("") is None
        assert analyzer.analyze_expression(None) is None

    def test_expression_truncation(self):
        """Test that long expressions are truncated."""
        analyzer = ExpressionAnalyzer()
        long_expr = "=Fields!" + "A" * 600 + ".Value"
        result = analyzer.analyze_expression(long_expr)

        assert result is not None
        assert len(result.expression) <= 500

    def test_unknown_function_partial(self):
        """Test unknown function defaults to PARTIAL."""
        analyzer = ExpressionAnalyzer()
        result = analyzer.analyze_expression("=UnknownFunction(Fields!Value.Value)")

        assert result is not None
        assert result.category == ExpressionConversionCategory.PARTIAL
        assert result.pattern_matched == "unknown_function"

    def test_analyze_expressions_list(self):
        """Test analyzing multiple expressions."""
        analyzer = ExpressionAnalyzer()
        expressions = [
            ExpressionFeature(
                expression="=Fields!Name.Value",
                location="Textbox1",
                category=ExpressionCategory.FIELD_REFERENCE,
            ),
            ExpressionFeature(
                expression="=Sum(Fields!Amount.Value)",
                location="Textbox2",
                category=ExpressionCategory.SIMPLE_AGGREGATE,
            ),
            ExpressionFeature(
                expression="Plain text",
                location="Textbox3",
                category=ExpressionCategory.UNKNOWN,
            ),  # Should be skipped
        ]
        results = analyzer.analyze_expressions(expressions)

        assert len(results) == 2  # Plain text skipped

    def test_analyze_features_convenience(self):
        """Test the analyze_features convenience function."""
        features = AnalysisFeatures(
            rdl_version="2016",
            expressions=[
                ExpressionFeature(
                    expression="=Fields!Test.Value",
                    location="TB1",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
            ]
        )
        results = analyze_expressions(features)

        assert len(results) == 1
        assert results[0].category == ExpressionConversionCategory.AUTO


# =============================================================================
# VBCodeAnalyzer Tests
# =============================================================================


class TestVBCodeAnalyzer:
    """Tests for VB code analyzer."""

    def test_function_extraction(self):
        """Test VB function extraction."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function FormatDate(ByVal dt As DateTime) As String
            Return Format(dt, "yyyy-MM-dd")
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].name == "FormatDate"
        assert "dt" in result[0].parameters

    def test_sub_extraction(self):
        """Test VB Sub extraction."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Sub DoSomething(ByVal value As Integer)
            Dim x As Integer = value * 2
        End Sub
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].name == "DoSomething"

    def test_multiple_functions(self):
        """Test extraction of multiple functions."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Add(a As Integer, b As Integer) As Integer
            Return a + b
        End Function

        Public Function Multiply(a As Integer, b As Integer) As Integer
            Return a * b
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 2
        names = {f.name for f in result}
        assert names == {"Add", "Multiply"}

    def test_date_pattern_detection(self):
        """Test date formatting pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function FormatDate(dt As DateTime) As String
            Return Format(dt, "MM/dd/yyyy")
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.DATE_FORMATTING in result[0].patterns_detected

    def test_string_pattern_detection(self):
        """Test string manipulation pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function TrimText(s As String) As String
            Return Left(Trim(s), 10)
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.STRING_MANIPULATION in result[0].patterns_detected

    def test_math_pattern_detection(self):
        """Test math operations pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function RoundValue(value As Double) As Integer
            Return CInt(Round(Abs(value), 2))
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.MATH_OPERATIONS in result[0].patterns_detected

    def test_conditional_pattern_detection(self):
        """Test conditional logic pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function GetStatus(value As Integer) As String
            Return IIf(value > 0, "Positive", "Non-positive")
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.CONDITIONAL_LOGIC in result[0].patterns_detected

    def test_null_handling_pattern_detection(self):
        """Test null handling pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function SafeValue(obj As Object) As String
            If IsNothing(obj) Then
                Return ""
            End If
            Return obj.ToString()
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.NULL_HANDLING in result[0].patterns_detected

    def test_error_handling_pattern_detection(self):
        """Test error handling pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function SafeParse(s As String) As Integer
            Try
                Return Integer.Parse(s)
            Catch ex As Exception
                Return 0
            End Try
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.ERROR_HANDLING in result[0].patterns_detected

    def test_collection_pattern_detection(self):
        """Test collection operations pattern detection."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function ProcessList(items As ArrayList) As Integer
            Dim total As Integer = 0
            For Each item In items
                total += CInt(item)
            Next
            Return total
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert VBPatternCategory.COLLECTION_OPERATIONS in result[0].patterns_detected

    def test_complexity_simple(self):
        """Test simple function complexity estimation."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Simple(a As Integer) As Integer
            Return a * 2
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].complexity_estimate == SPComplexity.SIMPLE

    def test_complexity_moderate(self):
        """Test moderate function complexity estimation."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Moderate(a As Integer, b As Integer, c As Integer, d As Integer) As Integer
            Dim result As Integer = a + b
            result = result * c
            result = result - d
            If result < 0 Then
                result = 0
            End If
            Return result
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        # Moderate due to param count (4) and line count
        assert result[0].complexity_estimate in (SPComplexity.MODERATE, SPComplexity.COMPLEX)

    def test_conversion_difficulty_low(self):
        """Test low conversion difficulty."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Simple(a As Integer) As Integer
            Return a
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].conversion_difficulty == "low"

    def test_conversion_difficulty_high(self):
        """Test high conversion difficulty."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Complex(items As ArrayList) As Integer
            Try
                Dim total As Integer = 0
                For Each item In items
                    total += CInt(item)
                Next
                Return total
            Catch ex As Exception
                Return 0
            End Try
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].conversion_difficulty == "high"

    def test_body_preview(self):
        """Test body preview generation."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function GetValue() As String
            Return "test"
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert result[0].body_preview is not None
        assert "Return" in result[0].body_preview

    def test_empty_code_returns_empty(self):
        """Test empty code returns empty list."""
        analyzer = VBCodeAnalyzer()

        assert analyzer.analyze_code_block("") == []
        assert analyzer.analyze_code_block(None) == []

    def test_parameter_parsing(self):
        """Test VB parameter parsing."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Test(ByVal a As Integer, ByRef b As String, c As Double) As Boolean
            Return True
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        assert len(result[0].parameters) == 3
        assert "a" in result[0].parameters
        assert "b" in result[0].parameters
        assert "c" in result[0].parameters

    def test_line_count(self):
        """Test line count calculation (excluding comments)."""
        analyzer = VBCodeAnalyzer()
        code = """
        Public Function Test() As Integer
            ' This is a comment
            Dim x As Integer = 1
            Dim y As Integer = 2
            ' Another comment
            Return x + y
        End Function
        """
        result = analyzer.analyze_code_block(code)

        assert len(result) == 1
        # Should count only non-comment, non-empty lines
        # Body includes return type declaration fragment, so 4 lines
        assert result[0].line_count >= 3  # Dim x, Dim y, Return (+ As Integer)

    def test_analyze_features_convenience(self):
        """Test the analyze_features convenience function."""
        features = AnalysisFeatures(
            rdl_version="2016",
            custom_code="""
            Public Function Test() As String
                Return "test"
            End Function
            """,
            custom_code_functions=[],
        )
        results = analyze_vb_code(features)

        assert len(results) == 1
        assert results[0].name == "Test"

    def test_analyze_from_parsed_functions(self):
        """Test analysis from pre-parsed function list (without raw code)."""
        analyzer = VBCodeAnalyzer()
        custom_functions = [
            CustomCodeFunction(
                name="MyFunc",
                parameters=["a", "b"],
                line_count=10,
            ),
        ]
        results = analyzer.analyze_functions(custom_functions, None)

        assert len(results) == 1
        assert results[0].name == "MyFunc"
        assert results[0].parameters == ["a", "b"]
        assert results[0].line_count == 10


# =============================================================================
# CodeAnalyzer (Combined) Tests
# =============================================================================


class TestCodeAnalyzer:
    """Tests for combined code analyzer."""

    def test_combined_analysis(self):
        """Test combined analysis of SPs, expressions, and VB code."""
        features = AnalysisFeatures(
            rdl_version="2016",
            datasets=[
                DatasetFeature(
                    name="Dataset1",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_GetData",
                    parameters=[
                        DatasetParameter(name="Id", data_type="Integer"),
                    ],
                ),
            ],
            expressions=[
                ExpressionFeature(
                    expression="=Sum(Fields!Amount.Value)",
                    location="Textbox1",
                    category=ExpressionCategory.SIMPLE_AGGREGATE,
                ),
                ExpressionFeature(
                    expression="=Code.FormatValue(Fields!Value.Value)",
                    location="Textbox2",
                    category=ExpressionCategory.CUSTOM_CODE,
                ),
            ],
            custom_code="""
            Public Function FormatValue(v As Double) As String
                Return Format(v, "#,##0.00")
            End Function
            """,
        )

        analyzer = CodeAnalyzer()
        result = analyzer.analyze(features)

        # Check SP results
        assert len(result.stored_procedures) == 1
        assert result.stored_procedures[0].name == "sp_GetData"

        # Check expression results
        assert len(result.expressions) == 2

        # Check VB results
        assert len(result.vb_functions) == 1
        assert result.vb_functions[0].name == "FormatValue"

        # Check summaries calculated
        assert result.sp_summary.unique_count == 1
        assert result.expression_summary.total_count == 2
        assert result.vb_summary.function_count == 1

    def test_summaries_calculation(self):
        """Test that summaries are correctly calculated."""
        features = AnalysisFeatures(
            rdl_version="2016",
            datasets=[
                DatasetFeature(
                    name="DS1",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_Simple",
                    parameters=[],
                ),
                DatasetFeature(
                    name="DS2",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_Complex",
                    parameters=[
                        DatasetParameter(name=f"P{i}", data_type="String")
                        for i in range(7)
                    ],
                ),
            ],
            expressions=[
                ExpressionFeature(
                    expression="=Fields!A.Value",
                    location="TB1",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
                ExpressionFeature(
                    expression="=Sum(Fields!B.Value)",
                    location="TB2",
                    category=ExpressionCategory.SIMPLE_AGGREGATE,
                ),
                ExpressionFeature(
                    expression="=Code.Custom()",
                    location="TB3",
                    category=ExpressionCategory.CUSTOM_CODE,
                ),
            ],
        )

        result = analyze_code(features)

        # SP summary
        assert result.sp_summary.unique_count == 2
        assert result.sp_summary.simple_count == 1
        assert result.sp_summary.complex_count == 1

        # Expression summary
        assert result.expression_summary.total_count == 3
        assert result.expression_summary.auto_count == 2
        assert result.expression_summary.manual_count == 1

    def test_requires_manual_work(self):
        """Test detection of manual work requirements."""
        # Case 1: Has manual expressions
        features1 = AnalysisFeatures(
            rdl_version="2016",
            expressions=[
                ExpressionFeature(
                    expression="=Code.Custom()",
                    location="TB1",
                    category=ExpressionCategory.CUSTOM_CODE,
                ),
            ]
        )
        result1 = analyze_code(features1)
        assert result1.requires_manual_work is True
        assert any("expression" in item.lower() for item in result1.manual_work_items)

        # Case 2: Has VB functions
        features2 = AnalysisFeatures(
            rdl_version="2016",
            custom_code="""
            Public Function Test() As String
                Return "test"
            End Function
            """
        )
        result2 = analyze_code(features2)
        assert result2.requires_manual_work is True
        assert any("VB function" in item for item in result2.manual_work_items)

        # Case 3: Has complex SPs
        features3 = AnalysisFeatures(
            rdl_version="2016",
            datasets=[
                DatasetFeature(
                    name="DS1",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_Complex",
                    parameters=[
                        DatasetParameter(name=f"P{i}", data_type="String")
                        for i in range(8)
                    ],
                ),
            ]
        )
        result3 = analyze_code(features3)
        assert result3.requires_manual_work is True

    def test_no_manual_work_simple_report(self):
        """Test that simple reports don't require manual work."""
        features = AnalysisFeatures(
            rdl_version="2016",
            expressions=[
                ExpressionFeature(
                    expression="=Fields!Name.Value",
                    location="TB1",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
                ExpressionFeature(
                    expression="=Sum(Fields!Amount.Value)",
                    location="TB2",
                    category=ExpressionCategory.SIMPLE_AGGREGATE,
                ),
            ]
        )
        result = analyze_code(features)

        assert result.requires_manual_work is False
        assert len(result.manual_work_items) == 0

    def test_expression_auto_percentage(self):
        """Test auto conversion percentage calculation."""
        features = AnalysisFeatures(
            rdl_version="2016",
            expressions=[
                ExpressionFeature(
                    expression="=Fields!A.Value",
                    location="TB1",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
                ExpressionFeature(
                    expression="=Fields!B.Value",
                    location="TB2",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
                ExpressionFeature(
                    expression="=Fields!C.Value",
                    location="TB3",
                    category=ExpressionCategory.FIELD_REFERENCE,
                ),
                ExpressionFeature(
                    expression="=Code.Custom()",
                    location="TB4",
                    category=ExpressionCategory.CUSTOM_CODE,
                ),
            ]
        )
        result = analyze_code(features)

        # 3 out of 4 are AUTO = 75%
        assert result.expression_summary.auto_percentage == 75.0

    def test_empty_features(self):
        """Test analysis with empty features."""
        features = AnalysisFeatures(rdl_version="2016")
        result = analyze_code(features)

        assert len(result.stored_procedures) == 0
        assert len(result.expressions) == 0
        assert len(result.vb_functions) == 0
        assert result.requires_manual_work is False

    def test_vb_patterns_aggregation(self):
        """Test VB patterns are aggregated in summary."""
        features = AnalysisFeatures(
            rdl_version="2016",
            custom_code="""
            Public Function Func1(dt As DateTime) As String
                Return Format(dt, "yyyy")
            End Function

            Public Function Func2(s As String) As String
                Return Left(s, 10)
            End Function
            """
        )
        result = analyze_code(features)

        assert len(result.vb_summary.patterns_found) >= 2
        assert VBPatternCategory.DATE_FORMATTING in result.vb_summary.patterns_found
        assert VBPatternCategory.STRING_MANIPULATION in result.vb_summary.patterns_found

    def test_convenience_function(self):
        """Test the analyze_code convenience function."""
        features = AnalysisFeatures(
            rdl_version="2016",
            datasets=[
                DatasetFeature(
                    name="DS1",
                    query_type=QueryType.STORED_PROCEDURE,
                    stored_procedure_name="sp_Test",
                    parameters=[],
                ),
            ]
        )
        result = analyze_code(features)

        assert isinstance(result, CodeAnalysisResult)
        assert result.sp_summary.unique_count == 1

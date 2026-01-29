"""Code Analysis Pydantic schemas for SP, expression, and VB analysis."""

from enum import Enum

from pydantic import BaseModel, Field, computed_field


class SPComplexity(str, Enum):
    """Stored procedure complexity based on parameter count."""

    SIMPLE = "simple"  # 0-2 parameters
    MODERATE = "moderate"  # 3-5 parameters
    COMPLEX = "complex"  # 6+ parameters


class ExpressionConversionCategory(str, Enum):
    """Category for expression conversion difficulty."""

    AUTO = "auto"  # Can be automatically converted
    PARTIAL = "partial"  # Needs some manual adjustment
    MANUAL = "manual"  # Requires full manual conversion


class VBPatternCategory(str, Enum):
    """Categories of patterns found in VB code."""

    DATE_FORMATTING = "date_formatting"
    STRING_MANIPULATION = "string_manipulation"
    MATH_OPERATIONS = "math_operations"
    CONDITIONAL_LOGIC = "conditional_logic"
    NULL_HANDLING = "null_handling"
    ERROR_HANDLING = "error_handling"
    COLLECTION_OPERATIONS = "collection_operations"


class StoredProcedureAnalysis(BaseModel):
    """Analysis result for a stored procedure."""

    name: str
    complexity: SPComplexity
    parameter_count: int
    parameters: list[str] = Field(default_factory=list)
    datasets_using: list[str] = Field(default_factory=list)
    conversion_notes: str | None = None

    @computed_field
    @property
    def usage_count(self) -> int:
        """Number of datasets using this stored procedure."""
        return len(self.datasets_using)

    @computed_field
    @property
    def is_shared(self) -> bool:
        """Whether this SP is used by multiple datasets."""
        return len(self.datasets_using) > 1


class ExpressionAnalysis(BaseModel):
    """Analysis result for an expression."""

    expression: str
    category: ExpressionConversionCategory
    location: str
    item_name: str | None = None
    reason: str
    suggested_dax: str | None = None
    pattern_matched: str | None = None


class VBFunctionAnalysis(BaseModel):
    """Analysis result for a VB.NET function."""

    name: str
    parameters: list[str] = Field(default_factory=list)
    line_count: int = 0
    patterns_detected: list[VBPatternCategory] = Field(default_factory=list)
    complexity_estimate: SPComplexity = SPComplexity.SIMPLE
    body_preview: str | None = None  # First 200 chars of body
    conversion_difficulty: str = "medium"  # low, medium, high

    @computed_field
    @property
    def parameter_count(self) -> int:
        """Number of parameters."""
        return len(self.parameters)


class ExpressionSummary(BaseModel):
    """Summary of expression analysis."""

    total_count: int = 0
    auto_count: int = 0
    partial_count: int = 0
    manual_count: int = 0

    @computed_field
    @property
    def auto_percentage(self) -> float:
        """Percentage of expressions that can be auto-converted."""
        if self.total_count == 0:
            return 100.0
        return round((self.auto_count / self.total_count) * 100, 1)


class StoredProcedureSummary(BaseModel):
    """Summary of stored procedure analysis."""

    total_count: int = 0
    unique_count: int = 0
    simple_count: int = 0
    moderate_count: int = 0
    complex_count: int = 0
    shared_count: int = 0  # SPs used by multiple datasets


class VBCodeSummary(BaseModel):
    """Summary of VB code analysis."""

    has_custom_code: bool = False
    function_count: int = 0
    total_line_count: int = 0
    patterns_found: list[VBPatternCategory] = Field(default_factory=list)


class CodeAnalysisResult(BaseModel):
    """Complete code analysis result combining SP, expression, and VB analysis."""

    # Detailed results
    stored_procedures: list[StoredProcedureAnalysis] = Field(default_factory=list)
    expressions: list[ExpressionAnalysis] = Field(default_factory=list)
    vb_functions: list[VBFunctionAnalysis] = Field(default_factory=list)

    # Summaries
    sp_summary: StoredProcedureSummary = Field(default_factory=StoredProcedureSummary)
    expression_summary: ExpressionSummary = Field(default_factory=ExpressionSummary)
    vb_summary: VBCodeSummary = Field(default_factory=VBCodeSummary)

    # Overall conversion assessment
    requires_manual_work: bool = False
    manual_work_items: list[str] = Field(default_factory=list)

    def calculate_summaries(self) -> None:
        """Calculate summaries from detailed results."""
        # SP summary
        self.sp_summary = StoredProcedureSummary(
            total_count=sum(sp.usage_count for sp in self.stored_procedures),
            unique_count=len(self.stored_procedures),
            simple_count=sum(
                1 for sp in self.stored_procedures if sp.complexity == SPComplexity.SIMPLE
            ),
            moderate_count=sum(
                1 for sp in self.stored_procedures
                if sp.complexity == SPComplexity.MODERATE
            ),
            complex_count=sum(
                1 for sp in self.stored_procedures if sp.complexity == SPComplexity.COMPLEX
            ),
            shared_count=sum(1 for sp in self.stored_procedures if sp.is_shared),
        )

        # Expression summary
        self.expression_summary = ExpressionSummary(
            total_count=len(self.expressions),
            auto_count=sum(
                1 for e in self.expressions
                if e.category == ExpressionConversionCategory.AUTO
            ),
            partial_count=sum(
                1 for e in self.expressions
                if e.category == ExpressionConversionCategory.PARTIAL
            ),
            manual_count=sum(
                1 for e in self.expressions
                if e.category == ExpressionConversionCategory.MANUAL
            ),
        )

        # VB summary
        all_patterns = set()
        for func in self.vb_functions:
            all_patterns.update(func.patterns_detected)

        self.vb_summary = VBCodeSummary(
            has_custom_code=len(self.vb_functions) > 0,
            function_count=len(self.vb_functions),
            total_line_count=sum(f.line_count for f in self.vb_functions),
            patterns_found=list(all_patterns),
        )

        # Determine if manual work is required
        self.requires_manual_work = (
            self.expression_summary.manual_count > 0
            or self.sp_summary.complex_count > 0
            or self.vb_summary.function_count > 0
        )

        # Build manual work items list
        self.manual_work_items = []
        if self.sp_summary.unique_count > 0:
            self.manual_work_items.append(
                f"{self.sp_summary.unique_count} stored procedure(s) to convert"
            )
        if self.expression_summary.manual_count > 0:
            self.manual_work_items.append(
                f"{self.expression_summary.manual_count} expression(s) requiring manual conversion"
            )
        if self.vb_summary.function_count > 0:
            self.manual_work_items.append(
                f"{self.vb_summary.function_count} VB function(s) to rewrite"
            )

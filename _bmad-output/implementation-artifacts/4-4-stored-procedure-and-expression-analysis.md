# Story 4.4: Stored Procedure and Expression Analysis

Status: done

## Story

As the **system**,
I want **to identify stored procedures and complex expressions**,
So that **the TODO list accurately reflects manual work requirements**.

## Acceptance Criteria

### AC1: Stored Procedure Name Extraction
**Given** a dataset uses a stored procedure
**When** analyzing the dataset
**Then** the stored procedure name is extracted
**And** the procedure is marked as requiring conversion attention
**And** the SP complexity is estimated (simple/moderate/complex) based on parameter count

### AC2: Multiple Stored Procedure Detection
**Given** multiple datasets with stored procedures
**When** analysis completes
**Then** all unique stored procedures are listed
**And** duplicate references are noted (e.g., "SP_GetSales used in 3 datasets")

### AC3: Expression Categorization
**Given** expressions are found in the report
**When** analyzing expressions
**Then** each expression is categorized:
  - **Auto-convertible**: Simple field references, basic aggregates (Sum, Count, Avg)
  - **Partial**: Lookup, Previous, aggregate with filters
  - **Manual**: Custom VB code calls, RunningValue, RowNumber with scope

### AC4: VB Custom Code Analysis
**Given** VB custom code is present
**When** analyzing the code block
**Then** each function is identified
**And** function complexity is estimated (lines of code, parameters)
**And** common patterns are flagged (e.g., "date formatting", "string manipulation")

### AC5: Expression Storage with Context
**Given** expressions requiring attention
**When** storing results
**Then** each is saved with:
  - Location (which report item)
  - Expression text
  - Category (auto/partial/manual)
  - Reason for categorization

## Tasks / Subtasks

- [x] **Task 1: Create SP Analyzer Service** (AC: 1, 2)
  - [x] Create `backend/app/services/sp_analyzer.py`
  - [x] Implement SP name extraction from dataset queries
  - [x] Estimate SP complexity from parameter count
  - [x] Track SP usage across datasets

- [x] **Task 2: Implement SP Complexity Estimation** (AC: 1)
  - [x] Define complexity criteria:
    - Simple: 0-2 parameters
    - Moderate: 3-5 parameters
    - Complex: 6+ parameters
  - [x] Parse parameter definitions from RDL
  - [x] Return complexity rating with confidence

- [x] **Task 3: Implement SP Deduplication and Usage Tracking** (AC: 2)
  - [x] Create dictionary of unique SP names
  - [x] Track which datasets reference each SP
  - [x] Generate usage summary (SP name -> dataset list)

- [x] **Task 4: Create Expression Analyzer Service** (AC: 3, 5)
  - [x] Create `backend/app/services/expression_analyzer.py`
  - [x] Implement `categorize_expression(expr: str) -> ExpressionCategory`
  - [x] Use regex patterns for pattern matching
  - [x] Extract location context from RDL element

- [x] **Task 5: Implement Expression Category Rules** (AC: 3)
  - [x] Auto-convertible patterns:
    - `=Fields!Name.Value`
    - `=Sum(Fields!Amount.Value)`
    - `=Count(Fields!ID.Value)`
  - [x] Partial patterns:
    - `Lookup(...)`, `LookupSet(...)`, `MultiLookup(...)`
    - `Previous(...)`, `First(...)`, `Last(...)`
    - Aggregates with filters: `Sum(..., "group")`
  - [x] Manual patterns:
    - `Code.FunctionName(...)`
    - `RunningValue(...)`
    - `RowNumber("scope")`

- [x] **Task 6: Create VB Code Analyzer** (AC: 4)
  - [x] Create `backend/app/services/vb_analyzer.py`
  - [x] Parse VB function declarations
  - [x] Count lines of code per function
  - [x] Identify common patterns (date, string, math)

- [x] **Task 7: Implement VB Pattern Detection** (AC: 4)
  - [x] Date formatting patterns (Format, DateDiff, DateAdd)
  - [x] String manipulation (Left, Right, Mid, Replace)
  - [x] Math operations (Round, Abs, custom calculations)
  - [x] Conditional logic (IIf, Select Case)

- [x] **Task 8: Create Analysis Result Models** (AC: 5)
  - [x] Create `StoredProcedureAnalysis` Pydantic model
  - [x] Create `ExpressionAnalysis` Pydantic model
  - [x] Create `VBFunctionAnalysis` Pydantic model
  - [x] Create combined `CodeAnalysisResult` model

- [x] **Task 9: Unit Testing** (AC: 1, 2, 3, 4, 5)
  - [x] Test SP extraction from various query formats
  - [x] Test expression categorization accuracy
  - [x] Test VB code parsing
  - [x] Test pattern detection

## Dev Notes

### Technical Implementation

**SP Analyzer Service:**
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class SPComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

@dataclass
class StoredProcedureInfo:
    name: str
    complexity: SPComplexity
    parameter_count: int
    parameters: List[str]
    datasets_using: List[str]

class SPAnalyzer:
    COMPLEXITY_THRESHOLDS = {
        'simple': (0, 2),
        'moderate': (3, 5),
        'complex': (6, float('inf')),
    }

    def analyze_datasets(self, datasets: List[DatasetFeature]) -> Dict[str, StoredProcedureInfo]:
        """Analyze all datasets for stored procedures."""
        sp_map: Dict[str, StoredProcedureInfo] = {}

        for dataset in datasets:
            if dataset.query_type != QueryType.STORED_PROCEDURE:
                continue

            sp_name = dataset.stored_procedure_name
            if sp_name in sp_map:
                # Track additional usage
                sp_map[sp_name].datasets_using.append(dataset.name)
            else:
                sp_map[sp_name] = StoredProcedureInfo(
                    name=sp_name,
                    complexity=self._estimate_complexity(dataset.parameter_count),
                    parameter_count=dataset.parameter_count,
                    parameters=[p['name'] for p in dataset.parameters],
                    datasets_using=[dataset.name]
                )

        return sp_map

    def _estimate_complexity(self, param_count: int) -> SPComplexity:
        """Estimate SP complexity based on parameter count."""
        if param_count <= 2:
            return SPComplexity.SIMPLE
        elif param_count <= 5:
            return SPComplexity.MODERATE
        else:
            return SPComplexity.COMPLEX
```

**Expression Analyzer Service:**
```python
import re
from typing import Tuple

class ExpressionConversionCategory(str, Enum):
    AUTO = "auto"      # Can be automatically converted
    PARTIAL = "partial"  # Needs some manual adjustment
    MANUAL = "manual"    # Requires full manual conversion

@dataclass
class ExpressionAnalysisResult:
    expression: str
    category: ExpressionConversionCategory
    location: str
    item_name: str
    reason: str
    suggested_dax: Optional[str] = None

class ExpressionAnalyzer:
    # Regex patterns for expression categorization
    PATTERNS = {
        'simple_field': (r'^=Fields![\w]+\.Value$', ExpressionConversionCategory.AUTO),
        'simple_sum': (r'^=Sum\(Fields![\w]+\.Value\)$', ExpressionConversionCategory.AUTO),
        'simple_count': (r'^=Count\(Fields![\w]+\.Value\)$', ExpressionConversionCategory.AUTO),
        'simple_avg': (r'^=Avg\(Fields![\w]+\.Value\)$', ExpressionConversionCategory.AUTO),
        'simple_min': (r'^=Min\(Fields![\w]+\.Value\)$', ExpressionConversionCategory.AUTO),
        'simple_max': (r'^=Max\(Fields![\w]+\.Value\)$', ExpressionConversionCategory.AUTO),
        'lookup': (r'Lookup\s*\(', ExpressionConversionCategory.PARTIAL),
        'lookupset': (r'LookupSet\s*\(', ExpressionConversionCategory.PARTIAL),
        'multilookup': (r'MultiLookup\s*\(', ExpressionConversionCategory.PARTIAL),
        'previous': (r'Previous\s*\(', ExpressionConversionCategory.PARTIAL),
        'first': (r'First\s*\(', ExpressionConversionCategory.PARTIAL),
        'last': (r'Last\s*\(', ExpressionConversionCategory.PARTIAL),
        'aggregate_with_scope': (r'(Sum|Count|Avg)\([^)]+,\s*"[\w]+"', ExpressionConversionCategory.PARTIAL),
        'custom_code': (r'Code\.[\w]+\s*\(', ExpressionConversionCategory.MANUAL),
        'running_value': (r'RunningValue\s*\(', ExpressionConversionCategory.MANUAL),
        'row_number': (r'RowNumber\s*\(', ExpressionConversionCategory.MANUAL),
    }

    def analyze_expression(self, expression: str, location: str, item_name: str) -> ExpressionAnalysisResult:
        """Analyze a single expression and categorize it."""
        if not expression.startswith('='):
            return None

        category, reason = self._categorize(expression)

        return ExpressionAnalysisResult(
            expression=expression,
            category=category,
            location=location,
            item_name=item_name,
            reason=reason,
            suggested_dax=self._suggest_dax(expression, category)
        )

    def _categorize(self, expression: str) -> Tuple[ExpressionConversionCategory, str]:
        """Determine the category of an expression."""
        for pattern_name, (pattern, category) in self.PATTERNS.items():
            if re.search(pattern, expression, re.IGNORECASE):
                return category, f"Matched pattern: {pattern_name}"

        # Default to PARTIAL if contains any function call
        if re.search(r'[\w]+\s*\(', expression):
            return ExpressionConversionCategory.PARTIAL, "Contains function call"

        return ExpressionConversionCategory.AUTO, "Simple expression"

    def _suggest_dax(self, expression: str, category: ExpressionConversionCategory) -> Optional[str]:
        """Suggest DAX equivalent for auto-convertible expressions."""
        if category != ExpressionConversionCategory.AUTO:
            return None

        # Simple field reference
        match = re.match(r'^=Fields!([\w]+)\.Value$', expression)
        if match:
            return f"[{match.group(1)}]"

        # Simple aggregates
        agg_match = re.match(r'^=(Sum|Count|Avg|Min|Max)\(Fields!([\w]+)\.Value\)$', expression)
        if agg_match:
            func, field = agg_match.groups()
            return f"{func.upper()}([{field}])"

        return None
```

**VB Code Analyzer:**
```python
import re
from typing import List

@dataclass
class VBFunctionInfo:
    name: str
    parameters: List[str]
    line_count: int
    patterns_detected: List[str]
    body: str

class VBCodeAnalyzer:
    # Common VB patterns
    PATTERN_DETECTORS = {
        'date_formatting': [r'Format\s*\(', r'DateDiff', r'DateAdd', r'DatePart'],
        'string_manipulation': [r'Left\s*\(', r'Right\s*\(', r'Mid\s*\(', r'Replace\s*\(', r'Trim'],
        'math_operations': [r'Round\s*\(', r'Abs\s*\(', r'Int\s*\(', r'CDbl', r'CInt'],
        'conditional_logic': [r'IIf\s*\(', r'Select\s+Case', r'If\s+.+\s+Then'],
        'null_handling': [r'IsNothing\s*\(', r'IsDBNull', r'Nothing'],
    }

    def analyze_code_block(self, code: str) -> List[VBFunctionInfo]:
        """Parse VB code block and analyze each function."""
        functions = []

        # Match function declarations
        func_pattern = r'(?:Public |Private )?(?:Shared )?Function\s+(\w+)\s*\(([^)]*)\)(.*?)End Function'
        matches = re.findall(func_pattern, code, re.IGNORECASE | re.DOTALL)

        for name, params, body in matches:
            parameters = [p.strip() for p in params.split(',') if p.strip()]
            line_count = len([l for l in body.split('\n') if l.strip()])
            patterns = self._detect_patterns(body)

            functions.append(VBFunctionInfo(
                name=name,
                parameters=parameters,
                line_count=line_count,
                patterns_detected=patterns,
                body=body.strip()
            ))

        return functions

    def _detect_patterns(self, code: str) -> List[str]:
        """Detect common patterns in VB code."""
        detected = []
        for pattern_name, regex_list in self.PATTERN_DETECTORS.items():
            for regex in regex_list:
                if re.search(regex, code, re.IGNORECASE):
                    detected.append(pattern_name)
                    break
        return detected
```

**Combined Analysis Result Model:**
```python
from pydantic import BaseModel
from typing import List, Dict

class StoredProcedureSchema(BaseModel):
    name: str
    complexity: SPComplexity
    parameter_count: int
    parameters: List[str]
    datasets_using: List[str]
    usage_count: int

    @property
    def usage_count(self) -> int:
        return len(self.datasets_using)

class ExpressionSchema(BaseModel):
    expression: str
    category: ExpressionConversionCategory
    location: str
    item_name: str
    reason: str
    suggested_dax: Optional[str] = None

class VBFunctionSchema(BaseModel):
    name: str
    parameters: List[str]
    line_count: int
    patterns_detected: List[str]
    complexity_estimate: str  # simple, moderate, complex

class CodeAnalysisResult(BaseModel):
    stored_procedures: List[StoredProcedureSchema]
    expressions: List[ExpressionSchema]
    vb_functions: List[VBFunctionSchema]

    # Summary counts
    sp_count: int
    auto_expression_count: int
    partial_expression_count: int
    manual_expression_count: int
    vb_function_count: int

    def model_post_init(self, __context):
        self.sp_count = len(self.stored_procedures)
        self.vb_function_count = len(self.vb_functions)
        self.auto_expression_count = sum(1 for e in self.expressions if e.category == ExpressionConversionCategory.AUTO)
        self.partial_expression_count = sum(1 for e in self.expressions if e.category == ExpressionConversionCategory.PARTIAL)
        self.manual_expression_count = sum(1 for e in self.expressions if e.category == ExpressionConversionCategory.MANUAL)
```

### Expression Categorization Reference

| Category | Patterns | DAX Equivalent Available |
|----------|----------|--------------------------|
| Auto | `=Fields!X.Value` | Yes |
| Auto | `=Sum(Fields!X.Value)` | Yes |
| Auto | `=Count(Fields!X.Value)` | Yes |
| Partial | `Lookup(...)` | Needs RELATED/LOOKUPVALUE |
| Partial | `Previous(...)` | Needs calculated column |
| Partial | `Sum(..., "scope")` | Needs CALCULATE |
| Manual | `Code.Function(...)` | No - requires manual conversion |
| Manual | `RunningValue(...)` | Needs WINDOW function |
| Manual | `RowNumber(...)` | Needs INDEX/ROWNUMBER |

### SP Complexity Criteria

| Complexity | Parameter Count | Typical Conversion Effort |
|------------|-----------------|---------------------------|
| Simple | 0-2 | Usually straightforward SELECT rewrite |
| Moderate | 3-5 | May involve temp tables or CTEs |
| Complex | 6+ | Likely has business logic to preserve |

### File Structure

```
backend/app/
  services/
    sp_analyzer.py         # Stored procedure analysis
    expression_analyzer.py # Expression categorization
    vb_analyzer.py         # VB code analysis
  schemas/
    code_analysis.py       # Result models
```

### Dependencies

- Story 4.2 (RDL Parsing) - Provides extracted features
- regex library (standard library)

### References

- [Source: epics.md#Story 4.4] - Original story definition
- [Source: prd.md#FR14, FR15] - SP and expression identification requirements

### Architecture Compliance Checklist

- [x] Each analyzer is a separate service
- [x] Regex patterns are documented and testable
- [x] Categories have clear, consistent definitions
- [x] Results include actionable context
- [x] Models support JSON serialization

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes List

- Implemented SPAnalyzer with complexity estimation (simple: 0-2, moderate: 3-5, complex: 6+ params)
- SP deduplication handles schema prefixes (e.g., `dbo.sp_GetData` matches `sp_GetData`)
- ExpressionAnalyzer uses 25+ regex patterns for AUTO/PARTIAL/MANUAL categorization
- DAX suggestions provided for auto-convertible expressions
- VBCodeAnalyzer detects 7 pattern categories: date_formatting, string_manipulation, math_operations, conditional_logic, null_handling, error_handling, collection_operations
- All models use Pydantic v2 with computed_field decorators
- CodeAnalysisResult.calculate_summaries() provides aggregated statistics
- 59 unit tests covering all analyzers and pattern detection

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created SP analyzer service | `app/services/sp_analyzer.py` |
| 2026-01-22 | Created expression analyzer service | `app/services/expression_analyzer.py` |
| 2026-01-22 | Created VB code analyzer service | `app/services/vb_analyzer.py` |
| 2026-01-22 | Created combined code analyzer | `app/services/code_analyzer.py` |
| 2026-01-22 | Created code analysis schemas | `app/schemas/code_analysis.py` |
| 2026-01-22 | Added 59 unit tests | `tests/test_code_analysis.py` |

### File List

- `backend/app/schemas/code_analysis.py` - Pydantic models (SPComplexity, ExpressionConversionCategory, VBPatternCategory, StoredProcedureAnalysis, ExpressionAnalysis, VBFunctionAnalysis, CodeAnalysisResult, summaries)
- `backend/app/services/sp_analyzer.py` - SPAnalyzer class with complexity estimation and deduplication
- `backend/app/services/expression_analyzer.py` - ExpressionAnalyzer class with 25+ categorization patterns
- `backend/app/services/vb_analyzer.py` - VBCodeAnalyzer class with function parsing and pattern detection
- `backend/app/services/code_analyzer.py` - Combined CodeAnalyzer orchestrating all analyzers
- `backend/tests/test_code_analysis.py` - 59 unit tests for all code analysis functionality

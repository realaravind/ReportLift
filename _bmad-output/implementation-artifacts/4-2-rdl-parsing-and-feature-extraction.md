# Story 4.2: RDL Parsing and Feature Extraction

Status: done

## Story

As the **system**,
I want **to parse RDL XML files and extract complexity features**,
So that **the analysis engine can classify and score reports accurately**.

## Acceptance Criteria

### AC1: RDL Validation and Namespace Detection
**Given** an RDL file is received for analysis
**When** parsing begins
**Then** the XML is validated as proper RDL format
**And** the RDL namespace version is detected (2008, 2010, 2016)

### AC2: Dataset Feature Extraction
**Given** a valid RDL file
**When** extracting dataset features
**Then** the following are captured:
  - Dataset count
  - Query type for each dataset (embedded SQL, stored procedure, shared dataset reference)
  - Parameter count and types
  - Field mappings

### AC3: Visual Feature Extraction
**Given** a valid RDL file
**When** extracting visual features
**Then** the following are captured:
  - Report item types (Table, Matrix, Chart, Gauge, Map, etc.)
  - Item count by type
  - Nested items (subreports, rectangles with children)
  - Grouping complexity (row groups, column groups, recursive groups)

### AC4: Expression Feature Extraction
**Given** a valid RDL file
**When** extracting expression features
**Then** the following are captured:
  - Expression count and locations
  - Expression types (field references, aggregates, custom code, lookups)
  - VB.NET custom code functions
  - RunningValue expressions (complexity flag)

### AC5: Layout Feature Extraction
**Given** a valid RDL file
**When** extracting layout features
**Then** the following are captured:
  - Page dimensions and orientation
  - Header/footer presence
  - Multi-column layout
  - Print-specific settings

### AC6: Error Handling for Invalid RDL
**Given** an invalid or corrupted RDL file
**When** parsing fails
**Then** an error is returned: "Invalid RDL format"
**And** the specific XML parse error is included

## Tasks / Subtasks

- [x] **Task 1: Create RDL Parser Service** (AC: 1)
  - [x] Create `backend/app/services/rdl_parser.py`
  - [x] Implement XML parsing with lxml
  - [x] Detect RDL namespace version from XML declaration
  - [x] Support namespaces: 2005, 2008, 2010, 2016
  - [x] Validate RDL root element structure

- [x] **Task 2: Implement Dataset Extraction** (AC: 2)
  - [x] Parse `<DataSets>` element
  - [x] Extract dataset names and query types
  - [x] Identify stored procedure calls vs embedded SQL
  - [x] Extract parameters with names and types
  - [x] Map dataset fields to their data types

- [x] **Task 3: Implement Visual Extraction** (AC: 3)
  - [x] Parse `<ReportItems>` elements recursively
  - [x] Categorize by type: Tablix, Chart, Gauge, Map, etc.
  - [x] Detect subreport references
  - [x] Count nested rectangles and containers
  - [x] Analyze Tablix grouping structure

- [x] **Task 4: Implement Expression Extraction** (AC: 4)
  - [x] Scan all elements for `=` expression prefix
  - [x] Categorize expressions by complexity
  - [x] Extract `<Code>` block for VB custom functions
  - [x] Identify RunningValue, RowNumber, Previous calls
  - [x] Parse Lookup and MultiLookup expressions

- [x] **Task 5: Implement Layout Extraction** (AC: 5)
  - [x] Parse `<Page>` element for dimensions
  - [x] Detect `<PageHeader>` and `<PageFooter>`
  - [x] Check for `<Columns>` multi-column setting
  - [x] Extract print margins and orientation

- [x] **Task 6: Create AnalysisFeatures Pydantic Model** (AC: 2, 3, 4, 5)
  - [x] Create `backend/app/schemas/analysis.py`
  - [x] Define DatasetFeature model
  - [x] Define VisualFeature model
  - [x] Define ExpressionFeature model
  - [x] Define LayoutFeature model
  - [x] Define AnalysisFeatures composite model

- [x] **Task 7: Implement Error Handling** (AC: 6)
  - [x] Catch lxml parsing exceptions
  - [x] Create custom RDLParseError exception
  - [x] Include line number and error details
  - [x] Log parsing failures for debugging

- [x] **Task 8: Unit Testing** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Create test RDL files for each scenario
  - [x] Test namespace version detection
  - [x] Test dataset extraction accuracy
  - [x] Test visual type detection
  - [x] Test expression categorization
  - [x] Test invalid RDL error handling

## Dev Notes

### Technical Implementation

**lxml for XML Parsing:**
```python
from lxml import etree
from typing import Optional

class RDLParser:
    # RDL namespace mappings
    NAMESPACES = {
        '2008': 'http://schemas.microsoft.com/sqlserver/reporting/2008/01/reportdefinition',
        '2010': 'http://schemas.microsoft.com/sqlserver/reporting/2010/01/reportdefinition',
        '2016': 'http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition',
    }

    def __init__(self, rdl_content: bytes):
        self.tree = etree.fromstring(rdl_content)
        self.namespace = self._detect_namespace()
        self.ns = {'rd': self.namespace}

    def _detect_namespace(self) -> str:
        """Detect RDL namespace from root element."""
        root_ns = self.tree.nsmap.get(None)
        for version, ns_uri in self.NAMESPACES.items():
            if ns_uri == root_ns:
                return ns_uri
        raise RDLParseError(f"Unknown RDL namespace: {root_ns}")
```

**Pydantic AnalysisFeatures Model:**
```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class QueryType(str, Enum):
    EMBEDDED_SQL = "embedded_sql"
    STORED_PROCEDURE = "stored_procedure"
    SHARED_DATASET = "shared_dataset"

class DatasetFeature(BaseModel):
    name: str
    query_type: QueryType
    stored_procedure_name: Optional[str] = None
    parameter_count: int
    field_count: int
    parameters: List[dict] = []

class VisualType(str, Enum):
    TABLE = "table"
    MATRIX = "matrix"
    CHART = "chart"
    GAUGE = "gauge"
    MAP = "map"
    SUBREPORT = "subreport"
    TEXTBOX = "textbox"
    IMAGE = "image"
    RECTANGLE = "rectangle"

class VisualFeature(BaseModel):
    type: VisualType
    name: str
    row_groups: int = 0
    column_groups: int = 0
    has_recursive_group: bool = False
    nested_items: int = 0

class ExpressionCategory(str, Enum):
    FIELD_REFERENCE = "field_reference"
    SIMPLE_AGGREGATE = "simple_aggregate"
    COMPLEX_AGGREGATE = "complex_aggregate"
    LOOKUP = "lookup"
    CUSTOM_CODE = "custom_code"
    RUNNING_VALUE = "running_value"

class ExpressionFeature(BaseModel):
    expression: str
    category: ExpressionCategory
    location: str
    item_name: str

class LayoutFeature(BaseModel):
    page_width: float
    page_height: float
    orientation: str  # Portrait, Landscape
    has_header: bool
    has_footer: bool
    column_count: int = 1
    margins: dict = {}

class AnalysisFeatures(BaseModel):
    rdl_version: str
    datasets: List[DatasetFeature]
    visuals: List[VisualFeature]
    expressions: List[ExpressionFeature]
    layout: LayoutFeature
    custom_code: Optional[str] = None
    custom_code_functions: List[str] = []

    # Summary counts
    dataset_count: int
    stored_procedure_count: int
    visual_count: int
    expression_count: int
    subreport_count: int
    running_value_count: int
```

**Expression Detection Regex:**
```python
import re

# Pattern to detect expression types
EXPRESSION_PATTERNS = {
    'field_reference': r'^=Fields!(\w+)\.Value$',
    'simple_aggregate': r'^=(Sum|Count|Avg|Min|Max)\(Fields!',
    'running_value': r'RunningValue\(',
    'lookup': r'(Lookup|LookupSet|MultiLookup)\(',
    'custom_code': r'Code\.\w+\(',
    'row_number': r'RowNumber\(',
}

def categorize_expression(expr: str) -> ExpressionCategory:
    expr = expr.strip()
    if not expr.startswith('='):
        return None  # Not an expression

    for category, pattern in EXPRESSION_PATTERNS.items():
        if re.search(pattern, expr):
            return ExpressionCategory(category)

    # Default to complex if contains aggregate with filter
    if re.search(r'(Sum|Count|Avg)\([^)]+,[^)]+\)', expr):
        return ExpressionCategory.COMPLEX_AGGREGATE

    return ExpressionCategory.FIELD_REFERENCE
```

**VB Custom Code Parser:**
```python
def extract_vb_functions(code_block: str) -> List[str]:
    """Extract function names from VB.NET code block."""
    pattern = r'(?:Public |Private )?(?:Shared )?Function\s+(\w+)'
    matches = re.findall(pattern, code_block, re.IGNORECASE)
    return matches
```

### RDL Element Reference

| Element | XPath | Purpose |
|---------|-------|---------|
| DataSets | `//rd:DataSets/rd:DataSet` | Report data sources |
| Query | `rd:Query/rd:CommandText` | SQL or SP name |
| QueryType | `rd:Query/rd:CommandType` | Text, StoredProcedure |
| Tablix | `//rd:Tablix` | Tables and matrices |
| Chart | `//rd:Chart` | Chart visuals |
| Subreport | `//rd:Subreport` | Embedded subreports |
| Code | `//rd:Code` | VB custom code |
| PageHeight | `//rd:Page/rd:PageHeight` | Page dimensions |

### File Structure

```
backend/app/
  services/
    rdl_parser.py       # RDL parsing logic
    feature_extractor.py # Feature extraction
  schemas/
    analysis.py         # Pydantic models
```

### Dependencies

- lxml>=5.0.0 (add to requirements.txt)
- Story 4.1 (Trigger Analysis) - Provides RDL content

### References

- [Source: epics.md#Story 4.2] - Original story definition
- [Source: prd.md#FR10] - Extract features from RDL file
- [RDL Schema Reference](https://docs.microsoft.com/sql/reporting-services/report-definition-language-ssrs)

### Architecture Compliance Checklist

- [x] Services follow single responsibility principle
- [x] Pydantic v2 models use proper type hints
- [x] Custom exceptions inherit from base exception class
- [x] Unit tests cover all extraction scenarios (32 tests)
- [x] Features stored as JSON for flexibility

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created comprehensive RDL parser with lxml for XML parsing
- Supports RDL namespace versions: 2005, 2008, 2010, 2016
- Extracts datasets with query type detection (embedded SQL, stored procedure, shared dataset)
- Extracts visual elements with grouping analysis (Tablix, Chart, Gauge, Map, Subreport, etc.)
- Categorizes expressions: field references, aggregates, running values, lookups, custom code calls
- Parses VB.NET custom code blocks and extracts function definitions
- Extracts layout features including page dimensions, margins, orientation
- Implements RDLParseError with line/column info for debugging
- Updated analysis_service.py to use new parser with backward-compatible legacy dict
- Added new scoring penalties for running values, lookups, maps, and gauges
- Created 32 comprehensive unit tests covering all extraction scenarios

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Add lxml to requirements | backend/requirements.txt |
| 2026-01-22 | Create AnalysisFeatures Pydantic schemas | backend/app/schemas/analysis.py |
| 2026-01-22 | Create comprehensive RDL parser | backend/app/services/rdl_parser.py |
| 2026-01-22 | Update analysis_service to use new parser | backend/app/services/analysis_service.py |
| 2026-01-22 | Add RDL parser unit tests | backend/tests/test_rdl_parser.py |

### File List

**Backend:**
- app/schemas/analysis.py (new) - Pydantic models for analysis features
- app/services/rdl_parser.py (new) - Comprehensive RDL parser with lxml
- app/services/analysis_service.py (modified) - Updated to use new parser
- requirements.txt (modified) - Added lxml>=5.0.0
- tests/test_rdl_parser.py (new) - 32 unit tests for parser

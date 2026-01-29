# Story 4.5: TODO List Generation

Status: done

## Story

As a **user**,
I want **a clear TODO list of manual work items for a report**,
So that **I know exactly what needs my attention after conversion**.

## Acceptance Criteria

### AC1: Generate TODO Items for Complexity Items
**Given** analysis has identified complexity items
**When** generating the TODO list
**Then** items are created for each:
  - Stored procedure requiring conversion
  - Expression requiring manual attention
  - Subreport requiring separate handling
  - Custom VB code function
  - Unsupported visual element

### AC2: TODO Item Structure
**Given** a TODO item is generated
**When** viewing the item
**Then** it includes:
  - Title (clear, actionable statement)
  - Category (SP, Expression, Subreport, etc.)
  - Priority (High/Medium/Low based on impact)
  - Location in report (dataset name, visual name, line number if applicable)
  - Guidance (brief suggestion for resolution)

### AC3: TODO List Sorting and Grouping
**Given** the TODO list is generated
**When** displaying items
**Then** they are sorted by priority (High first)
**And** grouped by category
**And** a count is shown: "X items requiring attention"

### AC4: Empty TODO List Handling
**Given** no complexity items are found (green report)
**When** viewing TODO list
**Then** a message shows: "No manual work items identified"
**And** the user can proceed directly to conversion

### AC5: TODO Persistence and Resolution Tracking
**Given** TODO items exist
**When** stored in the database
**Then** each item is linked to the analysis record
**And** items can be marked as "resolved" by the user (for tracking)

## Tasks / Subtasks

- [x] **Task 1: Create TODO Generator Service** (AC: 1)
  - [x] Create `backend/app/services/todo_generator.py`
  - [x] Implement `generate_todos(analysis_result: AnalysisResult) -> List[TodoItem]`
  - [x] Create TODO for each complexity item type
  - [x] Include all required metadata

- [x] **Task 2: Define TODO Item Model** (AC: 2)
  - [x] Create `TodoItem` Pydantic model with required fields
  - [x] Define `TodoCategory` enum
  - [x] Define `TodoPriority` enum
  - [x] Include resolution status field

- [x] **Task 3: Implement SP TODO Generation** (AC: 1, 2)
  - [x] Create TODO for each stored procedure
  - [x] Title: "Convert stored procedure '[SP_NAME]' to SELECT statement"
  - [x] Priority: High
  - [x] Include guidance based on SP complexity

- [x] **Task 4: Implement Expression TODO Generation** (AC: 1, 2)
  - [x] Create TODO for partial/manual expressions
  - [x] Title varies by expression type
  - [x] Priority: High for manual, Medium for partial
  - [x] Include original expression and suggested approach

- [x] **Task 5: Implement Subreport TODO Generation** (AC: 1, 2)
  - [x] Create TODO for each subreport reference
  - [x] Title: "Convert subreport '[NAME]' separately"
  - [x] Priority: Medium
  - [x] Include subreport path if available

- [x] **Task 6: Implement Custom Code TODO Generation** (AC: 1, 2)
  - [x] Create TODO for each VB function
  - [x] Title: "Convert VB function '[FUNC_NAME]' to DAX"
  - [x] Priority: High
  - [x] Include detected patterns as hints

- [x] **Task 7: Implement Unsupported Visual TODO Generation** (AC: 1, 2)
  - [x] Create TODO for maps, gauges, unsupported items
  - [x] Title: "Recreate [VISUAL_TYPE] visual '[NAME]' in Power BI"
  - [x] Priority: Medium
  - [x] Include visual type and suggested alternatives

- [x] **Task 8: Implement Priority Assignment** (AC: 2, 3)
  - [x] SP = High
  - [x] Custom Code = High
  - [x] Manual Expressions = High
  - [x] Subreports = Medium
  - [x] Partial Expressions = Medium
  - [x] Unsupported Visuals = Medium

- [x] **Task 9: Implement Guidance Templates** (AC: 2)
  - [x] Create guidance text for each TODO category
  - [x] Include actionable suggestions
  - [x] Reference relevant documentation

- [x] **Task 10: Create TODO List Database Storage** (AC: 5)
  - [x] Create `todo_items` database table
  - [x] Link to analysis record via foreign key
  - [x] Include `is_resolved` boolean field
  - [x] Create Alembic migration

- [x] **Task 11: Implement Resolution Tracking API** (AC: 5)
  - [x] Create `PATCH /api/todos/{todo_id}` endpoint
  - [x] Allow marking as resolved/unresolved
  - [x] Track resolution timestamp

- [x] **Task 12: Unit Testing** (AC: 1, 2, 3, 4, 5)
  - [x] Test TODO generation for each item type
  - [x] Test priority assignment
  - [x] Test empty TODO list scenario
  - [x] Test resolution tracking

## Dev Notes

### Technical Implementation

**TODO Item Model:**
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class TodoCategory(str, Enum):
    STORED_PROCEDURE = "stored_procedure"
    EXPRESSION = "expression"
    SUBREPORT = "subreport"
    CUSTOM_CODE = "custom_code"
    UNSUPPORTED_VISUAL = "unsupported_visual"

class TodoPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TodoItem(BaseModel):
    id: Optional[UUID] = None
    analysis_id: UUID
    title: str
    category: TodoCategory
    priority: TodoPriority
    location: str
    item_name: str
    guidance: str
    original_content: Optional[str] = None  # e.g., expression text, SP name
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None

class TodoListResponse(BaseModel):
    items: List[TodoItem]
    total_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    resolved_count: int
```

**TODO Generator Service:**
```python
from typing import List

class TodoGenerator:
    def generate_todos(
        self,
        analysis_id: UUID,
        features: AnalysisFeatures,
        code_analysis: CodeAnalysisResult
    ) -> List[TodoItem]:
        """Generate TODO items from analysis results."""
        todos = []

        # Stored procedures
        todos.extend(self._generate_sp_todos(analysis_id, code_analysis.stored_procedures))

        # Expressions requiring attention
        todos.extend(self._generate_expression_todos(analysis_id, code_analysis.expressions))

        # Subreports
        todos.extend(self._generate_subreport_todos(analysis_id, features.visuals))

        # Custom VB code
        todos.extend(self._generate_custom_code_todos(analysis_id, code_analysis.vb_functions))

        # Unsupported visuals
        todos.extend(self._generate_visual_todos(analysis_id, features.visuals))

        # Sort by priority
        priority_order = {TodoPriority.HIGH: 0, TodoPriority.MEDIUM: 1, TodoPriority.LOW: 2}
        todos.sort(key=lambda t: (priority_order[t.priority], t.category.value))

        return todos

    def _generate_sp_todos(self, analysis_id: UUID, sps: List[StoredProcedureSchema]) -> List[TodoItem]:
        """Generate TODOs for stored procedures."""
        todos = []
        for sp in sps:
            guidance = self._get_sp_guidance(sp.complexity)
            todos.append(TodoItem(
                analysis_id=analysis_id,
                title=f"Convert stored procedure '{sp.name}' to SELECT statement",
                category=TodoCategory.STORED_PROCEDURE,
                priority=TodoPriority.HIGH,
                location=f"Datasets: {', '.join(sp.datasets_using)}",
                item_name=sp.name,
                guidance=guidance,
                original_content=f"Parameters: {', '.join(sp.parameters)}" if sp.parameters else "No parameters"
            ))
        return todos

    def _generate_expression_todos(self, analysis_id: UUID, expressions: List[ExpressionSchema]) -> List[TodoItem]:
        """Generate TODOs for expressions requiring attention."""
        todos = []
        for expr in expressions:
            if expr.category == ExpressionConversionCategory.AUTO:
                continue  # Skip auto-convertible

            priority = TodoPriority.HIGH if expr.category == ExpressionConversionCategory.MANUAL else TodoPriority.MEDIUM
            title = self._get_expression_title(expr)
            guidance = self._get_expression_guidance(expr)

            todos.append(TodoItem(
                analysis_id=analysis_id,
                title=title,
                category=TodoCategory.EXPRESSION,
                priority=priority,
                location=expr.location,
                item_name=expr.item_name,
                guidance=guidance,
                original_content=expr.expression
            ))
        return todos

    def _generate_subreport_todos(self, analysis_id: UUID, visuals: List[VisualFeature]) -> List[TodoItem]:
        """Generate TODOs for subreports."""
        todos = []
        for visual in visuals:
            if visual.type != VisualType.SUBREPORT:
                continue

            todos.append(TodoItem(
                analysis_id=analysis_id,
                title=f"Convert subreport '{visual.name}' separately",
                category=TodoCategory.SUBREPORT,
                priority=TodoPriority.MEDIUM,
                location=f"Embedded in parent report",
                item_name=visual.name,
                guidance=SUBREPORT_GUIDANCE
            ))
        return todos

    def _generate_custom_code_todos(self, analysis_id: UUID, functions: List[VBFunctionSchema]) -> List[TodoItem]:
        """Generate TODOs for custom VB functions."""
        todos = []
        for func in functions:
            patterns_hint = f" (detected patterns: {', '.join(func.patterns_detected)})" if func.patterns_detected else ""

            todos.append(TodoItem(
                analysis_id=analysis_id,
                title=f"Convert VB function '{func.name}' to DAX measure",
                category=TodoCategory.CUSTOM_CODE,
                priority=TodoPriority.HIGH,
                location="Report custom code block",
                item_name=func.name,
                guidance=self._get_vb_guidance(func),
                original_content=f"Parameters: {', '.join(func.parameters)}, Lines: {func.line_count}{patterns_hint}"
            ))
        return todos

    def _generate_visual_todos(self, analysis_id: UUID, visuals: List[VisualFeature]) -> List[TodoItem]:
        """Generate TODOs for unsupported visuals."""
        todos = []
        unsupported_types = {VisualType.MAP, VisualType.GAUGE}

        for visual in visuals:
            if visual.type not in unsupported_types:
                continue

            guidance = VISUAL_GUIDANCE.get(visual.type, "Recreate this visual manually in Power BI.")

            todos.append(TodoItem(
                analysis_id=analysis_id,
                title=f"Recreate {visual.type.value} visual '{visual.name}' in Power BI",
                category=TodoCategory.UNSUPPORTED_VISUAL,
                priority=TodoPriority.MEDIUM,
                location=f"Report body",
                item_name=visual.name,
                guidance=guidance
            ))
        return todos
```

**Guidance Templates:**
```python
# Stored Procedure Guidance
SP_GUIDANCE = {
    SPComplexity.SIMPLE: """
This stored procedure appears simple with few parameters. Steps to convert:
1. Identify the core SELECT statement within the SP
2. Replace parameter references with Snowflake session variables
3. Update SQL Server-specific functions to Snowflake equivalents
4. Test the resulting query against sample data
""",
    SPComplexity.MODERATE: """
This stored procedure has moderate complexity. Consider:
1. Extract the main SELECT statement(s)
2. If multiple SELECTs exist, consider UNION or CTEs
3. Convert any temp table logic to CTEs
4. Replace parameters with session variables
5. Thoroughly test with edge cases
""",
    SPComplexity.COMPLEX: """
This stored procedure has complex logic requiring careful analysis:
1. Document the business logic and expected outputs
2. Consider breaking into multiple queries if needed
3. Cursors must be replaced with set-based operations
4. Dynamic SQL needs manual rewriting
5. Consider using AI-assisted conversion for better results
6. Extensive testing is required after conversion
"""
}

# Expression Guidance
EXPRESSION_GUIDANCE = {
    'lookup': """
Lookup expressions need conversion to DAX RELATED or LOOKUPVALUE:
- If data is in the same model: Use RELATED([Column])
- If cross-table lookup: Use LOOKUPVALUE([ResultColumn], [SearchColumn], [SearchValue])
- Ensure proper relationships exist between tables
""",
    'running_value': """
RunningValue requires Power BI window functions (DAX):
- Consider WINDOW functions in Power BI (2023+)
- Alternative: Create a calculated column with EARLIER()
- For cumulative sums: Use CALCULATE with FILTER(ALL())
""",
    'custom_code': """
Custom VB code must be rewritten as DAX measures:
1. Identify what the function calculates
2. Create a new DAX measure with equivalent logic
3. DAX does not support procedural code - restructure as calculations
4. Test with known inputs/outputs from SSRS
""",
}

# Subreport Guidance
SUBREPORT_GUIDANCE = """
Subreports must be converted separately:
1. Locate and analyze the subreport RDL file
2. Convert subreport independently using this tool
3. In Power BI, consider:
   - Embedding as a separate page with drill-through
   - Using bookmarks for navigation
   - Creating a paginated report if exact layout needed
"""

# Visual Guidance
VISUAL_GUIDANCE = {
    VisualType.MAP: """
SSRS Map visuals are not directly supported in Power BI Desktop:
- Use Power BI's built-in Map or Filled Map visuals
- Consider Azure Maps visual for advanced scenarios
- Data may need geocoding (latitude/longitude)
- Shape maps require TopoJSON files for custom regions
""",
    VisualType.GAUGE: """
SSRS Gauge visuals require recreation in Power BI:
- Use Power BI's Gauge visual for single-value KPIs
- Consider KPI visual for target comparisons
- Card visuals work well for simple metrics
- Custom visuals available in AppSource for advanced gauges
"""
}
```

**Database Model:**
```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class TodoItem(Base):
    __tablename__ = "todo_items"

    id = Column(UUID, primary_key=True, default=uuid4)
    analysis_id = Column(UUID, ForeignKey("analyses.id"), nullable=False)
    title = Column(String, nullable=False)
    category = Column(Enum(TodoCategory), nullable=False)
    priority = Column(Enum(TodoPriority), nullable=False)
    location = Column(String)
    item_name = Column(String)
    guidance = Column(String)
    original_content = Column(String)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID, ForeignKey("users.id"))
```

### Priority Assignment Rules

| Item Type | Priority | Rationale |
|-----------|----------|-----------|
| Stored Procedure | High | Core data source, blocks conversion |
| Custom VB Code | High | Report may fail without DAX equivalent |
| Manual Expression | High | Calculation errors if not converted |
| Subreport | Medium | Can convert main report first |
| Partial Expression | Medium | May work with minor adjustments |
| Unsupported Visual | Medium | Report works, visual needs recreation |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analyses/{id}/todos` | Get TODO list for analysis |
| PATCH | `/api/todos/{id}` | Update TODO (mark resolved) |
| GET | `/api/todos/{id}` | Get single TODO item |

### File Structure

```
backend/app/
  services/
    todo_generator.py    # TODO generation logic
  models/
    todo.py              # Database model
  schemas/
    todo.py              # Pydantic schemas
  api/routes/
    todos.py             # API endpoints
```

### Dependencies

- Story 4.3 (Classification) - Provides analysis results
- Story 4.4 (SP/Expression Analysis) - Provides code analysis

### References

- [Source: epics.md#Story 4.5] - Original story definition
- [Source: prd.md#FR16] - Generate TODO list requirement

### Architecture Compliance Checklist

- [x] TODO items have unique IDs for resolution tracking
- [x] Guidance text is templated and consistent
- [x] Priority assignment follows defined rules
- [x] Database model supports soft resolution (is_resolved)
- [x] API follows REST patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes List

- Created comprehensive TodoGenerator service with guidance templates for each category
- TodoItem schemas support both UUID (during generation) and int (from database)
- Guidance templates include detailed conversion steps for SPs, expressions, VB code, and visuals
- VB pattern hints are included in custom code TODOs based on detected patterns
- Database model uses SQLAlchemy with proper foreign key relationships
- API endpoints follow REST patterns with PATCH for updates, POST for quick actions
- Priority sorting ensures High items appear first, then Medium, then Low
- 21 unit tests covering all TODO generation scenarios

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created TODO schemas | `app/schemas/todo.py` |
| 2026-01-22 | Created TODO generator service | `app/services/todo_generator.py` |
| 2026-01-22 | Created TODO database model | `app/models/todo.py` |
| 2026-01-22 | Created database migration | `alembic/versions/004_add_todo_items_table.py` |
| 2026-01-22 | Created TODO API routes | `app/api/routes/todos.py` |
| 2026-01-22 | Added 21 unit tests | `tests/test_todo_generator.py` |

### File List

- `backend/app/schemas/todo.py` - Pydantic schemas (TodoCategory, TodoPriority, TodoItem, TodoListResponse, etc.)
- `backend/app/services/todo_generator.py` - TodoGenerator class with guidance templates
- `backend/app/models/todo.py` - SQLAlchemy TodoItem model
- `backend/alembic/versions/004_add_todo_items_table.py` - Database migration
- `backend/app/api/routes/todos.py` - REST API endpoints for TODO management
- `backend/tests/test_todo_generator.py` - 21 unit tests for TODO generation

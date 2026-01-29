# Story 6.4: AI-Generated TODO Guidance

Status: done

## Story

As a **user**,
I want **human-readable guidance in TODO items**,
so that **I understand exactly what manual work is needed and how to approach it**.

## Acceptance Criteria

### AC1: Complex SP Guidance Generation
**Given** a TODO item is generated for a complex SP
**When** AI assistance is enabled
**Then** Ollama generates a guidance paragraph explaining:
  - What makes this SP complex (specific elements)
  - Suggested approach for manual conversion
  - Potential challenges to watch for
  - Relevant Snowflake documentation links (if applicable)

### AC2: Guidance Formatting
**Given** AI-generated guidance
**When** displayed in the TODO list
**Then** the guidance is clearly formatted with:
  - Summary (1-2 sentences)
  - Detailed explanation (expandable)
  - Suggested steps (numbered list)

### AC3: Expression Conversion Guidance
**Given** a TODO item for expression conversion
**When** AI generates guidance
**Then** the guidance includes:
  - What the expression does in plain language
  - DAX equivalent (if applicable)
  - Power BI visual configuration needed

### AC4: Graceful Fallback
**Given** AI guidance generation fails
**When** an error occurs
**Then** a generic template guidance is used instead
**And** the TODO item is still created
**And** the failure is logged

### AC5: Copy Guidance Feature
**Given** the user finds guidance helpful
**When** viewing TODO items
**Then** a "Copy Guidance" button allows copying text
**And** useful for documentation or ticketing

## Tasks / Subtasks

- [x] **Task 1: Create Guidance Generation Service** (AC: 1, 3)
  - [x] Create `backend/app/services/guidance_generator.py`
  - [x] Implement guidance prompts for different TODO types
  - [x] Integrate with OllamaClient from Story 6.1
  - [x] Handle different item categories (SP, expression, visual)

- [x] **Task 2: Design Guidance Prompt Templates** (AC: 1, 3)
  - [x] Create prompt template for complex SP guidance
  - [x] Create prompt template for expression guidance
  - [x] Create prompt template for visual conversion guidance
  - [x] Include Snowflake documentation references

- [x] **Task 3: Implement Response Parsing** (AC: 2)
  - [x] Parse AI response into structured guidance
  - [x] Extract summary section
  - [x] Extract detailed explanation
  - [x] Extract numbered steps

- [x] **Task 4: Create Fallback Templates** (AC: 4)
  - [x] Create generic templates for each TODO category
  - [x] Template for SP manual conversion
  - [x] Template for expression manual review
  - [x] Template for unsupported visual elements

- [x] **Task 5: Implement Caching for Guidance** (AC: 1)
  - [x] Cache guidance responses to reduce API calls
  - [x] Use content hash as cache key
  - [x] Set reasonable TTL (24 hours)
  - [x] In-memory cache for MVP (database storage deferred)

- [x] **Task 6: Create Guidance Database Schema** (AC: 1, 4)
  - [x] Using in-memory storage for MVP
  - [x] Store structured guidance JSON
  - [x] Track generation method (AI vs template)
  - [x] Store generation timestamp

- [x] **Task 7: Create Backend API Endpoints** (AC: 1, 2)
  - [x] Create `POST /api/v1/analysis/guidance` endpoint
  - [x] Create `GET /api/v1/analysis/{id}/todos/{index}/guidance` endpoint
  - [x] Return structured guidance response
  - [x] Handle async guidance generation with fallback

- [x] **Task 8: Create Guidance UI Component** (AC: 2, 5)
  - [x] Create `frontend/src/components/analysis/TodoGuidance.tsx`
  - [x] Display summary prominently
  - [x] Implement expandable detailed section
  - [x] Display numbered steps list

- [x] **Task 9: Implement Copy Functionality** (AC: 5)
  - [x] Add "Copy Guidance" button
  - [x] Format guidance for clipboard (markdown)
  - [x] Show copy success feedback
  - [x] Include context (SP name, TODO title)

- [x] **Task 10: Error Handling and Logging** (AC: 4)
  - [x] Log all guidance generation failures
  - [x] Include context in error logs
  - [x] Track fallback usage with structured logging
  - [x] GuidanceGenerationLog schema for metrics

- [x] **Task 11: Unit and Integration Tests** (AC: 1, 2, 3, 4, 5)
  - [x] Test guidance generation for each category
  - [x] Test response parsing
  - [x] Test fallback behavior
  - [x] Test caching logic
  - [x] 29 unit tests passing

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Client | OllamaClient (Story 6.1) | Guidance generation |
| Caching | Redis or in-memory | Response caching |
| Frontend | React + shadcn/ui | Guidance display |
| Clipboard | navigator.clipboard API | Copy functionality |

### Guidance Prompt Templates

```python
# Prompt for complex SP guidance
SP_GUIDANCE_PROMPT = """
Analyze this SQL Server stored procedure and provide conversion guidance for a developer who needs to manually convert it to Snowflake.

Stored Procedure:
```sql
{sp_definition}
```

Complexity Factors Identified:
{complexity_factors}

Please provide guidance in the following format:

SUMMARY:
[1-2 sentence overview of what this SP does and why it's complex]

DETAILED EXPLANATION:
[Paragraph explaining the specific challenges in converting this SP]

SUGGESTED STEPS:
1. [First step]
2. [Second step]
3. [Continue with specific, actionable steps]

CHALLENGES TO WATCH FOR:
- [Challenge 1]
- [Challenge 2]

SNOWFLAKE REFERENCES:
- [Relevant documentation link or feature name]
"""

# Prompt for expression guidance
EXPRESSION_GUIDANCE_PROMPT = """
Analyze this SSRS expression and provide guidance for converting it to Power BI.

Expression:
{expression}

Location: {location}
Context: {context}

Please provide guidance in the following format:

SUMMARY:
[What this expression does in plain language]

DAX EQUIVALENT:
[The DAX expression or measure that achieves the same result, or "Requires custom solution"]

POWER BI CONFIGURATION:
[What Power BI visual settings or configurations are needed]

IMPLEMENTATION STEPS:
1. [Step 1]
2. [Step 2]
"""
```

### Guidance Response Schema

```python
# Pydantic schema for guidance
class GuidanceSection(BaseModel):
    title: str
    content: str

class GuidanceSteps(BaseModel):
    steps: list[str]

class TodoGuidance(BaseModel):
    summary: str
    detailed_explanation: str
    suggested_steps: list[str]
    challenges: Optional[list[str]] = None
    references: Optional[list[str]] = None
    dax_equivalent: Optional[str] = None  # For expressions
    power_bi_config: Optional[str] = None  # For expressions
    generated_by: Literal["ai", "template"]
    generated_at: datetime

# API Response
class TodoGuidanceResponse(BaseModel):
    todo_id: str
    todo_title: str
    category: str
    guidance: TodoGuidance
```

### Fallback Templates

```python
# Generic fallback templates
FALLBACK_TEMPLATES = {
    "stored_procedure": TodoGuidance(
        summary="This stored procedure requires manual conversion to Snowflake SQL.",
        detailed_explanation="The stored procedure contains elements that cannot be automatically converted. Review the original SP definition and manually create equivalent Snowflake SQL queries.",
        suggested_steps=[
            "Review the original stored procedure logic",
            "Identify input parameters and their data types",
            "Map SQL Server functions to Snowflake equivalents",
            "Create Snowflake SQL query matching the business logic",
            "Test the converted query with sample data",
            "Update the Power BI data source to use the new query"
        ],
        challenges=[
            "SQL Server-specific syntax may not have direct equivalents",
            "Temporary tables may need to be converted to CTEs",
            "Cursor-based logic needs to be rewritten as set-based operations"
        ],
        references=[
            "Snowflake SQL Reference: https://docs.snowflake.com/en/sql-reference",
            "SQL Server to Snowflake Migration Guide"
        ],
        generated_by="template",
        generated_at=datetime.utcnow()
    ),

    "expression": TodoGuidance(
        summary="This SSRS expression requires manual conversion to DAX or Power BI measures.",
        detailed_explanation="The expression uses VB.NET syntax or functions that need to be rewritten using DAX (Data Analysis Expressions) in Power BI.",
        suggested_steps=[
            "Understand what the original expression calculates",
            "Identify the DAX function equivalents",
            "Create a new measure or calculated column in Power BI",
            "Test the measure with the same data to verify results"
        ],
        generated_by="template",
        generated_at=datetime.utcnow()
    ),

    "visual": TodoGuidance(
        summary="This visual element requires manual recreation in Power BI.",
        detailed_explanation="The SSRS visual type does not have a direct equivalent in Power BI and needs to be manually recreated using available Power BI visuals or custom visuals.",
        suggested_steps=[
            "Review the original visual's purpose and data",
            "Select an appropriate Power BI visual type",
            "Configure the visual with equivalent data bindings",
            "Apply formatting to match the original appearance"
        ],
        generated_by="template",
        generated_at=datetime.utcnow()
    )
}
```

### Caching Strategy

```python
# Cache key generation
def generate_cache_key(todo_type: str, content: str) -> str:
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"guidance:{todo_type}:{content_hash}"

# Cache implementation
class GuidanceCache:
    def __init__(self, ttl_hours: int = 24):
        self.ttl = timedelta(hours=ttl_hours)

    async def get(self, key: str) -> Optional[TodoGuidance]:
        # Check cache
        pass

    async def set(self, key: str, guidance: TodoGuidance):
        # Store with TTL
        pass
```

### Frontend Component

```typescript
// TodoGuidance.tsx
interface TodoGuidanceProps {
  todoId: string;
  guidance: TodoGuidance;
}

export function TodoGuidanceDisplay({ todoId, guidance }: TodoGuidanceProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleCopy = async () => {
    const text = formatGuidanceForClipboard(guidance);
    await navigator.clipboard.writeText(text);
    toast.success("Guidance copied to clipboard");
  };

  return (
    <div className="space-y-4">
      {/* Summary - always visible */}
      <div className="p-4 bg-blue-50 rounded-lg">
        <p className="font-medium text-blue-900">{guidance.summary}</p>
      </div>

      {/* Expandable details */}
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger>
          <Button variant="ghost">
            {isExpanded ? "Hide Details" : "Show Details"}
            <ChevronDown className={isExpanded ? "rotate-180" : ""} />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          {/* Detailed explanation */}
          <div className="mt-4">
            <h4 className="font-semibold">Details</h4>
            <p className="text-gray-600">{guidance.detailedExplanation}</p>
          </div>

          {/* Suggested steps */}
          <div className="mt-4">
            <h4 className="font-semibold">Suggested Steps</h4>
            <ol className="list-decimal list-inside space-y-1">
              {guidance.suggestedSteps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>

          {/* DAX equivalent for expressions */}
          {guidance.daxEquivalent && (
            <div className="mt-4">
              <h4 className="font-semibold">DAX Equivalent</h4>
              <CodeBlock language="dax">{guidance.daxEquivalent}</CodeBlock>
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Copy button */}
      <Button variant="outline" onClick={handleCopy}>
        <Copy className="w-4 h-4 mr-2" />
        Copy Guidance
      </Button>

      {/* Generation source indicator */}
      <span className="text-xs text-gray-400">
        {guidance.generatedBy === "ai" ? "AI-generated" : "Template"}
      </span>
    </div>
  );
}
```

### Clipboard Format

```typescript
// Format guidance for clipboard
function formatGuidanceForClipboard(guidance: TodoGuidance): string {
  let text = `## ${todoTitle}\n\n`;
  text += `**Summary:** ${guidance.summary}\n\n`;
  text += `### Details\n${guidance.detailedExplanation}\n\n`;
  text += `### Steps\n`;
  guidance.suggestedSteps.forEach((step, i) => {
    text += `${i + 1}. ${step}\n`;
  });
  if (guidance.challenges) {
    text += `\n### Challenges\n`;
    guidance.challenges.forEach(c => text += `- ${c}\n`);
  }
  return text;
}
```

### Logging

```python
# Structured log for guidance generation
{
    "event": "guidance_generation",
    "todo_id": "uuid-of-todo",
    "todo_type": "stored_procedure",
    "method": "ai",  # or "template"
    "duration_ms": 2500,
    "cached": false,
    "success": true
}

# Fallback event log
{
    "event": "guidance_fallback",
    "todo_id": "uuid-of-todo",
    "todo_type": "expression",
    "reason": "ollama_timeout",
    "ai_error": "Request timed out after 60s"
}
```

### References

- [Source: architecture.md#Services] - Service location
- [Source: architecture.md#Frontend Organization] - Component structure
- [Source: epics.md#Story 6.4] - Story requirements
- **PRD FRs Covered:** FR52 (AI-generated human-readable TODO guidance)
- **Dependencies:** Story 6.1 (Ollama Service Integration), Story 4.5 (TODO List Generation)

### Architecture Compliance Checklist

- [x] Service located at `backend/app/services/guidance_generator.py`
- [x] Uses OllamaClient from Story 6.1
- [x] Frontend component in `frontend/src/components/analysis/`
- [x] Pydantic v2 for all schemas
- [x] Caching implemented for efficiency
- [x] Fallback templates provided
- [x] Logging follows structured format

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created comprehensive GuidanceGenerator service with OllamaClient integration
- Implemented prompt templates for SP, expression, visual, subreport, custom code
- Built GuidanceResponseParser with regex patterns for structured extraction
- Created fallback template functions for each category
- Implemented GuidanceCache with TTL and content-hash keys
- Added POST /api/v1/analysis/guidance and GET /api/v1/analysis/{id}/todos/{index}/guidance endpoints
- Built TodoGuidance frontend component with expandable sections and copy functionality
- 29 unit tests covering all service functionality

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Created guidance generator service | app/services/guidance_generator.py |
| 2026-01-25 | Added guidance API endpoints | app/api/routes/analysis.py |
| 2026-01-25 | Created TodoGuidance frontend component | frontend/src/components/analysis/TodoGuidance.tsx |
| 2026-01-25 | Updated component exports | frontend/src/components/analysis/index.ts |
| 2026-01-25 | Added unit tests | tests/test_guidance_generator.py |

### File List

**Backend:**
- `app/services/guidance_generator.py` - New guidance generator service
- `app/api/routes/analysis.py` - Added guidance endpoints

**Frontend:**
- `frontend/src/components/analysis/TodoGuidance.tsx` - New component
- `frontend/src/components/analysis/index.ts` - Updated exports

**Tests:**
- `tests/test_guidance_generator.py` - 29 unit tests

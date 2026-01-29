# Story 6.2: AI-Assisted Stored Procedure Analysis and Rewrite

Status: done

## Story

As the **system**,
I want **to use AI to analyze and rewrite complex stored procedures**,
so that **more SPs can be automatically converted to SELECT statements**.

## Acceptance Criteria

### AC1: Complex SP Detection and AI Routing
**Given** a stored procedure is classified as "Moderate" or "Complex" (from Story 5.3)
**When** AI assistance is enabled
**Then** the SP definition is sent to Ollama for analysis
**And** a structured prompt guides the AI to produce a Snowflake SELECT

### AC2: Prompt Construction
**Given** the AI prompt for SP rewriting
**When** constructing the request
**Then** the prompt includes:
  - Original SP definition (SQL Server syntax)
  - Target database (Snowflake)
  - Available tables schema (if configured)
  - Expected output format (SELECT statement + confidence + explanation)

### AC3: Response Processing and Validation
**Given** Ollama returns an AI-generated rewrite
**When** processing the response
**Then** the generated SELECT is extracted
**And** the SQL is validated for basic syntax
**And** confidence level is parsed (high/medium/low)
**And** explanation is captured for user review

### AC4: Successful Rewrite Storage
**Given** the AI-generated SELECT passes validation
**When** storing the result
**Then** the rewrite is marked as "AI-Generated"
**And** the original SP is preserved in comments
**And** a note indicates: "Review recommended before production use"

### AC5: Failed Validation Handling
**Given** the AI-generated SELECT fails validation
**When** handling the failure
**Then** the failed attempt is logged
**And** the SP is flagged for manual review
**And** the AI response is stored for debugging

### AC6: Timeout Handling
**Given** AI rewrite takes longer than timeout (60s default)
**When** the timeout occurs
**Then** the request is cancelled
**And** the SP is flagged for manual review
**And** rule-based conversion is attempted as fallback

## Tasks / Subtasks

- [ ] **Task 1: Create SP Rewriter AI Service** (AC: 1)
  - [ ] Create `backend/app/services/sp_rewriter_ai.py`
  - [ ] Implement SP complexity classification integration
  - [ ] Add logic to route Moderate/Complex SPs to AI
  - [ ] Integrate with OllamaClient from Story 6.1

- [ ] **Task 2: Implement Prompt Engineering** (AC: 2)
  - [ ] Design structured prompt template for SP conversion
  - [ ] Include few-shot examples for consistent output
  - [ ] Add dynamic schema context injection
  - [ ] Implement prompt size optimization (truncation if needed)

- [ ] **Task 3: Create Prompt Templates** (AC: 2)
  - [ ] Create `backend/app/services/prompts/sp_rewrite_prompt.py`
  - [ ] Define system prompt for SQL conversion context
  - [ ] Define user prompt template with placeholders
  - [ ] Include expected output format specification

- [ ] **Task 4: Response Parsing and Extraction** (AC: 3)
  - [ ] Implement response parser for AI output
  - [ ] Extract SQL SELECT statement from response
  - [ ] Parse confidence level from response
  - [ ] Extract explanation/reasoning text

- [ ] **Task 5: SQL Syntax Validation** (AC: 3, 5)
  - [ ] Implement basic SQL syntax validation
  - [ ] Use sqlparse for SQL parsing
  - [ ] Validate Snowflake-compatible syntax
  - [ ] Check for common SQL errors

- [ ] **Task 6: Result Storage and Tracking** (AC: 4, 5)
  - [ ] Create database schema for AI rewrite results
  - [ ] Store original SP, generated SQL, confidence, explanation
  - [ ] Mark rewrites as "AI-Generated" with metadata
  - [ ] Store failed attempts for debugging

- [ ] **Task 7: Timeout and Fallback Handling** (AC: 6)
  - [ ] Implement request cancellation on timeout
  - [ ] Trigger rule-based fallback on timeout
  - [ ] Flag SP for manual review
  - [ ] Log timeout events with context

- [ ] **Task 8: Integration with Conversion Pipeline** (AC: 1, 4)
  - [ ] Integrate AI rewriter with existing sp_rewriter.py
  - [ ] Add AI/rule-based method toggle
  - [ ] Pass AI results to SQL generator
  - [ ] Include AI metadata in conversion summary

- [ ] **Task 9: Unit and Integration Tests** (AC: 1, 2, 3, 4, 5, 6)
  - [ ] Test prompt construction with various SP types
  - [ ] Test response parsing with sample AI outputs
  - [ ] Test SQL validation logic
  - [ ] Test timeout and fallback scenarios
  - [ ] Mock Ollama responses for testing

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Client | OllamaClient (Story 6.1) | Ollama API communication |
| SQL Parsing | sqlparse | SQL syntax validation |
| Prompt Templates | Jinja2 or f-strings | Dynamic prompt generation |
| Validation | Pydantic v2 | Response schema validation |

### Prompt Template Structure

```python
# System prompt for consistent behavior
SYSTEM_PROMPT = """You are an expert SQL developer specializing in database migrations.
Your task is to convert SQL Server stored procedures to Snowflake SELECT statements.
Always provide:
1. A valid Snowflake SELECT statement
2. A confidence level (high/medium/low)
3. A brief explanation of the conversion
"""

# User prompt template
USER_PROMPT_TEMPLATE = """
Convert the following SQL Server stored procedure to a Snowflake SELECT statement.

Original Stored Procedure:
```sql
{sp_definition}
```

Target Database: Snowflake
Target Schema: {schema_name}

Available Tables:
{table_list}

Requirements:
- Convert SQL Server functions to Snowflake equivalents
- Handle parameters as session variables
- Preserve business logic

Output your response in the following format:
```sql
-- Converted SELECT statement
SELECT ...
```

Confidence: [high/medium/low]
Explanation: [Brief explanation of conversion decisions]
"""
```

### Response Parsing

```python
# Expected AI response format
"""
```sql
SELECT
    customer_id,
    customer_name,
    CURRENT_TIMESTAMP() as created_at
FROM {schema}.customers
WHERE status = 'active'
```

Confidence: high
Explanation: Simple SELECT conversion. Changed GETDATE() to CURRENT_TIMESTAMP()
for Snowflake compatibility. No complex logic requiring manual review.
"""

# Parser to extract components
class AIRewriteResponse(BaseModel):
    sql_statement: str
    confidence: Literal["high", "medium", "low"]
    explanation: str

def parse_ai_response(raw_response: str) -> AIRewriteResponse:
    # Extract SQL block
    # Extract confidence level
    # Extract explanation
    pass
```

### SQL Validation

```python
# Basic SQL validation using sqlparse
import sqlparse

def validate_sql_syntax(sql: str) -> tuple[bool, Optional[str]]:
    """
    Validate SQL syntax and return (is_valid, error_message)
    """
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "Empty SQL statement"

        # Check for SELECT statement
        stmt = parsed[0]
        if stmt.get_type() != 'SELECT':
            return False, "Not a SELECT statement"

        # Additional Snowflake-specific validation
        # ...

        return True, None
    except Exception as e:
        return False, str(e)
```

### Database Schema for AI Results

```python
# SQLAlchemy model for AI rewrite tracking
class AIRewriteResult(Base):
    __tablename__ = "ai_rewrite_results"

    id = Column(UUID, primary_key=True, default=uuid4)
    sp_name = Column(String, nullable=False)
    sp_definition = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)  # high/medium/low
    explanation = Column(Text, nullable=True)
    is_valid = Column(Boolean, default=False)
    validation_error = Column(Text, nullable=True)
    method = Column(String, default="ai")  # ai or rule-based
    ai_raw_response = Column(Text, nullable=True)  # For debugging
    created_at = Column(DateTime, default=datetime.utcnow)
    conversion_id = Column(UUID, ForeignKey("conversions.id"))
```

### Integration with SP Rewriter

```python
# In backend/app/services/sp_rewriter.py

class SPRewriter:
    def __init__(self, ollama_client: OllamaClient):
        self.ollama_client = ollama_client
        self.ai_rewriter = SPRewriterAI(ollama_client)

    async def rewrite(self, sp: StoredProcedure) -> RewriteResult:
        # Classify SP complexity
        complexity = self.classify_complexity(sp)

        if complexity == "simple":
            return self.rule_based_rewrite(sp)

        if not self.ollama_client.config.enabled:
            return self.flag_for_manual_review(sp)

        # Try AI-assisted rewrite
        try:
            return await self.ai_rewriter.rewrite(sp)
        except (OllamaUnavailable, TimeoutError):
            # Fallback to rule-based or manual
            return self.handle_ai_failure(sp, complexity)
```

### Temperature and Model Settings

```python
# Optimal settings for code generation
GENERATION_OPTIONS = {
    "temperature": 0.2,    # Low for consistent, deterministic output
    "num_predict": 2048,   # Max tokens for response
    "top_k": 40,           # Sampling parameter
    "top_p": 0.9,          # Nucleus sampling
}
```

### Error Handling

```python
# Custom exceptions for AI rewriting
class AIRewriteError(Exception):
    """Base exception for AI rewrite failures"""
    pass

class AIResponseParseError(AIRewriteError):
    """Failed to parse AI response"""
    pass

class AISQLValidationError(AIRewriteError):
    """Generated SQL failed validation"""
    pass

class AITimeoutError(AIRewriteError):
    """AI request timed out"""
    pass
```

### Logging

```python
# Structured logging for AI rewrites
{
    "event": "ai_sp_rewrite",
    "sp_name": "sp_GetCustomerOrders",
    "complexity": "moderate",
    "method": "ai",
    "confidence": "high",
    "is_valid": true,
    "duration_ms": 5200,
    "prompt_tokens": 450,
    "completion_tokens": 180
}
```

### References

- [Source: architecture.md#Services] - sp_rewriter.py location
- [Source: architecture.md#Error Response Format] - Error handling patterns
- [Source: epics.md#Story 6.2] - Story requirements
- **PRD FRs Covered:** FR22 (AI-assisted complex SP rewrite), FR50 (Send SP to Ollama), FR51 (Apply AI-generated rewrites)
- **Dependencies:** Story 6.1 (Ollama Service Integration), Story 5.3 (Rule-Based SP Rewriting)

### Architecture Compliance Checklist

- [x] Service located at `backend/app/services/sp_rewriter_ai.py`
- [x] Uses OllamaClient from Story 6.1
- [x] Pydantic v2 for response validation
- [x] Follows snake_case naming conventions
- [x] Error responses follow structured format
- [x] Logging uses structured JSON format
- [x] Integrates with existing sp_rewriter.py

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created `SPRewriterAI` class in new `sp_rewriter_ai.py` module
2. Implemented prompt engineering with SYSTEM_PROMPT and USER_PROMPT_TEMPLATE
3. Created `AIResponseParser` class for extracting SQL, confidence, and explanation
4. Implemented `SQLValidator` class using sqlparse for syntax validation
5. Created 6 Pydantic schemas: AIConfidenceLevel, AIRewriteResponse, AIRewriteAttempt, SQLValidationResult
6. Added timeout handling with asyncio.wait_for
7. Implemented fallback to placeholder when AI fails
8. Validation failure handling preserves AI output for debugging
9. Integrated with existing SPRewriter via `rewrite_with_ai` async method
10. Added enable_ai flag to SPRewriter for toggling AI assistance
11. Created 29 unit tests (all passing)
12. Total tests: 497 passed, 6 skipped

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Created SPRewriterAI service with prompt templates, parser, validator | app/services/sp_rewriter_ai.py |
| 2026-01-25 | Added AI integration to SPRewriter (rewrite_with_ai method) | app/services/sp_rewriter.py |
| 2026-01-25 | Created 29 unit tests | tests/test_sp_rewriter_ai.py |

### File List

**New Files:**
- `app/services/sp_rewriter_ai.py` - AI-assisted SP rewriter with prompt templates, response parser, SQL validator
- `tests/test_sp_rewriter_ai.py` - 29 unit tests for AI rewriter components

**Modified Files:**
- `app/services/sp_rewriter.py` - Added enable_ai flag, _get_ai_rewriter helper, rewrite_with_ai async method

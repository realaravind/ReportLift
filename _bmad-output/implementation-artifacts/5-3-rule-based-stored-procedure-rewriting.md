# Story 5.3: Rule-Based Stored Procedure Rewriting

Status: done

## Story

As the **system**,
I want **to automatically rewrite simple stored procedures as SELECT statements**,
so that **more reports can be converted without manual SP migration**.

## Acceptance Criteria

### AC1: SP Classification
**Given** a stored procedure is identified in analysis
**When** evaluating for auto-rewrite
**Then** the SP is classified as:
  - **Simple**: Single SELECT, no control flow, no temp tables, no cursors
  - **Moderate**: Multiple SELECTs with UNION, simple IF/ELSE
  - **Complex**: Temp tables, loops, cursors, dynamic SQL, transactions

### AC2: Simple SP Auto-Rewrite
**Given** a Simple stored procedure
**When** auto-rewrite is applied
**Then** the SELECT statement is extracted
**And** parameters are converted to Snowflake variables
**And** SQL Server functions are mapped to Snowflake
**And** the result is a standalone SELECT query

### AC3: Moderate SP Rewrite Attempt
**Given** a Moderate stored procedure
**When** auto-rewrite is attempted
**Then** an attempt is made to flatten UNIONs
**And** if successful, a combined SELECT is generated
**And** if unsuccessful, it is flagged for manual review

### AC4: Complex SP Handling
**Given** a Complex stored procedure
**When** auto-rewrite is evaluated
**Then** no automatic rewrite is attempted
**And** a TODO item is generated: "Manual conversion required for [SP name]"
**And** the original SP definition is included in comments if available

### AC5: Rewrite Confidence
**Given** auto-rewrite produces a query
**When** generating output
**Then** the original SP call is documented
**And** confidence level is noted (high/medium/low)
**And** suggestions for validation are included

## Tasks / Subtasks

- [ ] **Task 1: Create SP Parser Service** (AC: 1)
  - [ ] Create `backend/app/services/sp_rewriter.py`
  - [ ] Implement SP definition parsing using sqlparse
  - [ ] Detect control flow statements (IF, WHILE, BEGIN...END)
  - [ ] Detect temp tables (#table, @table variables)
  - [ ] Detect cursors (DECLARE CURSOR, OPEN, FETCH)
  - [ ] Detect dynamic SQL (EXEC, sp_executesql)
  - [ ] Detect transactions (BEGIN TRAN, COMMIT, ROLLBACK)

- [ ] **Task 2: Create SP Classifier** (AC: 1)
  - [ ] Implement `classify_stored_procedure()` method
  - [ ] Return classification: SIMPLE, MODERATE, COMPLEX
  - [ ] Return list of detected complexity elements
  - [ ] Calculate complexity score for reporting

- [ ] **Task 3: Implement Simple SP Rewriter** (AC: 2)
  - [ ] Implement `rewrite_simple_sp()` method
  - [ ] Extract SELECT statement from SP body
  - [ ] Convert SP parameters to Snowflake session variables
  - [ ] Apply SQL function mappings (from Story 5.2)
  - [ ] Generate standalone SELECT query
  - [ ] Add confidence level (HIGH for simple)

- [ ] **Task 4: Implement Moderate SP Rewriter** (AC: 3)
  - [ ] Implement `rewrite_moderate_sp()` method
  - [ ] Detect UNION/UNION ALL patterns
  - [ ] Attempt to flatten multiple SELECTs
  - [ ] Handle simple IF/ELSE by including both branches with CASE
  - [ ] Return success/failure status
  - [ ] Add confidence level (MEDIUM for moderate)

- [ ] **Task 5: Implement Complex SP Handler** (AC: 4)
  - [ ] Implement `handle_complex_sp()` method
  - [ ] Generate TODO item with SP name
  - [ ] Include original SP definition in comments
  - [ ] List specific complexity elements detected
  - [ ] Return placeholder SQL with instructions

- [ ] **Task 6: Create SP Rewrite Schemas** (AC: 1-5)
  - [ ] Create Pydantic schemas for SP classification result
  - [ ] Create schema for rewrite result (success/failure, confidence)
  - [ ] Create schema for TODO item generation

- [ ] **Task 7: Create Validation Suggestions Generator** (AC: 5)
  - [ ] Generate validation suggestions based on SP type
  - [ ] Include row count comparison suggestion
  - [ ] Include sample data comparison suggestion
  - [ ] Include performance testing suggestion

- [ ] **Task 8: Unit Tests for SP Rewriter** (AC: 1-4)
  - [ ] Create `backend/tests/test_sp_rewriter.py`
  - [ ] Test classification of simple SPs
  - [ ] Test classification of moderate SPs
  - [ ] Test classification of complex SPs
  - [ ] Test SELECT extraction
  - [ ] Test parameter conversion

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| SQL Parsing | sqlparse | AST parsing for SP analysis |
| Backend | FastAPI | Service layer |
| Testing | pytest | Unit tests |

### SP Classification Rules

**Simple SP Indicators:**
- Single SELECT statement
- No IF/ELSE/WHILE/GOTO
- No temp tables (#temp, @table)
- No cursors
- No dynamic SQL
- No transactions
- Only parameter declarations and SET statements

**Moderate SP Indicators:**
- Multiple SELECT with UNION/UNION ALL
- Simple IF/ELSE (single condition, no nesting)
- No temp tables or cursors
- No dynamic SQL

**Complex SP Indicators (any one):**
- Temp tables (#temp, @table variables)
- Cursors (DECLARE CURSOR, FETCH)
- Loops (WHILE, GOTO)
- Dynamic SQL (EXEC, sp_executesql)
- Transactions (BEGIN TRAN)
- Nested control flow
- Multiple result sets

### Example Transformations

**Simple SP (Original):**
```sql
CREATE PROCEDURE GetSalesByDate
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SELECT
        CustomerName,
        SUM(SalesAmount) as TotalSales
    FROM Sales
    WHERE SaleDate BETWEEN @StartDate AND @EndDate
    GROUP BY CustomerName
END
```

**Converted (Snowflake):**
```sql
-- Original SP: GetSalesByDate
-- Classification: SIMPLE
-- Confidence: HIGH

-- Parameter Declarations
SET start_date = :start_date; -- @StartDate
SET end_date = :end_date;     -- @EndDate

-- Converted Query
SELECT
    customer_name,
    SUM(sales_amount) AS total_sales
FROM ${database}.${schema}.sales
WHERE sale_date BETWEEN $start_date AND $end_date
GROUP BY customer_name;
```

**Complex SP Placeholder:**
```sql
-- Original SP: ComplexReportProc
-- Classification: COMPLEX
-- Confidence: N/A (Manual conversion required)

-- Detected Complexity Elements:
--   - Temp table: #TempResults
--   - Cursor: sales_cursor
--   - Dynamic SQL: EXEC sp_executesql

-- TODO: Manual conversion required for ComplexReportProc
-- Original SP definition preserved below for reference:
/*
CREATE PROCEDURE ComplexReportProc ...
*/

-- Placeholder query (replace with converted logic):
SELECT 'TODO: Implement converted query for ComplexReportProc' AS status;
```

### Confidence Levels

| Level | Criteria | User Action |
|-------|----------|-------------|
| HIGH | Simple SP, no complex elements | Can use with basic validation |
| MEDIUM | Moderate SP, flattened successfully | Requires data validation |
| LOW | Moderate SP, uncertain conversion | Requires thorough review |
| N/A | Complex SP, no auto-conversion | Full manual conversion needed |

### Validation Suggestions Template

```
Validation Recommendations:
1. Compare row counts between original SP and converted query
2. Sample 100 random rows and verify data matches
3. Test with edge case parameters (null, empty, boundary values)
4. Compare execution time for performance baseline
5. Review any NULL handling differences between SQL Server and Snowflake
```

### References

- [Source: architecture.md#services/sp_rewriter.py] - SP rewriter service location
- [Source: epics.md#Story 5.3] - Story requirements
- [Source: prd.md#FR21] - Rewrite simple SP requirement

### PRD FRs Covered

- **FR21**: System rewrites simple stored procedures as SELECT statements (rule-based)

### Architecture Compliance Checklist

- [x] Service uses sqlparse for SQL parsing
- [x] Classification returns structured result
- [x] Confidence levels included in output
- [x] Complex SPs generate TODO items
- [x] Original SP preserved in comments
- [x] Unit tests cover all classification cases

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created comprehensive SPParser class for detecting complexity elements (temp tables, cursors, dynamic SQL, transactions, loops)
2. Created SPClassifier for classifying SPs as SIMPLE, MODERATE, or COMPLEX
3. Implemented Simple SP Rewriter with SELECT extraction and parameter conversion
4. Implemented Moderate SP Rewriter for UNION queries and simple IF/ELSE patterns
5. Implemented Complex SP Handler with TODO placeholders and original SP preservation
6. Created validation suggestions generator with confidence-based recommendations
7. Integrated with converter service for automatic SP processing during conversion
8. Added 45 unit tests covering all classification cases and rewrite scenarios
9. Uses SQLGenerator from Story 5-2 for SQL Server to Snowflake function conversion

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created SP rewriter service | app/services/sp_rewriter.py |
| 2026-01-22 | Integrated with converter service | app/services/converter.py |
| 2026-01-22 | Created unit tests | tests/test_sp_rewriter.py |

### File List

**New Files:**
- `app/services/sp_rewriter.py` - SP Parser, Classifier, and Rewriter service with complexity detection and conversion
- `tests/test_sp_rewriter.py` - 45 unit tests for SP rewriting

**Modified Files:**
- `app/services/converter.py` - Updated _rewrite_stored_procedures to use SPRewriter service

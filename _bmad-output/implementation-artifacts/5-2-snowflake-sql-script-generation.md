# Story 5.2: Snowflake SQL Script Generation

Status: done

## Story

As a **user**,
I want **SQL scripts generated for Snowflake**,
so that **report data sources work on our target database platform**.

## Acceptance Criteria

### AC1: Embedded SQL Conversion
**Given** a report has datasets with embedded SQL queries
**When** generating SQL scripts
**Then** each query is converted to Snowflake-compatible syntax
**And** SQL Server-specific functions are mapped to Snowflake equivalents
**And** CONVERT/CAST syntax is updated for Snowflake

### AC2: Schema Configuration
**Given** the Snowflake connection is configured
**When** generating SQL scripts
**Then** the configured schema is used in table references
**And** database.schema.table naming convention is applied
**And** warehouse context is included in script comments

### AC3: Simple SP Auto-Conversion
**Given** a dataset references a stored procedure
**When** that SP can be auto-converted (simple SELECT wrapper)
**Then** a corresponding SELECT statement is generated
**And** the original SP reference is noted in comments

### AC4: Complex SP Placeholder
**Given** a dataset references a stored procedure
**When** that SP cannot be auto-converted (complex logic)
**Then** a placeholder script is generated with TODO comments
**And** the original SP call is preserved in comments

### AC5: Parameter Conversion
**Given** parameters are used in queries
**When** generating SQL scripts
**Then** parameters are converted to Snowflake session variables format
**And** a parameter declaration section is included
**And** default values from RDL are preserved

### AC6: Output File Generation
**Given** SQL generation completes
**When** scripts are produced
**Then** each dataset gets a separate .sql file
**And** a combined "all_scripts.sql" is also generated
**And** scripts are formatted for readability

## Tasks / Subtasks

- [ ] **Task 1: Create SQL Dialect Converter** (AC: 1)
  - [ ] Create `backend/app/services/sql_generator.py`
  - [ ] Implement SQL Server to Snowflake function mapping
  - [ ] Map GETDATE() to CURRENT_TIMESTAMP()
  - [ ] Map ISNULL() to COALESCE()
  - [ ] Map TOP N to LIMIT N
  - [ ] Map CONVERT/CAST to Snowflake syntax
  - [ ] Handle date function conversions (DATEADD, DATEDIFF, etc.)
  - [ ] Handle string function conversions (CHARINDEX, STUFF, etc.)

- [ ] **Task 2: Create Schema Mapping Service** (AC: 2)
  - [ ] Add method to read Snowflake configuration
  - [ ] Implement table reference rewriting (database.schema.table)
  - [ ] Generate warehouse context header comments
  - [ ] Handle missing schema configuration (use placeholders)

- [ ] **Task 3: Create Parameter Converter** (AC: 5)
  - [ ] Implement RDL parameter extraction
  - [ ] Convert parameters to Snowflake session variables
  - [ ] Generate SET statements for parameter declarations
  - [ ] Preserve default values from RDL
  - [ ] Handle different parameter types

- [ ] **Task 4: Integrate with SP Rewriter** (AC: 3, 4)
  - [ ] Connect to Story 5.3's sp_rewriter service
  - [ ] Determine if SP is simple (auto-convertible) or complex
  - [ ] For simple SPs: extract and convert SELECT statement
  - [ ] For complex SPs: generate TODO placeholder
  - [ ] Include original SP details in comments

- [ ] **Task 5: Create Output File Generator** (AC: 6)
  - [ ] Create individual .sql files per dataset
  - [ ] Create combined all_scripts.sql file
  - [ ] Apply SQL formatting for readability
  - [ ] Add header comments with generation metadata
  - [ ] Store files in conversion storage directory

- [ ] **Task 6: Create SQL Generation Pydantic Schemas** (AC: 1-6)
  - [ ] Add SQLScriptOutput schema
  - [ ] Add SQLGenerationResult schema
  - [ ] Add FunctionMapping schema for tracking conversions

- [ ] **Task 7: Unit Tests for SQL Conversion** (AC: 1, 5)
  - [ ] Create `backend/tests/test_sql_generator.py`
  - [ ] Test common function mappings
  - [ ] Test parameter conversion
  - [ ] Test edge cases (nested functions, complex expressions)

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| SQL Parsing | sqlparse | Parse and format SQL |
| Backend | FastAPI | Service layer |
| Testing | pytest | Unit tests for conversions |

### SQL Server to Snowflake Function Mapping

| SQL Server | Snowflake | Notes |
|------------|-----------|-------|
| GETDATE() | CURRENT_TIMESTAMP() | |
| ISNULL(a, b) | COALESCE(a, b) | |
| TOP N | LIMIT N | Move to end of query |
| CONVERT(type, value) | CAST(value AS type) | Type mapping needed |
| DATEADD(part, n, date) | DATEADD(part, n, date) | Same syntax |
| DATEDIFF(part, d1, d2) | DATEDIFF(part, d1, d2) | Same syntax |
| CHARINDEX(s, str) | POSITION(s IN str) | |
| LEN(s) | LENGTH(s) | |
| SUBSTRING(s, start, len) | SUBSTR(s, start, len) | |
| STUFF(s, start, len, rep) | INSERT(s, start, len, rep) | Different name |
| CAST(x AS VARCHAR(n)) | CAST(x AS VARCHAR(n)) | Same |
| + (string concat) | \|\| | String concatenation |

### Parameter Conversion Pattern

**Original (RDL Parameter):**
```xml
<ReportParameter Name="StartDate">
  <DataType>DateTime</DataType>
  <DefaultValue>
    <Values><Value>=Today()</Value></Values>
  </DefaultValue>
</ReportParameter>
```

**Generated Snowflake:**
```sql
-- Parameter Declarations
SET start_date = CURRENT_DATE(); -- Default from RDL: Today()

-- Query with parameters
SELECT * FROM sales WHERE sale_date >= $start_date;
```

### Output File Structure

```sql
-- ============================================
-- ReportLift SQL Script
-- Generated: 2026-01-21T10:30:00Z
-- Report: Sales Summary Report
-- Dataset: SalesData
-- Target: Snowflake
-- Warehouse: ANALYTICS_WH
-- Database: REPORTING
-- Schema: PUBLIC
-- ============================================

-- Original Query Type: Embedded SQL
-- Conversion Notes: 3 functions mapped

-- Parameter Declarations
SET @start_date = CURRENT_DATE();
SET @end_date = CURRENT_DATE();

-- Converted Query
SELECT
    customer_name,
    COALESCE(sales_amount, 0) AS sales_amount,
    sale_date
FROM REPORTING.PUBLIC.sales
WHERE sale_date BETWEEN $start_date AND $end_date
LIMIT 1000;
```

### Error Handling

- If function cannot be mapped, add TODO comment and preserve original
- If schema not configured, use placeholder: `{DATABASE}.{SCHEMA}.table`
- Log all unmapped functions for review

### References

- [Source: architecture.md#services/sql_generator.py] - SQL generator service
- [Source: epics.md#Story 5.2] - Story requirements
- [Source: prd.md#FR20] - Generate Snowflake SQL scripts requirement

### PRD FRs Covered

- **FR20**: System generates Snowflake SQL scripts for report data sources

### Architecture Compliance Checklist

- [ ] Service follows snake_case naming for Python
- [ ] SQL files properly formatted and commented
- [ ] Error handling uses structured logging
- [ ] Unmapped functions flagged with TODO comments
- [ ] Unit tests cover common conversion scenarios

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created comprehensive SQLGenerator class with SQL Server to Snowflake function mappings
2. Implemented 25+ function conversions (GETDATE, ISNULL, LEN, SUBSTRING, CONVERT, etc.)
3. Implemented TOP N to LIMIT N conversion
4. Implemented string concatenation conversion (+ to ||)
5. Created schema qualification service (database.schema.table naming)
6. Created parameter converter for RDL parameters to Snowflake session variables
7. Created output file generator with individual .sql files and combined all_scripts.sql
8. Integrated with converter service (Story 5-1) for use during conversion
9. Created placeholder generator for stored procedures (to be converted in Story 5-3)
10. Added 42 unit tests covering all conversion scenarios
11. Fixed regex patterns to avoid catastrophic backtracking

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created SQL generator service | app/services/sql_generator.py |
| 2026-01-22 | Added sqlparse dependency | requirements.txt |
| 2026-01-22 | Integrated with converter service | app/services/converter.py |
| 2026-01-22 | Created unit tests | tests/test_sql_generator.py |

### File List

**New Files:**
- `app/services/sql_generator.py` - SQL Generator service with function mappings, schema qualification, and output generation
- `tests/test_sql_generator.py` - 42 unit tests for SQL conversion

**Modified Files:**
- `requirements.txt` - Added sqlparse dependency
- `app/services/converter.py` - Updated _generate_sql_scripts to use SQLGenerator

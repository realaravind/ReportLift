# Story 5.1: Initiate Report Conversion

Status: done

## Story

As a **user**,
I want **to initiate conversion of an analyzed report**,
so that **I can generate Power BI and SQL outputs**.

## Acceptance Criteria

### AC1: Conversion Initiation
**Given** a report has been analyzed
**When** the user clicks "Convert Report"
**Then** conversion begins with a progress indicator
**And** the UI shows current step: "Generating SQL...", "Building Power BI...", etc.
**And** the user can cancel conversion (partial files are discarded)

### AC2: Snowflake Not Configured Warning
**Given** conversion is initiated
**When** Snowflake is not configured
**Then** the user is warned: "Snowflake not configured - SQL scripts will use placeholder schema"
**And** the user can proceed or cancel to configure Snowflake first

### AC3: Conversion Progress UI
**Given** conversion is in progress
**When** viewing the UI
**Then** estimated time remaining is not shown (per guidelines)
**And** a progress bar or spinner indicates activity
**And** navigation away shows a confirmation dialog

### AC4: Successful Conversion
**Given** conversion completes successfully
**When** all outputs are ready
**Then** the view transitions to the Conversion Summary
**And** all output files are stored for download
**And** the conversion is logged for audit (Epic 7)

### AC5: Failed Conversion
**Given** conversion fails
**When** an error occurs
**Then** partial outputs are discarded (NFR15 - complete or nothing)
**And** an error message explains the failure
**And** the user can view the analysis and retry

## Tasks / Subtasks

- [ ] **Task 1: Create Conversion Database Model** (AC: 4, 5)
  - [ ] Create `backend/app/models/conversion_job.py` model
  - [ ] Add fields: id, report_id, analysis_id, status, started_at, completed_at, error_message
  - [ ] Add relationship to analysis_result model
  - [ ] Create Alembic migration for conversion_jobs table
  - [ ] Add status enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED

- [ ] **Task 2: Create Conversion Pydantic Schemas** (AC: 1, 4, 5)
  - [ ] Create `backend/app/schemas/conversion.py`
  - [ ] Create ConversionJobCreate schema
  - [ ] Create ConversionJobResponse schema with status
  - [ ] Create ConversionProgressResponse schema
  - [ ] Create ConversionErrorResponse schema

- [ ] **Task 3: Create Conversion Service** (AC: 1, 4, 5)
  - [ ] Create `backend/app/services/converter.py`
  - [ ] Implement `initiate_conversion()` method
  - [ ] Implement conversion orchestration (calls sql_generator, pbix_builder)
  - [ ] Implement atomic file handling (all-or-nothing)
  - [ ] Implement cleanup on failure (discard partial files)
  - [ ] Add progress tracking with step indicators

- [ ] **Task 4: Create Conversion API Endpoints** (AC: 1, 2, 4, 5)
  - [ ] Create `backend/app/api/routes/conversion.py`
  - [ ] Add `POST /api/v1/reports/{report_id}/convert` endpoint
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/status` endpoint
  - [ ] Add `DELETE /api/v1/conversions/{conversion_id}` for cancellation
  - [ ] Add Snowflake configuration check before conversion
  - [ ] Register routes in main.py

- [ ] **Task 5: Create Frontend Conversion Hook** (AC: 1, 2, 3)
  - [ ] Create `frontend/src/hooks/useConversion.ts`
  - [ ] Implement mutation for initiating conversion
  - [ ] Implement polling for conversion status
  - [ ] Handle cancellation
  - [ ] Handle Snowflake warning dialog

- [ ] **Task 6: Create Conversion UI Components** (AC: 1, 2, 3)
  - [ ] Create `frontend/src/components/conversion/ConvertButton.tsx`
  - [ ] Create `frontend/src/components/conversion/ConversionProgress.tsx`
  - [ ] Create progress step indicators UI
  - [ ] Create cancellation confirmation dialog
  - [ ] Create Snowflake warning dialog
  - [ ] Add navigation guard for in-progress conversion

- [ ] **Task 7: Integrate Audit Logging** (AC: 4)
  - [ ] Log conversion initiation event
  - [ ] Log conversion success event
  - [ ] Log conversion failure event
  - [ ] Include report details in audit log

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | API endpoints for conversion |
| Database | SQLAlchemy | Conversion job persistence |
| Background Tasks | FastAPI BackgroundTasks | Async conversion processing |
| Frontend | React Query | Mutation and polling |
| UI | shadcn/ui | Progress indicators, dialogs |

### API Endpoints

**POST /api/v1/reports/{report_id}/convert**
```json
Request: {}
Response: {
  "data": {
    "conversion_id": "uuid",
    "status": "in_progress",
    "started_at": "2026-01-21T10:30:00Z"
  }
}
```

**GET /api/v1/conversions/{conversion_id}/status**
```json
Response: {
  "data": {
    "conversion_id": "uuid",
    "status": "in_progress",
    "current_step": "Generating SQL scripts",
    "steps_completed": 1,
    "total_steps": 4
  }
}
```

**DELETE /api/v1/conversions/{conversion_id}**
```json
Response: {
  "data": {
    "conversion_id": "uuid",
    "status": "cancelled"
  }
}
```

### Conversion Steps (Progress Indicators)

1. "Validating analysis data..."
2. "Generating SQL scripts..."
3. "Rewriting stored procedures..."
4. "Building Power BI report..."
5. "Applying branding template..."
6. "Finalizing outputs..."

### File Storage Pattern

```
storage/
├── conversions/
│   ├── {conversion_id}/
│   │   ├── sql/
│   │   │   ├── all_scripts.sql
│   │   │   └── datasets/
│   │   │       ├── dataset1.sql
│   │   │       └── dataset2.sql
│   │   ├── pbix/
│   │   │   └── {report_name}_converted.pbix
│   │   └── metadata.json
```

### Error Handling

- Use atomic operations for file creation
- On any failure, delete all partial outputs
- Store error details in conversion_job record
- Return structured error response to frontend

### NFR Compliance

- **NFR15**: Conversion outputs complete or not generated (atomic)
- All partial files must be cleaned up on failure
- Use database transaction for conversion record

### References

- [Source: architecture.md#services/converter.py] - Converter service location
- [Source: architecture.md#API Patterns] - Response format patterns
- [Source: epics.md#Story 5.1] - Story requirements
- [Source: prd.md#FR18] - Initiate conversion requirement
- [Source: prd.md#NFR15] - Complete or nothing requirement

### PRD FRs Covered

- **FR18**: User can initiate conversion of an analyzed report

### Architecture Compliance Checklist

- [ ] Conversion job stored in SQL Server database
- [ ] API follows REST conventions with snake_case JSON
- [ ] Error responses use `{ error: { code, message, details } }` format
- [ ] Background task used for long-running conversion
- [ ] Audit logging integrated for compliance

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created ConversionJob SQLAlchemy model with status tracking, progress, and output file management
2. Created Alembic migration for conversion_jobs table with proper indexes
3. Created comprehensive Pydantic schemas for all conversion operations
4. Created converter service with 6-step orchestration (stubs for steps implemented in later stories)
5. Created REST API endpoints for conversion initiation, status polling, cancellation, and results
6. Created React Query hooks for frontend conversion operations with automatic polling
7. Created ConversionProgress component with step indicators
8. Created SnowflakeWarningDialog for warning when Snowflake not configured
9. Created CancelConversionDialog for cancellation confirmation
10. Created ConversionPanel that integrates all conversion UI components
11. Added navigation guard for in-progress conversions
12. Added 36 unit tests (31 passing, 5 skipped for integration tests requiring DB)
13. Task 7 (Audit Logging) deferred to Epic 7 as noted in story

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created ConversionJob model | app/models/conversion.py |
| 2026-01-22 | Created Alembic migration | alembic/versions/005_add_conversion_jobs_table.py |
| 2026-01-22 | Created Conversion schemas | app/schemas/conversion.py |
| 2026-01-22 | Created Converter service | app/services/converter.py |
| 2026-01-22 | Created Conversion API routes | app/api/routes/conversion.py |
| 2026-01-22 | Updated main.py with conversion router | app/main.py |
| 2026-01-22 | Created useConversion hook | frontend/src/hooks/useConversion.ts |
| 2026-01-22 | Created conversion UI components | frontend/src/components/conversion/*.tsx |
| 2026-01-22 | Created conversion tests | tests/test_conversion.py |

### File List

**Backend:**
- `app/models/conversion.py` - ConversionJob SQLAlchemy model
- `alembic/versions/005_add_conversion_jobs_table.py` - Database migration
- `app/schemas/conversion.py` - Pydantic schemas for conversion operations
- `app/services/converter.py` - Conversion orchestration service
- `app/api/routes/conversion.py` - REST API endpoints
- `app/main.py` - Updated to register conversion router
- `tests/test_conversion.py` - Unit tests

**Frontend:**
- `frontend/src/hooks/useConversion.ts` - React Query hooks
- `frontend/src/components/conversion/ConversionProgress.tsx` - Progress display
- `frontend/src/components/conversion/SnowflakeWarningDialog.tsx` - Snowflake warning
- `frontend/src/components/conversion/CancelConversionDialog.tsx` - Cancel confirmation
- `frontend/src/components/conversion/ConversionPanel.tsx` - Main conversion panel
- `frontend/src/components/conversion/index.ts` - Barrel export

# Story 4.1: Trigger On-Demand Report Analysis

Status: done

## Story

As a **user**,
I want **to trigger analysis of a selected report**,
So that **I can understand its conversion complexity before deciding to convert**.

## Acceptance Criteria

### AC1: Analyze Button and Initiation
**Given** a report is selected in the browser
**When** the user clicks the "Analyze" button
**Then** the system fetches the RDL file from SSRS
**And** a loading indicator shows "Analyzing report..."
**And** analysis completes within 2 seconds (NFR29)

### AC2: Loading State and Progress Indicator
**Given** analysis is in progress
**When** viewing the UI
**Then** the "Analyze" button is disabled
**And** a cancel option is available
**And** navigation away shows a confirmation dialog

### AC3: Successful Analysis Completion
**Given** analysis completes successfully
**When** results are available
**Then** the view transitions to the Analysis Results dashboard
**And** the analysis is stored in the database for future reference

### AC4: Cached Results Check
**Given** the same report is analyzed again
**When** initiating analysis
**Then** the user is prompted: "Report was analyzed on [date]. Analyze again?"
**And** selecting "Yes" runs a fresh analysis
**And** selecting "View Previous" shows the cached results

### AC5: Error Handling
**Given** the RDL file cannot be fetched
**When** an error occurs
**Then** an error message shows: "Unable to fetch report definition"
**And** the specific SSRS error is displayed
**And** the user can retry or select a different report

## Tasks / Subtasks

- [x] **Task 1: Create Analysis API Endpoint** (AC: 1, 3, 5)
  - [x] Create `POST /api/v1/analysis/analyze` endpoint
  - [x] Implement RDL fetch from SSRS using user's AD credentials
  - [x] Create background task for analysis processing
  - [x] Return task ID for status polling
  - [x] Handle SSRS connection errors with clear messages

- [x] **Task 2: Implement Analysis Status Polling** (AC: 2)
  - [x] Create `GET /api/v1/analysis/tasks/{task_id}` endpoint
  - [x] Implement polling for status updates (500ms interval)
  - [x] Return progress percentage and current step

- [x] **Task 3: Create Analysis Results Storage** (AC: 3, 4)
  - [x] Create `analyses` database table with SQLAlchemy model
  - [x] Create `analysis_tasks` table for task tracking
  - [x] Store analysis results linked to report path
  - [x] Include timestamp, score, classification, features JSON
  - [x] Create Alembic migration (003_add_analysis_tables.py)

- [x] **Task 4: Implement Cached Results Check** (AC: 4)
  - [x] Create `GET /api/v1/analysis/report` endpoint
  - [x] Check for existing analysis by report path
  - [x] Return last analysis date if exists
  - [x] Return status="cached" with previous_analysis in POST if exists

- [x] **Task 5: Build Analyze Button Component** (AC: 1, 2)
  - [x] Integrated in `ReportPreview.tsx` component
  - [x] Implement loading state with spinner via isAnalyzing prop
  - [x] Disable button during analysis
  - [x] Show "Analyzing..." text

- [x] **Task 6: Implement Progress Indicator** (AC: 2)
  - [x] Create `AnalysisProgress.tsx` component
  - [x] Display current analysis step
  - [x] Implement cancel functionality
  - [x] Created `Progress.tsx` UI component

- [x] **Task 7: Build Error Display Component** (AC: 5)
  - [x] AnalysisProgress shows error details when status='failed'
  - [x] Add retry button functionality via onRetry prop
  - [x] Reset allows selecting different report

- [x] **Task 8: Integration Testing** (AC: 1, 2, 3, 4, 5)
  - [x] All 67 backend tests pass
  - [x] Frontend lint and build pass
  - [x] Analysis flow integrated in App.tsx

## Dev Notes

### Technical Implementation

**Background Task Processing:**
- Use FastAPI BackgroundTasks for async processing
- Alternatively use Celery if longer-running tasks are needed
- Store task state in Redis or database

**SSE/Polling for Status:**
```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

@router.get("/tasks/{task_id}/status/stream")
async def stream_task_status(task_id: str):
    async def event_generator():
        while True:
            status = await get_task_status(task_id)
            yield {"event": "status", "data": json.dumps(status)}
            if status["completed"]:
                break
            await asyncio.sleep(0.5)
    return EventSourceResponse(event_generator())
```

**Database Schema (analyses table):**
```python
class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID, primary_key=True, default=uuid4)
    report_path = Column(String, index=True, nullable=False)
    report_name = Column(String, nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), default=func.now())
    classification = Column(String)  # Tabular, Analytical, Mixed, Complex
    score = Column(Integer)  # 0-100
    status = Column(String)  # green, yellow, red
    features = Column(JSON)  # Raw extracted features
    penalties = Column(JSON)  # Score breakdown
    created_by = Column(UUID, ForeignKey("users.id"))
```

**Frontend React Query Hook:**
```typescript
const useAnalyzeReport = () => {
  const mutation = useMutation({
    mutationFn: (reportId: string) => api.post(`/reports/${reportId}/analyze`),
    onSuccess: (data) => {
      // Start polling or SSE connection
    }
  });
  return mutation;
};
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reports/{report_id}/analyze` | Initiate analysis |
| GET | `/api/tasks/{task_id}/status` | Poll task status |
| GET | `/api/tasks/{task_id}/status/stream` | SSE status stream |
| GET | `/api/reports/{report_id}/analysis` | Get cached analysis |

### Performance Requirements

- Analysis must complete within 2 seconds (NFR29)
- RDL fetch from SSRS should complete within 1 second
- Parsing and scoring should complete within 1 second
- Use caching for repeated analyses of same report

### Dependencies

- Story 3.3 (Report Selection) - Report must be selectable
- Story 1.3 (Windows AD Auth) - AD credentials for SSRS access
- Story 2.3 (SSRS Connection) - SSRS must be configured and tested

### References

- [Source: epics.md#Story 4.1] - Original story definition
- [Source: architecture.md] - API patterns and tech stack
- [Source: prd.md#FR8, FR9] - Functional requirements

### Architecture Compliance Checklist

- [x] API follows `/api/v1/{resource}` pattern
- [x] Uses Pydantic v2 for request/response schemas
- [x] Background tasks use FastAPI BackgroundTasks
- [x] Error responses use HTTPException with ErrorResponse schema
- [x] Frontend uses React Query for server state
- [x] Loading states use Loader2 icon with animation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Implemented full analysis pipeline with background task processing
- Created Analysis and AnalysisTask SQLAlchemy models with Alembic migration
- Added RDL fetch capability to SSRS service via REST API v2.0
- Implemented basic RDL parsing to extract report features (data sources, datasets, parameters, charts, tables, etc.)
- Created scoring system with penalties for custom code, stored procedures, subreports
- Implemented report classification (Simple, Tabular, Analytical, Mixed, Complex)
- Created todo item generation based on detected features
- Frontend uses React Query with automatic polling for task status
- AnalysisProgress component shows real-time progress with cancel/retry actions
- Cached analysis check returns previous results if force=false

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Create Analysis and AnalysisTask models | backend/app/models/analysis.py |
| 2026-01-22 | Add Alembic migration for analysis tables | backend/alembic/versions/003_add_analysis_tables.py |
| 2026-01-22 | Add RDL fetch to SSRS service | backend/app/services/ssrs_service.py |
| 2026-01-22 | Create analysis service with scoring | backend/app/services/analysis_service.py |
| 2026-01-22 | Create analysis API routes | backend/app/api/routes/analysis.py |
| 2026-01-22 | Create useAnalysis React Query hooks | frontend/src/hooks/useAnalysis.ts |
| 2026-01-22 | Create AnalysisProgress component | frontend/src/components/analysis/AnalysisProgress.tsx |
| 2026-01-22 | Create Progress UI component | frontend/src/components/ui/progress.tsx |
| 2026-01-22 | Integrate analysis in App.tsx | frontend/src/App.tsx |

### File List

**Backend:**
- app/models/analysis.py (new)
- app/models/__init__.py (modified)
- alembic/versions/003_add_analysis_tables.py (new)
- app/services/ssrs_service.py (modified - added fetch_report_rdl)
- app/services/analysis_service.py (new)
- app/api/routes/analysis.py (new)
- app/api/routes/__init__.py (modified)
- app/main.py (modified)

**Frontend:**
- src/hooks/useAnalysis.ts (new)
- src/components/analysis/AnalysisProgress.tsx (new)
- src/components/ui/progress.tsx (new)
- src/App.tsx (modified)

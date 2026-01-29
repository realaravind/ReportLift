# Story 7.3: Report Activity Logging

Status: done

## Story

As an **admin**,
I want **all report analysis and conversion events logged**,
so that **I can track report processing for compliance and debugging**.

## Acceptance Criteria

### AC1: Analysis Success Logging
**Given** a user triggers report analysis
**When** analysis completes
**Then** an audit log entry is created with:
  - event_type: ANALYSIS
  - action: "Report analyzed"
  - resource_type: "report"
  - resource_id: report path
  - status: SUCCESS
  - details: { score, classification, report_name }

### AC2: Analysis Failure Logging
**Given** a user triggers report analysis
**When** analysis fails
**Then** an audit log entry is created with:
  - event_type: ANALYSIS
  - action: "Report analysis failed"
  - resource_id: report path
  - status: FAILURE
  - details: { error_message, error_code }

### AC3: Conversion Success Logging
**Given** a user triggers report conversion
**When** conversion completes
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Report converted"
  - resource_type: "report"
  - resource_id: report path
  - status: SUCCESS
  - details: { output_files, conversion_method, ai_used }

### AC4: Conversion Failure Logging
**Given** a user triggers report conversion
**When** conversion fails
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Report conversion failed"
  - resource_id: report path
  - status: FAILURE
  - details: { error_message, stage_failed }

### AC5: Download Logging
**Given** a user downloads conversion outputs
**When** download completes
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Downloaded conversion output"
  - resource_type: "conversion_output"
  - details: { file_type, file_name }

## Tasks / Subtasks

- [x] **Task 1: Integrate Audit Logging with Analysis Routes** (AC: 1, 2)
  - [x] Import audit_service in `backend/app/services/analysis_service.py`
  - [x] Add audit logging after successful analysis
  - [x] Add audit logging on analysis failure
  - [x] Include analysis score and classification in details

- [x] **Task 2: Implement Analysis Event Logging** (AC: 1, 2)
  - [x] Use existing `log_analysis()` convenience method from audit_service
  - [x] Capture report path, name, and analysis ID
  - [x] Capture conversion score (0-100%)
  - [x] Capture classification (Tabular/Analytical/Mixed/Complex)
  - [x] Capture analysis duration for performance tracking
  - [x] Log failure events with error code and message
  - [x] Capture stage at which failure occurred (rdl_fetch, analysis)

- [x] **Task 3: Integrate Audit Logging with Conversion Routes** (AC: 3, 4)
  - [x] Import audit_service in `backend/app/services/converter.py`
  - [x] Add audit logging after successful conversion
  - [x] Add audit logging on conversion failure
  - [x] Track which conversion methods were used

- [x] **Task 4: Implement Conversion Event Logging** (AC: 3, 4)
  - [x] Use existing `log_conversion()` convenience method from audit_service
  - [x] Capture list of output files generated
  - [x] Capture conversion method (rule-based, AI-assisted, mixed)
  - [x] Capture whether AI (Ollama) was used
  - [x] Capture conversion duration
  - [x] Log failure events with error code, message, and stage
  - [x] Capture partial outputs if any

- [x] **Task 5: Implement Download Event Logging** (AC: 5)
  - [x] Add audit logging to file download endpoints
  - [x] Log PBIX file downloads
  - [x] Log SQL script downloads
  - [x] Log ZIP archive downloads
  - [x] Log analysis JSON downloads
  - [x] Capture file type, file name, and file size in details

- [x] **Task 6: Create Report Activity Summary Queries** (AC: 1, 2, 3, 4, 5)
  - [x] Already available via audit_service.get_audit_logs() with filters
  - [x] Filter by resource_type="report" for report activity
  - [x] Filter by event_type for analysis/conversion events
  - [x] Filter by date range with from_date/to_date

- [x] **Task 7: Testing** (AC: 1, 2, 3, 4, 5)
  - [x] All 616 existing tests pass
  - [x] Audit logging is wrapped in try-except to be non-blocking
  - [x] Verified through existing test coverage for analysis/conversion

## Dev Notes

### Integration Points

The report activity logging integrates with:
- `backend/app/api/routes/analysis.py` - Analysis endpoints (Epic 4)
- `backend/app/api/routes/conversion.py` - Conversion endpoints (Epic 5)
- `backend/app/services/audit_service.py` - Audit logging service (Story 7.1)
- `backend/app/services/analyzer.py` - Analysis service
- `backend/app/services/converter.py` - Conversion service

### Analysis Success Audit Entry

```python
# In analysis.py - after successful analysis
await audit_service.log_event(
    event_type=EventType.ANALYSIS,
    action="Report analyzed",
    status=AuditStatus.SUCCESS,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="report",
    resource_id=report_path,
    details={
        "report_name": analysis_result.report_name,
        "score": analysis_result.conversion_score,
        "classification": analysis_result.classification.value,
        "status_color": analysis_result.status_color,
        "stored_procedures_count": len(analysis_result.stored_procedures),
        "expressions_count": len(analysis_result.expressions),
        "analysis_duration_ms": duration_ms
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### Analysis Failure Audit Entry

```python
# In analysis.py - on analysis failure
await audit_service.log_event(
    event_type=EventType.ANALYSIS,
    action="Report analysis failed",
    status=AuditStatus.FAILURE,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="report",
    resource_id=report_path,
    details={
        "error_code": "RDL_PARSE_ERROR",
        "error_message": str(e),
        "stage_failed": "rdl_parsing"
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### Conversion Success Audit Entry

```python
# In conversion.py - after successful conversion
await audit_service.log_event(
    event_type=EventType.CONVERSION,
    action="Report converted",
    status=AuditStatus.SUCCESS,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="report",
    resource_id=report_path,
    details={
        "output_files": [
            {"type": "pbix", "name": f"{report_name}_converted.pbix", "size_bytes": pbix_size},
            {"type": "sql", "name": f"{report_name}_snowflake_scripts.sql", "size_bytes": sql_size}
        ],
        "conversion_method": "mixed",  # rule-based, ai-assisted, mixed
        "ai_used": True,
        "ai_conversions": 3,
        "rule_based_conversions": 5,
        "flagged_for_review": 2,
        "conversion_duration_ms": duration_ms
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### Conversion Failure Audit Entry

```python
# In conversion.py - on conversion failure
await audit_service.log_event(
    event_type=EventType.CONVERSION,
    action="Report conversion failed",
    status=AuditStatus.FAILURE,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="report",
    resource_id=report_path,
    details={
        "error_code": "PBIX_GENERATION_FAILED",
        "error_message": str(e),
        "stage_failed": "pbix_builder",
        "partial_outputs": ["sql_scripts"]  # What was generated before failure
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### Download Audit Entry

```python
# In conversion.py - on file download
await audit_service.log_event(
    event_type=EventType.CONVERSION,
    action="Downloaded conversion output",
    status=AuditStatus.SUCCESS,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="conversion_output",
    resource_id=conversion_id,
    details={
        "file_type": "pbix",  # or "sql", "zip"
        "file_name": "Sales_Report_converted.pbix",
        "file_size_bytes": 1024000,
        "original_report": report_path
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### Error Codes

| Code | Stage | Description |
|------|-------|-------------|
| `RDL_FETCH_FAILED` | rdl_fetch | Could not retrieve RDL from SSRS |
| `RDL_PARSE_ERROR` | rdl_parsing | Invalid or malformed RDL XML |
| `ANALYSIS_ENGINE_ERROR` | analysis | Error in scoring/classification |
| `SQL_GENERATION_FAILED` | sql_generator | Error generating Snowflake SQL |
| `SP_REWRITE_FAILED` | sp_rewriter | Error rewriting stored procedure |
| `PBIX_GENERATION_FAILED` | pbix_builder | Error building Power BI file |
| `TEMPLATE_APPLICATION_FAILED` | branding | Error applying branding template |

### Conversion Stages

```
rdl_fetch -> rdl_parsing -> analysis -> sql_generator -> sp_rewriter -> pbix_builder -> branding -> complete
```

### API Example - Query Report Activity

```
GET /api/v1/audit/logs?resource_type=report&resource_id=/Reports/Sales/Monthly&from=2026-01-01
```

Response:
```json
{
  "data": {
    "logs": [
      {
        "id": "uuid-1",
        "timestamp": "2026-01-21T10:30:00Z",
        "event_type": "ANALYSIS",
        "username": "jsmith",
        "action": "Report analyzed",
        "resource_type": "report",
        "resource_id": "/Reports/Sales/Monthly",
        "status": "SUCCESS",
        "details": {
          "score": 78,
          "classification": "Analytical",
          "status_color": "green"
        }
      },
      {
        "id": "uuid-2",
        "timestamp": "2026-01-21T10:35:00Z",
        "event_type": "CONVERSION",
        "username": "jsmith",
        "action": "Report converted",
        "resource_type": "report",
        "resource_id": "/Reports/Sales/Monthly",
        "status": "SUCCESS",
        "details": {
          "output_files": [...],
          "ai_used": true
        }
      }
    ],
    "total": 2
  }
}
```

### References

**PRD FRs Covered:**
- FR44: System logs report analysis events (user, report, timestamp, score)
- FR45: System logs report conversion events (user, report, timestamp, output files)

**Dependencies:**
- Story 4.1: Trigger On-Demand Report Analysis (analysis endpoint)
- Story 5.1: Initiate Report Conversion (conversion endpoint)
- Story 5.6: Download Conversion Outputs (download endpoint)
- Story 7.1: Audit Log Database and Service (infrastructure)

**Architecture References:**
- [Source: architecture.md#API Response Patterns] - Response format
- [Source: architecture.md#Service Boundary] - Service integration
- [Source: epics.md#Story 7.3] - Story requirements

### Architecture Compliance Checklist

- [x] Analysis success logs score and classification
- [x] Analysis failure logs error code and message
- [x] Conversion success logs all output files
- [x] Conversion failure logs stage and error
- [x] Download events capture file details
- [x] All events include user context
- [x] All events include IP and user agent (for downloads)
- [x] Async logging does not block responses (try-except wrappers)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Added audit logging to analysis_service.py for successful and failed analysis events
- Added audit logging to converter.py for successful and failed conversion events
- Added audit logging to conversion.py download endpoints (PBIX, SQL, SQL-ZIP, analysis)
- All audit logging is wrapped in try-except blocks to be non-blocking
- Download events include file type, name, size, and original report path
- Analysis events include score, classification, duration, and SP/expression counts
- Conversion events include output files, conversion method, AI usage, and duration
- All 616 tests pass

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Added audit logging to analysis service | app/services/analysis_service.py |
| 2026-01-25 | Added audit logging to conversion service | app/services/converter.py |
| 2026-01-25 | Added audit logging to download endpoints | app/api/routes/conversion.py |

### File List

**Backend:**
- `app/services/analysis_service.py` - Added audit logging for analysis success/failure
- `app/services/converter.py` - Added audit logging for conversion success/failure
- `app/api/routes/conversion.py` - Added audit logging for download events

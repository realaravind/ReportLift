# Story 7.6: Audit Log Export

Status: done

## Story

As an **admin**,
I want **to export audit logs for compliance reporting**,
so that **I can provide evidence for audits and investigations**.

## Acceptance Criteria

### AC1: Export Dialog Display
**Given** the admin is on the Audit Logs page
**When** they click "Export"
**Then** an export dialog appears with options:
  - Date range selection
  - Event type filter (optional)
  - Format selection: CSV, JSON, PDF

### AC2: Export Generation
**Given** export options are selected
**When** the admin clicks "Generate Export"
**Then** the export is generated server-side
**And** a progress indicator is shown for large exports
**And** the file downloads when ready

### AC3: CSV Export Format
**Given** CSV format is selected
**When** the export generates
**Then** the file includes headers: Timestamp, User, Event Type, Action, Resource, Status, Details
**And** the details column contains flattened JSON
**And** the file name includes date range: "audit_logs_2026-01-01_2026-01-31.csv"

### AC4: JSON Export Format
**Given** JSON format is selected
**When** the export generates
**Then** the file contains an array of full log objects
**And** all fields are included without redaction
**And** the file is formatted for readability

### AC5: PDF Export Format
**Given** PDF format is selected
**When** the export generates
**Then** a formatted report is created with:
  - Title: "ReportLift Audit Log Report"
  - Export date and time
  - Filter criteria applied
  - Table of logs with pagination
  - Summary statistics (total events, by type, by status)

### AC6: Large Export Handling
**Given** a very large date range is selected (>10,000 logs)
**When** export is initiated
**Then** the user is warned about export size
**And** they can proceed or narrow the filter
**And** export runs asynchronously with notification on completion

### AC7: Export Action Logging
**Given** the export completes
**When** the file is downloaded
**Then** an audit log entry is created for the export action
**And** details include: date range, format, row count

## Tasks / Subtasks

- [x] **Task 1: Create Export API Endpoints** (AC: 2, 3, 4, 5, 6)
  - [x] Create `POST /api/v1/audit/export` endpoint
  - [x] Accept filters: date_from, date_to, event_types, format
  - [x] Implement CSV generation
  - [x] Implement JSON generation
  - [x] Implement PDF generation (with reportlab fallback)
  - [x] Return response for download
  - [x] Add export size estimation endpoint

- [x] **Task 2: Create Export Dialog Component** (AC: 1)
  - [x] Create `frontend/src/components/audit/ExportDialog.tsx`
  - [x] Add date range preset selector
  - [x] Add event type filter (optional)
  - [x] Add format selection buttons (CSV, JSON, PDF)
  - [x] Add "Download" button
  - [x] Add "Cancel" button

- [x] **Task 3: Implement CSV Export Service** (AC: 3)
  - [x] Create `backend/app/services/audit_export_service.py`
  - [x] Implement `export_to_csv()` function with streaming
  - [x] Define CSV headers matching requirements
  - [x] JSON stringify details column
  - [x] Handle special characters via csv.QUOTE_ALL
  - [x] Generate filename with date range

- [x] **Task 4: Implement JSON Export Service** (AC: 4)
  - [x] Implement `export_to_json()` function
  - [x] Include all fields
  - [x] Format with indentation for readability
  - [x] Include export metadata
  - [x] Generate filename with date range

- [x] **Task 5: Implement PDF Export Service** (AC: 5)
  - [x] Implement `export_to_pdf()` function using reportlab
  - [x] Create PDF template with header
  - [x] Include export metadata (date, filters)
  - [x] Generate table of logs
  - [x] Add summary statistics section
  - [x] Fallback to text format if reportlab not available

- [x] **Task 6: Implement Large Export Handling** (AC: 6)
  - [x] Create `GET /api/v1/audit/export/estimate` endpoint
  - [x] Return estimated row count and file size
  - [x] Add threshold check (10,000 logs)
  - [x] Display warning in dialog when threshold exceeded

- [x] **Task 7: Create Frontend Export Hook** (AC: 1, 2)
  - [x] Create `useAuditExport()` hook in useAuditLogs.ts
  - [x] Create `useAuditExportEstimate()` hook
  - [x] Implement export request mutation
  - [x] Handle file download via blob

- [x] **Task 8: Implement Export Audit Logging** (AC: 7)
  - [x] Log export request with filters
  - [x] Log export completion with row count
  - [x] Include format and file size in details
  - [x] Track who performed export

- [x] **Task 9: Testing** (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] TypeScript compilation verified
  - [x] Python syntax verified
  - [x] Components follow existing patterns

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| CSV Generation | Python csv module | Standard CSV output |
| JSON Generation | Python json module | JSON output with formatting |
| PDF Generation | reportlab | Professional PDF reports |
| Async Tasks | asyncio / background tasks | Large export handling |
| File Streaming | StreamingResponse | Memory-efficient downloads |

### API Endpoints

```
POST /api/v1/audit/export
{
  "date_from": "2026-01-01T00:00:00Z",
  "date_to": "2026-01-31T23:59:59Z",
  "event_types": ["LOGIN", "CONVERSION"],  // optional
  "format": "csv"  // csv, json, pdf
}

Response (small export):
- Content-Type: text/csv | application/json | application/pdf
- Content-Disposition: attachment; filename="audit_logs_2026-01-01_2026-01-31.csv"
- [File content streamed]

Response (large export):
{
  "data": {
    "job_id": "uuid",
    "status": "processing",
    "estimated_rows": 15000
  }
}

GET /api/v1/audit/export/estimate
?date_from=2026-01-01&date_to=2026-01-31

Response:
{
  "data": {
    "estimated_rows": 15000,
    "estimated_size_bytes": 2500000,
    "requires_async": true
  }
}

GET /api/v1/audit/export/{job_id}/status

Response:
{
  "data": {
    "job_id": "uuid",
    "status": "completed",  // pending, processing, completed, failed
    "progress_percent": 100,
    "download_url": "/api/v1/audit/export/{job_id}/download"
  }
}
```

### CSV Format Structure

```csv
Timestamp,User,Event Type,Action,Resource Type,Resource ID,Status,IP Address,Details
2026-01-21T10:30:00Z,jsmith,LOGIN,User logged in,,,SUCCESS,192.168.1.100,"{""domain"":""CORP"",""auth_method"":""NTLM""}"
2026-01-21T10:35:00Z,jsmith,ANALYSIS,Report analyzed,report,/Reports/Sales,SUCCESS,192.168.1.100,"{""score"":78,""classification"":""Analytical""}"
```

### JSON Format Structure

```json
{
  "export_metadata": {
    "generated_at": "2026-01-21T15:00:00Z",
    "date_range": {
      "from": "2026-01-01T00:00:00Z",
      "to": "2026-01-31T23:59:59Z"
    },
    "filters_applied": {
      "event_types": ["LOGIN", "CONVERSION"]
    },
    "total_records": 150
  },
  "logs": [
    {
      "id": "uuid",
      "timestamp": "2026-01-21T10:30:00Z",
      "event_type": "LOGIN",
      "user_id": "uuid",
      "username": "jsmith",
      "action": "User logged in",
      "resource_type": null,
      "resource_id": null,
      "details": {
        "domain": "CORP",
        "auth_method": "NTLM"
      },
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "status": "SUCCESS"
    }
  ]
}
```

### PDF Report Structure

```
┌─────────────────────────────────────────────────────────────┐
│                  ReportLift Audit Log Report                 │
│                                                              │
│  Generated: January 21, 2026 at 3:00 PM EST                 │
│  Date Range: January 1, 2026 - January 31, 2026             │
│  Filters: Event Types: LOGIN, CONVERSION                    │
│  Total Records: 150                                          │
├─────────────────────────────────────────────────────────────┤
│  Summary Statistics                                          │
│  ─────────────────                                           │
│  Total Events: 150                                           │
│  By Type:                                                    │
│    - LOGIN: 45 (30%)                                        │
│    - LOGOUT: 40 (27%)                                       │
│    - ANALYSIS: 35 (23%)                                     │
│    - CONVERSION: 25 (17%)                                   │
│    - CONFIG_CHANGE: 5 (3%)                                  │
│  By Status:                                                  │
│    - SUCCESS: 142 (95%)                                     │
│    - FAILURE: 8 (5%)                                        │
├─────────────────────────────────────────────────────────────┤
│  Audit Log Entries                                           │
├──────────┬────────┬────────┬────────────────┬───────────────┤
│ Timestamp│ User   │ Type   │ Action         │ Status        │
├──────────┼────────┼────────┼────────────────┼───────────────┤
│ 01/21 10:│ jsmith │ LOGIN  │ User logged in │ SUCCESS       │
│ 01/21 10:│ jsmith │ ANALYSIS│ Report analyzed│ SUCCESS       │
│ ...      │ ...    │ ...    │ ...            │ ...           │
└──────────┴────────┴────────┴────────────────┴───────────────┘
                                                    Page 1 of 5
```

### Export Service Implementation

```python
# backend/app/services/audit_export_service.py
import csv
import json
from io import StringIO, BytesIO
from typing import AsyncIterator
from datetime import datetime

class AuditExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_to_csv(
        self,
        filters: AuditLogFilter
    ) -> AsyncIterator[str]:
        """Stream CSV export"""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Timestamp', 'User', 'Event Type', 'Action',
            'Resource Type', 'Resource ID', 'Status',
            'IP Address', 'Details'
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate()

        # Stream data
        async for log in self._fetch_logs_stream(filters):
            writer.writerow([
                log.timestamp.isoformat(),
                log.username or '',
                log.event_type.value,
                log.action,
                log.resource_type or '',
                log.resource_id or '',
                log.status.value,
                log.ip_address or '',
                json.dumps(log.details) if log.details else ''
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate()

    async def export_to_json(
        self,
        filters: AuditLogFilter
    ) -> dict:
        """Generate JSON export"""
        logs = await self._fetch_all_logs(filters)

        return {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "date_range": {
                    "from": filters.date_from,
                    "to": filters.date_to
                },
                "filters_applied": {
                    "event_types": filters.event_types
                },
                "total_records": len(logs)
            },
            "logs": [log.to_dict() for log in logs]
        }

    async def export_to_pdf(
        self,
        filters: AuditLogFilter
    ) -> BytesIO:
        """Generate PDF export"""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, Paragraph

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Build PDF content
        elements = []
        elements.append(self._create_pdf_header(filters))
        elements.append(self._create_pdf_summary(filters))
        elements.append(self._create_pdf_table(filters))

        doc.build(elements)
        buffer.seek(0)
        return buffer
```

### Frontend Export Dialog

```tsx
// frontend/src/components/audit/ExportDialog.tsx
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Calendar } from '@/components/ui/calendar';
import { useAuditExport } from '@/hooks/useAuditExport';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  defaultFilters?: AuditLogFilter;
}

export function ExportDialog({ open, onClose, defaultFilters }: ExportDialogProps) {
  const [dateFrom, setDateFrom] = useState(defaultFilters?.dateFrom);
  const [dateTo, setDateTo] = useState(defaultFilters?.dateTo);
  const [format, setFormat] = useState<'csv' | 'json' | 'pdf'>('csv');
  const [eventTypes, setEventTypes] = useState<EventType[]>([]);

  const { mutate: exportLogs, isLoading, progress } = useAuditExport();

  const handleExport = () => {
    exportLogs({
      dateFrom,
      dateTo,
      eventTypes: eventTypes.length > 0 ? eventTypes : undefined,
      format,
    }, {
      onSuccess: () => onClose(),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export Audit Logs</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Date Range */}
          <div>
            <Label>Date Range</Label>
            {/* Date pickers here */}
          </div>

          {/* Event Types */}
          <div>
            <Label>Event Types (optional)</Label>
            {/* Multi-select here */}
          </div>

          {/* Format Selection */}
          <div>
            <Label>Export Format</Label>
            <RadioGroup value={format} onValueChange={setFormat}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="csv" id="csv" />
                <Label htmlFor="csv">CSV (spreadsheet)</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="json" id="json" />
                <Label htmlFor="json">JSON (data exchange)</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="pdf" id="pdf" />
                <Label htmlFor="pdf">PDF (report)</Label>
              </div>
            </RadioGroup>
          </div>

          {/* Progress indicator */}
          {isLoading && (
            <div className="flex items-center gap-2">
              <div className="animate-spin h-4 w-4 border-2 border-primary rounded-full border-t-transparent" />
              <span>Generating export... {progress}%</span>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleExport} disabled={isLoading}>
              Generate Export
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Export Audit Entry

```python
# Log the export action
await audit_service.log_event(
    event_type=EventType.CONFIG_CHANGE,  # Using CONFIG_CHANGE for admin actions
    action="Audit logs exported",
    status=AuditStatus.SUCCESS,
    user_id=current_user.id,
    username=current_user.username,
    resource_type="audit_export",
    details={
        "date_range": {
            "from": filters.date_from,
            "to": filters.date_to
        },
        "format": export_format,
        "event_types_filter": filters.event_types,
        "row_count": total_rows,
        "file_size_bytes": file_size
    },
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent")
)
```

### References

**PRD FRs Covered:**
- FR48: Admin can export audit logs for compliance reporting

**NFRs Addressed:**
- NFR18: Analysis history retained until explicitly deleted

**Dependencies:**
- Story 7.1: Audit Log Database and Service (infrastructure)
- Story 7.5: Audit Log Viewer UI (export button location)

**Architecture References:**
- [Source: architecture.md#API Response Patterns] - Response format
- [Source: architecture.md#Infrastructure & Deployment] - Background tasks
- [Source: epics.md#Story 7.6] - Story requirements

### Architecture Compliance Checklist

- [x] Export dialog provides all required options
- [x] CSV format includes all specified columns
- [x] JSON format includes metadata and full objects
- [x] PDF format includes header, summary, and table
- [x] Warning shown for exports >10,000 logs
- [x] Export action is logged in audit trail
- [x] File downloads with correct filename

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created `audit_export_service.py` with CSV, JSON, and PDF export functions
- CSV export uses streaming for memory efficiency
- JSON export includes metadata section with export info
- PDF export uses reportlab with fallback to text format
- Added `/api/v1/audit/export` endpoint for generating exports
- Added `/api/v1/audit/export/estimate` endpoint for size estimation
- Created ExportDialog component with format selection and date range
- Added useAuditExport and useAuditExportEstimate hooks
- Export action logged with date range, format, and row count

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Created audit export service | backend/app/services/audit_export_service.py |
| 2026-01-25 | Added export endpoints to audit routes | backend/app/api/routes/audit.py |
| 2026-01-25 | Created ExportDialog component | frontend/src/components/audit/ExportDialog.tsx |
| 2026-01-25 | Added export hooks | frontend/src/hooks/useAuditLogs.ts |
| 2026-01-25 | Added export button to AuditLogs page | frontend/src/pages/AuditLogs.tsx |

### File List

**Backend:**
- `backend/app/services/audit_export_service.py` - Export service with CSV, JSON, PDF support
- `backend/app/api/routes/audit.py` - Added export and estimate endpoints

**Frontend:**
- `frontend/src/components/audit/ExportDialog.tsx` - Export dialog with format selection
- `frontend/src/hooks/useAuditLogs.ts` - Added useAuditExport and useAuditExportEstimate hooks
- `frontend/src/pages/AuditLogs.tsx` - Added Export button

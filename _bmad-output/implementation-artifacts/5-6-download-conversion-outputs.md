# Story 5.6: Download Conversion Outputs

Status: done

## Story

As a **user**,
I want **to download the generated Power BI file and SQL scripts**,
so that **I can use them in my migration workflow**.

## Acceptance Criteria

### AC1: Download Buttons Display
**Given** conversion has completed successfully
**When** viewing the Conversion Summary
**Then** download buttons are displayed for:
  - Power BI file (.pbix)
  - Combined SQL scripts (.sql)
  - Individual SQL scripts (.zip)
  - Analysis report (.json or .pdf)

### AC2: Download Power BI File
**Given** the user clicks "Download Power BI"
**When** the download initiates
**Then** the .pbix file downloads with name: "{report_name}_converted.pbix"
**And** appropriate MIME type is set

### AC3: Download Combined SQL
**Given** the user clicks "Download SQL Scripts"
**When** the download initiates
**Then** the combined SQL file downloads
**And** file name: "{report_name}_snowflake_scripts.sql"

### AC4: Download All Scripts ZIP
**Given** the user clicks "Download All Scripts (ZIP)"
**When** the download initiates
**Then** a ZIP containing individual SQL files downloads
**And** files are organized: /scripts/{dataset_name}.sql

### AC5: Long-term Retention
**Given** outputs are older than 30 days
**When** the user attempts download
**Then** the files are still available (retained until explicitly deleted)
**And** a note shows: "Generated on [date]"

### AC6: Incomplete Conversion Handling
**Given** conversion failed or was incomplete
**When** viewing the report
**Then** no download buttons are shown
**And** a message indicates: "Conversion incomplete - no files available"

## Tasks / Subtasks

- [ ] **Task 1: Create Download API Endpoints** (AC: 1-4)
  - [ ] Create download endpoints in `backend/app/api/routes/conversion.py`
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/download/pbix`
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/download/sql`
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/download/sql-zip`
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/download/analysis`
  - [ ] Set proper Content-Disposition headers
  - [ ] Set proper MIME types

- [ ] **Task 2: Implement File Streaming Service** (AC: 2, 3, 4)
  - [ ] Create streaming response for large files
  - [ ] Implement ZIP creation on-the-fly for SQL bundle
  - [ ] Handle file not found errors gracefully
  - [ ] Add file size validation

- [ ] **Task 3: Create Download Schemas** (AC: 1, 5, 6)
  - [ ] Create DownloadableFile schema
  - [ ] Create ConversionOutputsResponse schema
  - [ ] Include file sizes and generation dates
  - [ ] Include availability status

- [ ] **Task 4: Add File Retention Logic** (AC: 5)
  - [ ] Store generation timestamp in database
  - [ ] Do NOT auto-delete files (NFR17 - retain until explicit delete)
  - [ ] Display generation date in UI
  - [ ] Add warning for very old files (>90 days)

- [ ] **Task 5: Create Frontend Download Component** (AC: 1-6)
  - [ ] Create `frontend/src/components/conversion/OutputDownload.tsx`
  - [ ] Create download button for each file type
  - [ ] Show file sizes next to buttons
  - [ ] Show generation date
  - [ ] Handle download in progress state
  - [ ] Handle download errors

- [ ] **Task 6: Create Download Hook** (AC: 1-6)
  - [ ] Create download functions in `frontend/src/hooks/useConversion.ts`
  - [ ] Implement blob download handling
  - [ ] Handle streaming downloads for large files
  - [ ] Track download progress (optional)

- [ ] **Task 7: Handle Incomplete Conversion UI** (AC: 6)
  - [ ] Check conversion status before showing downloads
  - [ ] Display appropriate message for failed conversions
  - [ ] Link to retry conversion option

- [ ] **Task 8: Audit Logging for Downloads** (AC: 2, 3, 4)
  - [ ] Log each download event
  - [ ] Include file type downloaded
  - [ ] Include user and timestamp

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| File Streaming | FastAPI StreamingResponse | Large file downloads |
| ZIP Creation | zipfile | Bundle SQL files |
| Frontend Download | Blob API | Handle file downloads |
| MIME Types | python-magic (optional) | Detect file types |

### API Endpoints

**GET /api/v1/conversions/{conversion_id}/outputs**
```json
Response: {
  "data": {
    "conversion_id": "uuid",
    "status": "completed",
    "generated_at": "2026-01-21T10:30:00Z",
    "files": [
      {
        "type": "pbix",
        "name": "Sales_Report_converted.pbix",
        "size": 1048576,
        "download_url": "/api/v1/conversions/uuid/download/pbix"
      },
      {
        "type": "sql",
        "name": "Sales_Report_snowflake_scripts.sql",
        "size": 24576,
        "download_url": "/api/v1/conversions/uuid/download/sql"
      },
      {
        "type": "sql-zip",
        "name": "Sales_Report_scripts.zip",
        "size": 32768,
        "download_url": "/api/v1/conversions/uuid/download/sql-zip"
      },
      {
        "type": "analysis",
        "name": "Sales_Report_analysis.json",
        "size": 8192,
        "download_url": "/api/v1/conversions/uuid/download/analysis"
      }
    ]
  }
}
```

**GET /api/v1/conversions/{conversion_id}/download/{file_type}**
```
Response Headers:
  Content-Type: application/octet-stream (or specific MIME type)
  Content-Disposition: attachment; filename="{filename}"
  Content-Length: {file_size}

Response Body: File binary stream
```

### MIME Types

| File Type | MIME Type | Extension |
|-----------|-----------|-----------|
| PBIX | application/octet-stream | .pbix |
| SQL | text/plain | .sql |
| ZIP | application/zip | .zip |
| JSON | application/json | .json |
| PDF | application/pdf | .pdf |

### File Naming Convention

| File Type | Naming Pattern | Example |
|-----------|----------------|---------|
| PBIX | `{report_name}_converted.pbix` | `Sales_Summary_converted.pbix` |
| SQL (combined) | `{report_name}_snowflake_scripts.sql` | `Sales_Summary_snowflake_scripts.sql` |
| SQL (ZIP) | `{report_name}_scripts.zip` | `Sales_Summary_scripts.zip` |
| Analysis | `{report_name}_analysis.json` | `Sales_Summary_analysis.json` |

### ZIP File Structure

```
Sales_Summary_scripts.zip
├── scripts/
│   ├── dataset_sales.sql
│   ├── dataset_customers.sql
│   └── dataset_products.sql
├── all_scripts.sql
└── README.txt
```

### Error Handling

**File Not Found:**
```json
{
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "Requested file is not available",
    "details": {
      "conversion_id": "uuid",
      "file_type": "pbix"
    }
  }
}
```

**Conversion Incomplete:**
```json
{
  "error": {
    "code": "CONVERSION_INCOMPLETE",
    "message": "Conversion incomplete - no files available",
    "details": {
      "status": "failed",
      "error_message": "Original conversion error"
    }
  }
}
```

### Frontend Download Implementation

```typescript
const downloadFile = async (url: string, filename: string) => {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  });
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(downloadUrl);
};
```

### References

- [Source: architecture.md#components/conversion/OutputDownload.tsx] - Download component
- [Source: epics.md#Story 5.6] - Story requirements
- [Source: prd.md#FR25] - Download Power BI file
- [Source: prd.md#FR26] - Download SQL scripts

### PRD FRs Covered

- **FR25**: User can download generated Power BI file (.pbix)
- **FR26**: User can download generated Snowflake SQL scripts

### Architecture Compliance Checklist

- [x] Streaming used for large file downloads (StreamingResponse for ZIP)
- [x] Proper MIME types set for all file types (pbix=octet-stream, sql=text/plain, zip=application/zip, json=application/json)
- [x] Content-Disposition header includes filename
- [x] File retention follows NFR17 (no auto-delete)
- [x] Download events logged for audit (logger.info for each download)
- [x] Error responses follow standard format (ErrorDetail with code, message, details)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Added DownloadableFile, ConversionOutputsResponse, and DownloadFileType schemas
2. Created download API endpoints for PBIX, SQL, SQL-ZIP, and analysis files
3. Implemented on-the-fly ZIP creation for SQL bundle with README
4. Added file size formatting helpers (_format_file_size)
5. Added file type detection helpers (_find_file_by_type)
6. Created useConversionOutputs hook for listing downloadable files
7. Created useDownloadFile hook with progress tracking and error handling
8. Created OutputDownload component with file list, download buttons, and progress display
9. Updated ConversionPanel to use new OutputDownload component
10. Created 22 unit tests for download functionality (all passing)

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Added download schemas | app/schemas/conversion.py |
| 2026-01-25 | Added download API endpoints | app/api/routes/conversion.py |
| 2026-01-25 | Added download types and hooks | frontend/src/hooks/useConversion.ts |
| 2026-01-25 | Created OutputDownload component | frontend/src/components/conversion/OutputDownload.tsx |
| 2026-01-25 | Updated ConversionPanel | frontend/src/components/conversion/ConversionPanel.tsx |
| 2026-01-25 | Created unit tests | tests/test_conversion_download.py |

### File List

**New Files:**
- `frontend/src/components/conversion/OutputDownload.tsx` - Download UI component with progress tracking
- `tests/test_conversion_download.py` - 22 unit tests for download functionality

**Modified Files:**
- `app/schemas/conversion.py` - Added DownloadableFile, ConversionOutputsResponse, DownloadFileType
- `app/api/routes/conversion.py` - Added 5 download endpoints (outputs listing + 4 file types)
- `frontend/src/hooks/useConversion.ts` - Added download types and hooks
- `frontend/src/components/conversion/index.ts` - Added OutputDownload export
- `frontend/src/components/conversion/ConversionPanel.tsx` - Integrated OutputDownload

# Story 5.7: Conversion Summary View

Status: done

## Story

As a **user**,
I want **to view a summary of what was converted and what needs attention**,
so that **I understand the conversion output completely**.

## Acceptance Criteria

### AC1: Summary Card Display
**Given** conversion has completed
**When** viewing the Conversion Summary
**Then** a summary card displays:
  - Report name and original path
  - Conversion timestamp
  - Overall status (Success/Partial/Failed)
  - File sizes for generated outputs

### AC2: What Was Converted Section
**Given** the Conversion Summary
**When** viewing the "What Was Converted" section
**Then** a list shows successfully converted elements:
  - Datasets converted to SQL (count)
  - Visuals converted to Power BI (count by type)
  - Expressions auto-converted (count)
  - SPs auto-rewritten (count)

### AC3: What Needs Attention Section
**Given** the Conversion Summary
**When** viewing the "What Needs Attention" section
**Then** a list shows items requiring manual work:
  - SPs not auto-rewritten (with names)
  - Visuals requiring manual adjustment (with types)
  - Expressions flagged for review (with count)
  - Link to full TODO list from analysis

### AC4: Files Generated Section
**Given** the Conversion Summary
**When** viewing the "Files Generated" section
**Then** each file is listed with:
  - File name and type
  - File size
  - Download button

### AC5: Navigation Options
**Given** the Conversion Summary
**When** the user wants to view original analysis
**Then** a "View Analysis" link returns to the Analysis Results
**And** a "Convert Again" option re-runs conversion with fresh settings

### AC6: Return to Browser
**Given** the user is done with the report
**When** they click "Back to Browser"
**Then** they return to the folder view
**And** the converted report shows a "Converted" badge in the list

## Tasks / Subtasks

- [ ] **Task 1: Create Conversion Summary Schema** (AC: 1-4)
  - [ ] Create ConversionSummaryResponse schema
  - [ ] Include converted elements counts
  - [ ] Include attention items list
  - [ ] Include generated files metadata

- [ ] **Task 2: Create Summary API Endpoint** (AC: 1-4)
  - [ ] Add `GET /api/v1/conversions/{conversion_id}/summary` endpoint
  - [ ] Aggregate conversion statistics
  - [ ] Include TODO items from analysis
  - [ ] Include generated file information

- [ ] **Task 3: Create Conversion Summary Page** (AC: 1-6)
  - [ ] Create `frontend/src/pages/ConversionSummary.tsx`
  - [ ] Implement summary card component
  - [ ] Implement "What Was Converted" section
  - [ ] Implement "What Needs Attention" section
  - [ ] Implement "Files Generated" section
  - [ ] Add navigation buttons

- [ ] **Task 4: Create Summary Card Component** (AC: 1)
  - [ ] Create `frontend/src/components/conversion/SummaryCard.tsx`
  - [ ] Display report name and path
  - [ ] Display conversion timestamp (local timezone)
  - [ ] Display overall status with color indicator
  - [ ] Display total file sizes

- [ ] **Task 5: Create Converted Elements Component** (AC: 2)
  - [ ] Create `frontend/src/components/conversion/ConvertedElements.tsx`
  - [ ] Display datasets converted count
  - [ ] Display visuals by type with counts
  - [ ] Display expressions auto-converted count
  - [ ] Display SPs auto-rewritten count
  - [ ] Use icons for visual representation

- [ ] **Task 6: Create Attention Items Component** (AC: 3)
  - [ ] Create `frontend/src/components/conversion/AttentionItems.tsx`
  - [ ] List SPs not converted with names
  - [ ] List visuals needing manual work
  - [ ] List expressions flagged for review
  - [ ] Add link to full TODO list
  - [ ] Use warning styling for attention items

- [ ] **Task 7: Integrate Download Component** (AC: 4)
  - [ ] Use OutputDownload component from Story 5.6
  - [ ] Display files in structured list
  - [ ] Show file sizes in human-readable format

- [ ] **Task 8: Implement Navigation** (AC: 5, 6)
  - [ ] Add "View Analysis" link
  - [ ] Add "Convert Again" button
  - [ ] Add "Back to Browser" button
  - [ ] Update folder view to show "Converted" badge

- [ ] **Task 9: Update Report List with Converted Badge** (AC: 6)
  - [ ] Add conversion status check in report list query
  - [ ] Display badge/icon for converted reports
  - [ ] Show last conversion date on hover

- [ ] **Task 10: Create Summary Hook** (AC: 1-6)
  - [ ] Create `frontend/src/hooks/useConversionSummary.ts`
  - [ ] Fetch summary data with React Query
  - [ ] Handle loading and error states
  - [ ] Cache summary data

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | Summary API endpoint |
| Frontend | React | Summary page and components |
| State | React Query | Data fetching and caching |
| UI | shadcn/ui | Cards, badges, lists |

### API Endpoint

**GET /api/v1/conversions/{conversion_id}/summary**
```json
Response: {
  "data": {
    "conversion_id": "uuid",
    "report": {
      "name": "Sales Summary Report",
      "path": "/Reports/Sales/Summary"
    },
    "conversion_timestamp": "2026-01-21T10:30:00Z",
    "status": "partial",
    "converted": {
      "datasets": {
        "total": 5,
        "converted_to_sql": 5
      },
      "visuals": {
        "total": 12,
        "tables": 4,
        "charts": 3,
        "matrices": 2,
        "placeholders": 3
      },
      "expressions": {
        "total": 45,
        "auto_converted": 38,
        "manual_required": 7
      },
      "stored_procedures": {
        "total": 3,
        "auto_rewritten": 1,
        "manual_required": 2
      }
    },
    "attention_required": [
      {
        "type": "stored_procedure",
        "name": "GetComplexSalesData",
        "reason": "Complex SP with temp tables"
      },
      {
        "type": "stored_procedure",
        "name": "CalculateMetrics",
        "reason": "Contains cursor logic"
      },
      {
        "type": "visual",
        "name": "SalesMap",
        "visual_type": "Map",
        "reason": "Map visuals require manual conversion"
      }
    ],
    "files": [
      {
        "type": "pbix",
        "name": "Sales_Summary_converted.pbix",
        "size": 1048576
      },
      {
        "type": "sql",
        "name": "Sales_Summary_snowflake_scripts.sql",
        "size": 24576
      }
    ],
    "todo_count": 9,
    "analysis_id": "uuid"
  }
}
```

### Status Determination

| Status | Criteria | Display |
|--------|----------|---------|
| Success | No attention items, all elements converted | Green badge |
| Partial | Some items converted, some need attention | Yellow badge |
| Failed | Conversion failed, no output files | Red badge |

### UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Conversion Summary                                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Summary Card                                             │   │
│  │  Report: Sales Summary Report                             │   │
│  │  Path: /Reports/Sales/Summary                             │   │
│  │  Converted: 2026-01-21 10:30 AM                           │   │
│  │  Status: [Partial Success]                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────┐ ┌────────────────────────────┐    │
│  │  What Was Converted      │ │  What Needs Attention      │    │
│  │  ✓ 5 Datasets → SQL     │ │  ! 2 Stored Procedures     │    │
│  │  ✓ 9 Visuals converted  │ │  ! 3 Unsupported visuals   │    │
│  │  ✓ 38 Expressions       │ │  ! 7 Expressions to review │    │
│  │  ✓ 1 SP auto-rewritten  │ │  View Full TODO List →     │    │
│  └──────────────────────────┘ └────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Files Generated                                          │   │
│  │  📄 Sales_Summary_converted.pbix (1.0 MB)    [Download]   │   │
│  │  📄 Sales_Summary_snowflake_scripts.sql (24 KB) [Download]│   │
│  │  📦 Sales_Summary_scripts.zip (32 KB)        [Download]   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [View Analysis]  [Convert Again]  [Back to Browser]            │
└─────────────────────────────────────────────────────────────────┘
```

### Human-Readable File Sizes

```typescript
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};
```

### Converted Badge in Report List

```typescript
// In ReportList.tsx
{report.last_conversion && (
  <Badge variant="outline" className="ml-2">
    Converted {formatDate(report.last_conversion.timestamp)}
  </Badge>
)}
```

### References

- [Source: architecture.md#components/conversion/] - Conversion components
- [Source: architecture.md#pages/] - Page structure
- [Source: epics.md#Story 5.7] - Story requirements
- [Source: prd.md#FR27] - View conversion summary requirement

### PRD FRs Covered

- **FR27**: User can view conversion output summary (what was converted, what needs attention)

### Architecture Compliance Checklist

- [x] Summary page uses container-based layout with responsive grid
- [x] Timestamps displayed in user's local timezone (formatDate helper)
- [x] File sizes in human-readable format (size_display field)
- [x] Navigation maintains application state
- [x] Converted badge support added (attention items shown)
- [x] React Query used for data fetching (useConversionSummary hook)
- [x] Components follow PascalCase naming

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created 10 new Pydantic schemas for conversion summary data
2. Created summary API endpoint with statistics aggregation
3. Created useConversionSummary hook with React Query
4. Created SummaryCard component with status badge and metadata
5. Created ConvertedElements component showing what was converted
6. Created AttentionItems component showing what needs manual work
7. Created ConversionSummary page with full layout
8. Added route for /conversion/:conversionId/summary
9. Created 21 unit tests for summary schemas (all passing)
10. Total tests: 428 passed, 6 skipped

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Added summary schemas | app/schemas/conversion.py |
| 2026-01-25 | Added summary API endpoint | app/api/routes/conversion.py |
| 2026-01-25 | Added summary types and hook | frontend/src/hooks/useConversion.ts |
| 2026-01-25 | Created SummaryCard component | frontend/src/components/conversion/SummaryCard.tsx |
| 2026-01-25 | Created ConvertedElements component | frontend/src/components/conversion/ConvertedElements.tsx |
| 2026-01-25 | Created AttentionItems component | frontend/src/components/conversion/AttentionItems.tsx |
| 2026-01-25 | Created ConversionSummary page | frontend/src/pages/ConversionSummary.tsx |
| 2026-01-25 | Added summary route | frontend/src/main.tsx |
| 2026-01-25 | Created unit tests | tests/test_conversion_summary.py |

### File List

**New Files:**
- `frontend/src/components/conversion/SummaryCard.tsx` - Summary header with status badge
- `frontend/src/components/conversion/ConvertedElements.tsx` - Shows converted element counts
- `frontend/src/components/conversion/AttentionItems.tsx` - Shows items needing attention
- `frontend/src/pages/ConversionSummary.tsx` - Full summary page
- `tests/test_conversion_summary.py` - 21 unit tests for summary schemas

**Modified Files:**
- `app/schemas/conversion.py` - Added 10 summary schemas
- `app/api/routes/conversion.py` - Added summary endpoint and _build_conversion_summary helper
- `frontend/src/hooks/useConversion.ts` - Added summary types and useConversionSummary hook
- `frontend/src/components/conversion/index.ts` - Added component exports
- `frontend/src/main.tsx` - Added route for ConversionSummary page

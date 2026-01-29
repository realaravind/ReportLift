# Story 3.2: Report List Display

Status: done

## Story

As a **user**,
I want **to see the list of reports in a selected folder**,
so that **I can choose which report to analyze and convert**.

## Acceptance Criteria

### AC1: Report List Display
**Given** the user selects a folder in the tree
**When** the folder is selected
**Then** the right panel displays a list of reports in that folder
**And** each report shows: Name, Description (truncated), Modified Date, Size
**And** reports are sorted alphabetically by name (default)

### AC2: Report Row Interaction
**Given** the report list is displayed
**When** viewing report entries
**Then** each row is clickable/selectable
**And** a visual indicator shows the selected report (if any)
**And** only reports the user has permission to view are shown (FR7)

### AC3: Empty Folder Handling
**Given** a folder contains no reports
**When** viewing the list
**Then** a message is displayed: "No reports in this folder"
**And** subfolders are not shown in the report list (folders are tree-only)

### AC4: Large List Performance
**Given** a folder contains many reports (50+)
**When** scrolling the list
**Then** virtual scrolling is used for performance
**And** a "Showing X of Y reports" count is displayed

### AC5: Client-Side Filtering
**Given** the user wants to find a specific report
**When** they type in the search/filter box
**Then** the list filters to reports matching the search text
**And** filtering is instant (client-side)
**And** search matches against Name and Description

### AC6: Sorting Options
**Given** the report list is displayed
**When** the user clicks a column header
**Then** the list sorts by that column (ascending/descending toggle)
**And** sortable columns include: Name, Modified Date, Size

### AC7: Error Handling
**Given** the report list fetch fails
**When** an error occurs
**Then** an error message is displayed: "Unable to load reports"
**And** the specific error from SSRS is shown
**And** a "Retry" option is available

## Tasks / Subtasks

- [x] **Task 1: Backend - Report List API Endpoint** (AC: 1, 2, 7)
  - [x] Create `GET /api/v1/ssrs/reports?path=` endpoint (query param for path)
  - [x] Fetch reports from SSRS for the specified folder path
  - [x] Pass user's AD identity for permission filtering
  - [x] Return report metadata: name, description, modified_date, size
  - [x] Implement proper error handling with structured responses

- [x] **Task 2: Backend - SSRS Client Reports Method** (AC: 1, 2)
  - [x] Add `list_ssrs_reports()` to `ssrs_service.py`
  - [x] Parse SSRS response to extract report properties
  - [x] Filter to only include Report type items (exclude folders, data sources)
  - [x] Handle reports with missing metadata gracefully

- [x] **Task 3: Frontend - Report List Component** (AC: 1, 2, 3)
  - [x] Create `components/ssrs/ReportList.tsx` component
  - [x] Custom table-like display with clickable rows
  - [x] Implement row selection with visual highlight (primary color)
  - [x] Display truncated descriptions
  - [x] Format dates in user-friendly format (Month Day, Year)
  - [x] Format sizes in human-readable format (KB, MB)

- [x] **Task 4: Frontend - React Query Integration** (AC: 1, 7)
  - [x] Create `useReportList` hook using React Query
  - [x] Configure query key: `['ssrs', 'reports', folderPath]`
  - [x] Implement loading state with spinner
  - [x] Implement error state with retry button
  - [x] Cache results for quick folder switching (5 min staleTime)

- [x] **Task 5: Frontend - Empty State** (AC: 3)
  - [x] Create empty state with FileText icon
  - [x] Display "No Reports Found" message
  - [x] Separate "No Matching Reports" for filtered empty state

- [x] **Task 6: Frontend - Virtual Scrolling** (AC: 4)
  - [x] Implement custom virtual scrolling with position: absolute technique
  - [x] Configure ROW_HEIGHT (64px) and OVERSCAN (5 rows)
  - [x] Add "X of Y reports" counter in header
  - [x] Uses ResizeObserver for container height tracking

- [x] **Task 7: Frontend - Search/Filter** (AC: 5)
  - [x] Add search input above the table
  - [x] Implement instant client-side filtering
  - [x] Filter on name and description fields
  - [x] Clear search button when no results

- [x] **Task 8: Frontend - Column Sorting** (AC: 6)
  - [x] Make column headers clickable
  - [x] Implement sort state management
  - [x] Add sort direction indicators (ArrowUp/ArrowDown/ArrowUpDown)
  - [x] Default sort: Name ascending

- [x] **Task 9: Integration Testing** (AC: 1-7)
  - [x] Backend tests pass (67 tests)
  - [x] Frontend lint passes
  - [x] Frontend build succeeds
  - [x] All acceptance criteria verified

## Dev Notes

### Technology Requirements

| Component | Technology | Notes |
|-----------|------------|-------|
| Table Component | shadcn/ui Table | With DataTable pattern |
| Virtual Scrolling | @tanstack/react-virtual | For large lists (50+ items) |
| Data Fetching | React Query | Caching, background refresh |
| State Management | Zustand | For selected report state |
| Date Formatting | date-fns | For relative/absolute dates |

### API Response Format

**Success Response:**
```json
{
  "data": [
    {
      "id": "report-uuid-1",
      "name": "Monthly Sales Report",
      "path": "/Sales Reports/Monthly Sales Report",
      "description": "Shows monthly sales performance by region and product category with trend analysis",
      "modified_date": "2026-01-15T14:30:00Z",
      "size_bytes": 245760,
      "created_by": "DOMAIN\\jsmith"
    },
    {
      "id": "report-uuid-2",
      "name": "Quarterly Financial Summary",
      "path": "/Sales Reports/Quarterly Financial Summary",
      "description": null,
      "modified_date": "2026-01-10T09:15:00Z",
      "size_bytes": 512000,
      "created_by": "DOMAIN\\aadmin"
    }
  ],
  "meta": {
    "timestamp": "2026-01-21T10:30:00Z",
    "total_count": 2,
    "folder_path": "/Sales Reports"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "SSRS_FOLDER_NOT_FOUND",
    "message": "The specified folder does not exist or you do not have permission to view it",
    "details": {
      "path": "/Restricted Folder",
      "ssrs_error": "rsItemNotFound"
    }
  }
}
```

### Frontend Component Structure

```typescript
// components/ssrs/ReportList.tsx
interface Report {
  id: string;
  name: string;
  path: string;
  description: string | null;
  modifiedDate: string;
  sizeBytes: number;
  createdBy: string;
}

interface ReportListProps {
  folderPath: string;
  onReportSelect: (report: Report) => void;
  selectedReportId?: string;
}

// hooks/useReportList.ts
export function useReportList(folderPath: string) {
  return useQuery({
    queryKey: ['reports', 'list', folderPath],
    queryFn: () => api.get(`/ssrs/folders/${encodeURIComponent(folderPath)}/reports`),
    enabled: !!folderPath,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### Table Column Configuration

| Column | Width | Sortable | Notes |
|--------|-------|----------|-------|
| Name | flex-1 (min 200px) | Yes | Primary column, bold text |
| Description | 300px | No | Truncated with ellipsis, tooltip |
| Modified | 150px | Yes | Relative format (e.g., "2 days ago") |
| Size | 100px | Yes | Human-readable (e.g., "240 KB") |

### Virtual Scrolling Configuration

```typescript
// For folders with 50+ reports
const rowVirtualizer = useVirtualizer({
  count: filteredReports.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 48, // row height in pixels
  overscan: 10, // render extra rows for smooth scrolling
});
```

### Performance Considerations

- **Caching:** React Query caches report lists per folder
- **Virtual Scrolling:** Only renders visible rows for large lists
- **Client-Side Filter:** No server round-trip for filtering
- **Debounce:** Search input debounced to avoid excessive filtering

### Dependencies

- Story 3.1: SSRS Folder Tree Navigation (provides folder selection)
- Story 1.3: Windows AD Authentication (user identity for permissions)
- Story 2.2: SSRS Connection Configuration (SSRS URL)

### Functional Requirements Covered

- **FR6:** View list of reports available in a selected SSRS folder
- **FR7:** Respect SSRS permissions (user sees only permitted reports)

### Non-Functional Requirements

- **NFR28:** Report list retrieved within 5 seconds
- **NFR7:** Windows Integrated Authentication

### UI/UX Considerations

- Selected row should have a distinct background color (primary-100 or similar)
- Hover state on rows to indicate interactivity
- Empty state should be friendly, not alarming
- Loading skeleton should match final table structure
- Filter input should have a clear/reset button

### References

- [Source: architecture.md#Frontend Organization] - Component structure
- [Source: architecture.md#State Management Patterns] - React Query keys
- [Source: epics.md#Story 3.2] - Original story requirements

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Used query parameter `?path=` instead of path parameter for reports endpoint (matches folders endpoint pattern)
- Implemented custom virtual scrolling instead of @tanstack/react-virtual (simpler, no extra dependency)
- ReportList uses custom table-like layout rather than shadcn Table for better virtual scrolling integration
- App.tsx updated to include ReportList in a two-panel layout (report list + details)
- SplitPanel updated to pass onFolderSelect callback to Sidebar
- SearchHeader is a separate internal component for cleaner code organization
- ReportRow component handles keyboard accessibility (Enter/Space key support)

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Initial implementation | All files below |

### File List
- `backend/app/services/ssrs_service.py` - Added SSRSReport, SSRSReportsResult, list_ssrs_reports()
- `backend/app/api/routes/ssrs.py` - Added /reports endpoint with ReportItem, ReportsMeta schemas
- `frontend/src/hooks/useReportList.ts` - New React Query hook for reports
- `frontend/src/components/ssrs/ReportList.tsx` - New report list component with virtual scrolling
- `frontend/src/components/layout/SplitPanel.tsx` - Updated to pass onFolderSelect prop
- `frontend/src/App.tsx` - Updated with ReportList integration and two-panel layout

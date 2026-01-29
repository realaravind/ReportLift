# Story 3.1: SSRS Folder Tree Navigation

Status: done

## Story

As a **user**,
I want **to browse the SSRS Report Server folder structure in a tree view**,
so that **I can navigate to the reports I need to convert**.

## Acceptance Criteria

### AC1: Folder Tree Display
**Given** the user is authenticated and SSRS is configured
**When** they view the main application
**Then** the left panel displays the SSRS folder tree starting at the root "/"
**And** folders are displayed with folder icons
**And** the tree loads within 5 seconds (NFR28)

### AC2: Folder Expand/Collapse
**Given** the folder tree is displayed
**When** the user clicks a folder with subfolders
**Then** the folder expands to show child folders
**And** a loading indicator is shown while fetching children
**And** the expanded state is maintained during the session

### AC3: Leaf Folder Selection
**Given** a folder has no subfolders
**When** the user clicks it
**Then** it is selected (highlighted)
**And** no expand/collapse indicator is shown

### AC4: Permission-Aware Browsing
**Given** the user's AD identity
**When** fetching folder contents
**Then** only folders the user has permission to see are displayed (FR7)
**And** hidden/restricted folders are not shown

### AC5: Error Handling
**Given** the folder fetch fails
**When** an error occurs
**Then** an error message is displayed inline: "Unable to load folders"
**And** a "Retry" option is available

### AC6: Unconfigured State
**Given** the SSRS connection is not configured
**When** viewing the folder tree area
**Then** a message is displayed: "SSRS not configured"
**And** a link to Settings is provided

## Tasks / Subtasks

- [x] **Task 1: Backend - SSRS Folder API Endpoint** (AC: 1, 2, 4)
  - [x] Create `GET /api/v1/ssrs/folders?path=/` endpoint with query param for path
  - [x] Implement folder listing via SSRS REST API (v2.0)
  - [x] Pass user's AD identity through for permission filtering (requests-ntlm)
  - [x] Return structured response: `{ data: [...], meta: {...} }`
  - [x] Handle SSRS connection errors with structured error responses

- [x] **Task 2: Backend - SSRS Client Service** (AC: 1, 2, 4)
  - [x] Added `list_ssrs_folders()` function to `services/ssrs_service.py`
  - [x] Implemented SSRSFolder and SSRSFoldersResult dataclasses
  - [x] Configure requests-ntlm for Windows authentication
  - [x] Add timeout handling (10 seconds default)

- [x] **Task 3: Frontend - Folder Tree Component** (AC: 1, 2, 3)
  - [x] Create `components/ssrs/FolderTree.tsx` component
  - [x] Implement recursive FolderNode with expand/collapse
  - [x] Add folder icons (Lucide Folder/FolderOpen icons)
  - [x] Implement selection highlighting with primary color
  - [x] Use React Query for data fetching with lazy loading on expand
  - [x] Store expanded state in local component state (Set)

- [x] **Task 4: Frontend - Loading and Error States** (AC: 5)
  - [x] Add loading spinner for folder expansion (Loader2)
  - [x] Implement error display with "Retry" button
  - [x] Add loading state for initial tree load

- [x] **Task 5: Frontend - Unconfigured State Handling** (AC: 6)
  - [x] Check SSRS connection status from health store and folder query
  - [x] Display "SSRS Not Configured" message in Sidebar
  - [x] Add "Go to Settings" button to navigate to Settings page
  - [x] Use `useSSRSFolders` and `useHealthStore` hooks

- [x] **Task 6: Integration Testing** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Backend tests pass (67 tests)
  - [x] Frontend lint and build pass
  - [x] All acceptance criteria verified

## Dev Notes

### Technology Requirements

| Component | Technology | Notes |
|-----------|------------|-------|
| SSRS Authentication | requests-ntlm | Pass user's Windows identity to SSRS |
| Tree Component | Custom React or react-arborist | Virtual rendering for large trees |
| State Management | React Query | For server state + caching |
| UI Components | shadcn/ui | TreeView pattern with custom styling |
| Icons | Lucide React | `Folder`, `FolderOpen`, `ChevronRight` |

### SSRS API Integration

**SSRS REST API (2017+):**
```
GET {ssrs_url}/api/v2.0/Folders
GET {ssrs_url}/api/v2.0/Folders(Path='/FolderName')
```

**SSRS SOAP (Legacy):**
```
ReportingService2010.asmx
ListChildren(path, recursive=false)
```

**Backend Implementation Pattern:**
```python
# services/ssrs_client.py
from requests_ntlm import HttpNtlmAuth

class SSRSClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def list_folders(self, path: str, username: str, password: str) -> list[dict]:
        """List folders at the given path using user's AD credentials."""
        auth = HttpNtlmAuth(username, password)
        response = requests.get(
            f"{self.base_url}/api/v2.0/CatalogItems",
            auth=auth,
            params={"$filter": f"Path eq '{path}' and Type eq 'Folder'"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()["value"]
```

### Frontend Component Structure

```typescript
// components/ssrs/FolderTree.tsx
interface FolderNode {
  name: string;
  path: string;
  hasChildren: boolean;
}

interface FolderTreeProps {
  onFolderSelect: (path: string) => void;
}
```

### API Response Format

**Success Response:**
```json
{
  "data": [
    {
      "name": "Sales Reports",
      "path": "/Sales Reports",
      "has_children": true
    },
    {
      "name": "Finance",
      "path": "/Finance",
      "has_children": false
    }
  ],
  "meta": {
    "timestamp": "2026-01-21T10:30:00Z",
    "total_count": 2
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "SSRS_CONNECTION_FAILED",
    "message": "Unable to connect to SSRS server",
    "details": {
      "url": "http://ssrs.company.com/reportserver",
      "status_code": 401
    }
  }
}
```

### Performance Considerations

- **Lazy Loading:** Only fetch children when folder is expanded
- **Virtual Scrolling:** Use virtualization for folders with 100+ items
- **Caching:** React Query caches folder data, invalidate on explicit refresh
- **5-Second Target:** NFR28 requires report list within 5 seconds

### Dependencies

- Story 1.1: Project initialization (backend/frontend structure)
- Story 1.3: Windows AD Authentication (user identity for pass-through)
- Story 2.2: SSRS Connection Configuration (SSRS URL and settings)
- Story 2.3: SSRS Connection Test (verified connectivity)

### Functional Requirements Covered

- **FR5:** Browse SSRS Report Server folder structure
- **FR7:** Respect SSRS permissions (user sees only permitted folders)

### Non-Functional Requirements

- **NFR28:** Report list retrieved within 5 seconds
- **NFR7:** Windows Integrated Authentication for SSRS connection

### References

- [Source: architecture.md#SSRS Client] - requests-ntlm integration
- [Source: architecture.md#Frontend Organization] - Component structure
- [Source: epics.md#Story 3.1] - Original story requirements

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Added `list_ssrs_folders()` to existing ssrs_service.py instead of creating separate client
- Created new SSRS router with `/api/v1/ssrs/folders` endpoint
- FolderTree component uses recursive FolderNode pattern with lazy loading
- Each folder expansion triggers a new React Query fetch
- Expanded state stored in Set for O(1) lookup
- Sidebar integrates health store to check SSRS configuration status
- Unconfigured state shows "Go to Settings" button with navigation
- Connection status indicator at bottom of sidebar

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Initial implementation | All files below |

### File List
- `backend/app/services/ssrs_service.py` - Added SSRSFolder, SSRSFoldersResult, list_ssrs_folders()
- `backend/app/api/routes/ssrs.py` - New SSRS router with folders endpoint
- `backend/app/api/routes/__init__.py` - Export ssrs_router
- `backend/app/main.py` - Register SSRS router
- `frontend/src/hooks/useSSRSFolders.ts` - New React Query hook for folders
- `frontend/src/components/ssrs/FolderTree.tsx` - New FolderTree component
- `frontend/src/components/layout/Sidebar.tsx` - Updated with FolderTree integration

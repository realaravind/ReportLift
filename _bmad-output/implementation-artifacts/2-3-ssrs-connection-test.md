# Story 2.3: SSRS Connection Test

Status: done

## Story

As an **admin**,
I want **to test the SSRS connection before users start working**,
so that **I can verify the configuration is correct**.

## Acceptance Criteria

### AC1: Test Connection Button
**Given** SSRS configuration has been saved
**When** the admin clicks "Test Connection"
**Then** the system attempts to authenticate to the Report Server
**And** a loading indicator is displayed during the test
**And** the test completes within 10 seconds (timeout)

### AC2: Connection Success
**Given** the connection test succeeds
**When** results are displayed
**Then** a success message shows: "Connected to SSRS successfully"
**And** the Report Server version is displayed (if available)
**And** the status indicator turns green

### AC3: Connection Failure
**Given** the connection test fails
**When** results are displayed
**Then** an error message shows the failure reason
**And** common issues are suggested (e.g., "Check URL", "Verify credentials", "Check network access")
**And** the status indicator turns red

### AC4: AD Pass-Through Test
**Given** the current user's AD identity
**When** testing SSRS connection
**Then** the test uses the AD pass-through identity (from Story 1.3)
**And** confirms the user has at least read access to the root folder

### AC5: Disabled State
**Given** SSRS is not configured
**When** viewing the SSRS tab
**Then** the "Test Connection" button is disabled
**And** a tooltip shows: "Configure SSRS settings first"

## Tasks / Subtasks

- [x] **Task 1: Create Test Connection UI Component** (AC: 1, 2, 3, 5)
  - [x] Test Connection button uses existing TestConnectionButton component
  - [x] Implement loading state with spinner during test
  - [x] Created ConnectionTestResult component for status display
  - [x] Display test results in alert panel with green/red indicators
  - [x] Disable button when no configuration exists (with tooltip)

- [x] **Task 2: Implement Connection Test Results Display** (AC: 2, 3)
  - [x] Created `ConnectionTestResult` component with Alert UI
  - [x] Show success state: green checkmark, success message, server version
  - [x] Show failure state: red X, error message, troubleshooting suggestions
  - [x] Include timestamp of last test
  - [x] Test Again via same button

- [x] **Task 3: Create Backend Test Endpoint** (AC: 1, 4)
  - [x] Created `POST /api/v1/settings/ssrs/test` endpoint
  - [x] Implement 10-second timeout for connection attempt
  - [x] Extract current user's AD identity from JWT token
  - [x] Return structured test result with status, message, details

- [x] **Task 4: Implement SSRS Connection Logic** (AC: 1, 4)
  - [x] Created `backend/app/services/ssrs_service.py`
  - [x] Implemented `test_ssrs_connection()` function
  - [x] Use `requests-ntlm` for Windows authentication
  - [x] Attempt to fetch SSRS REST API root folders endpoint
  - [x] Extract Report Server version from response headers if available

- [x] **Task 5: Implement Error Handling and Suggestions** (AC: 3)
  - [x] Created error categorization logic with SSRSErrorCode enum
  - [x] Map HTTP status codes to user-friendly messages
  - [x] Map common exceptions to troubleshooting suggestions:
    - Connection refused: "Check that the Report Server URL is correct"
    - 401 Unauthorized: "Your Windows credentials could not authenticate"
    - 404 Not Found: "Report Server not found at the specified URL"
    - Timeout: "Connection timed out - check network connectivity"
    - SSL Error: "SSL certificate error"

- [x] **Task 6: Create Frontend API Integration** (AC: 1, 2, 3)
  - [x] Added `useTestSSRSConnection` mutation hook to useSSRSSettings.ts
  - [x] Created SSRSTestResult and SSRSTestResultDetails interfaces
  - [x] Handle loading, success, and error states
  - [x] Store last test result in component state

- [x] **Task 7: Verify All Acceptance Criteria**
  - [x] Test button shows loading state during test
  - [x] Successful connection shows green status with message
  - [x] Failed connection shows red status with suggestions
  - [x] Test uses current user's AD identity (or service account if configured)
  - [x] Disabled state when not configured with tooltip

## Dev Notes

### Technical Requirements

**Test Result Schema:**
```typescript
interface SSRSTestResult {
  success: boolean;
  message: string;
  details: {
    server_version?: string;
    response_time_ms: number;
    root_folder_accessible: boolean;
    error_code?: string;
  };
  suggestions?: string[];
  tested_at: string;
}
```

**Backend Test Endpoint:**
```python
@router.post("/ssrs/test")
async def test_ssrs_connection(
    current_user: User = Depends(get_current_user)
) -> SSRSTestResult:
    """
    Test SSRS connection using current user's AD identity.
    Timeout: 10 seconds
    """
    pass
```

**SSRS API Interaction:**
- Use SSRS REST API endpoint: `{base_url}/api/v2.0/Folders`
- Authentication: NTLM with user's AD credentials
- Expected response for success: HTTP 200 with folder listing
- Extract `X-SSRS-Version` header if present

**Error Categories:**
| Error Type | User Message | Suggestions |
|------------|--------------|-------------|
| ConnectionError | "Unable to connect to server" | "Check URL", "Verify server is running" |
| Timeout | "Connection timed out" | "Check network", "Try again" |
| 401 | "Authentication failed" | "Verify Windows credentials", "Check SSRS permissions" |
| 404 | "Report Server not found" | "Verify URL path" |
| SSL | "Certificate error" | "Verify SSL certificate" |

### AD Pass-Through Implementation
- Current user's AD identity stored in JWT from login (Story 1.3)
- Backend extracts `domain\username` from token
- SSRS connection uses this identity via NTLM
- Test confirms user can access root folder

### UI States
1. **No Configuration**: Button disabled, tooltip explains
2. **Ready**: Button enabled, no previous result shown
3. **Testing**: Button disabled, spinner shown
4. **Success**: Green indicator, success message, version info
5. **Failure**: Red indicator, error message, suggestions list

### Dependencies
- Requires Story 2.2 (SSRS Connection Configuration) - settings to test
- Requires Story 1.3 (Windows AD Authentication) - user identity

### Architecture References
- [Source: epics.md#Story 2.3] - Story definition
- FR3: Test SSRS connection and verify authentication
- NFR11: Clear error messages when connections fail
- ARCH19: requests-ntlm for authentication

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created ssrs_service.py with test_ssrs_connection function
- Uses requests-ntlm for NTLM authentication to SSRS
- SSRSErrorCode enum for categorizing errors
- ERROR_SUGGESTIONS mapping for troubleshooting guidance
- Created SSRSTestResultResponse and SSRSTestResultDetails schemas
- Added POST /api/v1/settings/ssrs/test endpoint
- Added useTestSSRSConnection mutation hook
- Updated SSRSSettings.tsx with ConnectionTestResult component
- Test button disabled when not configured (with tooltip)
- 67 backend tests passing
- Frontend lint and build passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created SSRS service | backend/app/services/ssrs_service.py |
| 2026-01-22 | Updated settings schemas | backend/app/schemas/settings.py |
| 2026-01-22 | Updated schemas __init__ | backend/app/schemas/__init__.py |
| 2026-01-22 | Updated settings routes with test endpoint | backend/app/api/routes/settings.py |
| 2026-01-22 | Updated SSRS settings hooks | frontend/src/hooks/useSSRSSettings.ts |
| 2026-01-22 | Updated SSRS settings component | frontend/src/components/settings/SSRSSettings.tsx |

### File List
**Backend:**
- backend/app/services/ssrs_service.py (new)
- backend/app/schemas/settings.py (updated)
- backend/app/schemas/__init__.py (updated)
- backend/app/api/routes/settings.py (updated)

**Frontend:**
- frontend/src/hooks/useSSRSSettings.ts (updated)
- frontend/src/components/settings/SSRSSettings.tsx (updated)

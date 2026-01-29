# Story 2.5: Snowflake Connection Test

Status: done

## Story

As an **admin**,
I want **to test the Snowflake connection**,
so that **I can verify the database is accessible before conversion begins**.

## Acceptance Criteria

### AC1: Test Connection Button
**Given** Snowflake configuration has been saved
**When** the admin clicks "Test Connection"
**Then** the system attempts to connect to Snowflake
**And** a loading indicator is displayed
**And** the test completes within 15 seconds (timeout)

### AC2: OAuth Token Usage
**Given** OAuth authentication is configured
**When** testing connection
**Then** the stored OAuth tokens are used
**And** if tokens expired, the user is prompted to re-authorize

### AC3: Connection Success
**Given** the connection test succeeds
**When** results are displayed
**Then** a success message shows: "Connected to Snowflake successfully"
**And** displays: Account, Warehouse, Database, Schema, Role
**And** the status indicator turns green

### AC4: Connection Failure
**Given** the connection test fails
**When** results are displayed
**Then** the error message includes Snowflake error code/message
**And** suggestions for common issues are displayed
**And** the status indicator turns red

### AC5: Resource Not Found Errors
**Given** the warehouse or database doesn't exist
**When** the test runs
**Then** specific error: "Warehouse 'X' not found" or "Database 'Y' not found"

### AC6: Disabled State
**Given** Snowflake is not configured
**When** viewing the Snowflake tab
**Then** the "Test Connection" button is disabled
**And** a tooltip shows: "Configure Snowflake settings first"

## Tasks / Subtasks

- [x] **Task 1: Create Test Connection UI Component** (AC: 1, 3, 4, 6)
  - [x] Add "Test Connection" button using existing TestConnectionButton component
  - [x] Implement loading state with spinner during test
  - [x] Display test results via SnowflakeConnectionTestResult component
  - [x] Disable button when no configuration exists (with tooltip)

- [x] **Task 2: Implement Connection Test Results Display** (AC: 3, 4, 5)
  - [x] Create `SnowflakeConnectionTestResult` component
  - [x] Show success: green checkmark, user, role, warehouse, database, schema
  - [x] Show failure: red X, error message, suggestions list
  - [x] Show re-auth required: amber indicator, prompt to re-authorize
  - [x] Include response time in milliseconds

- [x] **Task 3: Create Backend Test Endpoint** (AC: 1, 2)
  - [x] Create `POST /api/v1/settings/snowflake/test` endpoint
  - [x] Implement 15-second timeout for connection attempt
  - [x] Handle OAuth token retrieval via OAuthService.get_valid_token()
  - [x] Return structured test result with full details

- [x] **Task 4: Implement Snowflake Connection Logic** (AC: 1, 3, 5)
  - [x] Create `backend/app/services/snowflake_service.py`
  - [x] Implement `test_snowflake_connection()` function
  - [x] Use `snowflake-connector-python` library
  - [x] Execute test query to get CURRENT_USER, ROLE, WAREHOUSE, DATABASE, SCHEMA, ACCOUNT
  - [x] Support both OAuth and basic authentication

- [x] **Task 5: Implement OAuth Token Handling** (AC: 2)
  - [x] Get valid token via OAuthService.get_valid_token() (handles refresh)
  - [x] If token retrieval fails, return requires_reauth: true
  - [x] Frontend shows amber indicator with re-auth prompt

- [x] **Task 6: Implement Error Handling and Suggestions** (AC: 4, 5)
  - [x] Created SnowflakeErrorCode enum for error categorization
  - [x] Map Snowflake SQL error codes to our error codes
  - [x] ERROR_MESSAGES mapping for user-friendly messages
  - [x] ERROR_SUGGESTIONS mapping for troubleshooting guidance
  - [x] Detect specific errors: auth, account, warehouse, database, schema, timeout

- [x] **Task 7: Create Frontend API Integration** (AC: 1, 2, 3, 4)
  - [x] Created SnowflakeTestResult and SnowflakeTestResultDetails interfaces
  - [x] Created `useTestSnowflakeConnection` mutation hook
  - [x] Store last test result in component state
  - [x] Clear test result when settings are saved

- [x] **Task 8: Verify All Acceptance Criteria**
  - [x] Test button shows loading state via TestConnectionButton
  - [x] Successful connection shows all details (user, role, warehouse, database, schema)
  - [x] Failed connection shows error code and suggestions
  - [x] OAuth re-auth required shows amber indicator
  - [x] Disabled state when not configured with tooltip

## Dev Notes

### Technical Requirements

**Test Result Schema:**
```typescript
interface SnowflakeTestResult {
  success: boolean;
  message: string;
  details: {
    account: string;
    warehouse: string;
    database: string;
    schema: string;
    role: string;
    user: string;
    response_time_ms: number;
    error_code?: string;
  };
  suggestions?: string[];
  requires_reauth?: boolean;
  tested_at: string;
}
```

**Backend Test Endpoint:**
```python
@router.post("/snowflake/test")
async def test_snowflake_connection() -> SnowflakeTestResult:
    """
    Test Snowflake connection using stored configuration.
    Timeout: 15 seconds
    Handles OAuth token refresh automatically.
    """
    pass
```

**Snowflake Connection Code:**
```python
import snowflake.connector

def test_connection(config: SnowflakeConfig) -> TestResult:
    conn = snowflake.connector.connect(
        account=config.account_identifier,
        warehouse=config.warehouse,
        database=config.database,
        schema=config.schema,
        # OAuth or basic auth params
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT CURRENT_USER(), CURRENT_ROLE(),
               CURRENT_WAREHOUSE(), CURRENT_DATABASE(),
               CURRENT_SCHEMA()
    """)
    result = cursor.fetchone()
    return TestResult(
        user=result[0],
        role=result[1],
        warehouse=result[2],
        database=result[3],
        schema=result[4]
    )
```

**Common Snowflake Error Codes:**
| Code | Meaning | Suggestion |
|------|---------|------------|
| 250001 | Authentication failed | Check credentials or re-authorize OAuth |
| 390100 | Account not found | Verify Account Identifier |
| 390201 | Warehouse not found | Check warehouse name and permissions |
| 390202 | Database not found | Check database name and permissions |
| 390203 | Schema not found | Check schema name and permissions |
| 390318 | Role not authorized | User lacks permission for role |

### OAuth Token Refresh Flow
1. Check if access_token exists and is not expired
2. If expired, attempt refresh using refresh_token
3. If refresh succeeds, update stored tokens
4. If refresh fails, return `requires_reauth: true`
5. Frontend shows "Re-authorize" button instead of error

### UI States
1. **No Configuration**: Button disabled, tooltip explains
2. **Ready**: Button enabled, no previous result
3. **Testing**: Button disabled, spinner with "Testing connection..."
4. **Success**: Green indicator, full connection details table
5. **Failure**: Red indicator, error code, message, suggestions
6. **Re-auth Required**: Orange indicator, "Re-authorize" button

### Dependencies
- Requires Story 2.4 (Snowflake Connection Configuration) - settings to test
- Requires Story 1.5 (OAuth2/PKCE Infrastructure) - token management
- Requires `snowflake-connector-python` package

### Architecture References
- [Source: epics.md#Story 2.5] - Story definition
- FR4: Test Snowflake connection and verify authentication
- NFR11: Clear error messages when connections fail

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Added snowflake-connector-python>=3.6.0 to requirements.txt
- Created snowflake_service.py with test_snowflake_connection function
- SnowflakeErrorCode enum for error categorization
- ERROR_MESSAGES and ERROR_SUGGESTIONS mappings for troubleshooting
- Created SnowflakeTestResultDetails and SnowflakeTestResultResponse schemas
- Added POST /api/v1/settings/snowflake/test endpoint
- Endpoint handles both OAuth and basic authentication
- OAuth tokens retrieved via OAuthService.get_valid_token()
- Created useTestSnowflakeConnection mutation hook
- Created SnowflakeConnectionTestResult component for result display
- Test result shows user, role, warehouse, database, schema, response time
- Re-auth required state shown with amber indicator
- 67 backend tests passing
- Frontend lint and build passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Added Snowflake connector dependency | backend/requirements.txt |
| 2026-01-21 | Created Snowflake service | backend/app/services/snowflake_service.py |
| 2026-01-21 | Added test result schemas | backend/app/schemas/settings.py |
| 2026-01-21 | Updated schemas __init__ | backend/app/schemas/__init__.py |
| 2026-01-21 | Added test endpoint | backend/app/api/routes/settings.py |
| 2026-01-21 | Added test hook and types | frontend/src/hooks/useSnowflakeSettings.ts |
| 2026-01-21 | Added test UI to Snowflake settings | frontend/src/components/settings/SnowflakeSettings.tsx |

### File List
**Backend:**
- backend/requirements.txt (updated)
- backend/app/services/snowflake_service.py (new)
- backend/app/schemas/settings.py (updated)
- backend/app/schemas/__init__.py (updated)
- backend/app/api/routes/settings.py (updated)

**Frontend:**
- frontend/src/hooks/useSnowflakeSettings.ts (updated)
- frontend/src/components/settings/SnowflakeSettings.tsx (updated)

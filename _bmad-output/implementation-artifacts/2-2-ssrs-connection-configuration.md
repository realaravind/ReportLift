# Story 2.2: SSRS Connection Configuration

Status: done

## Story

As an **admin**,
I want **to configure the SSRS Report Server connection details**,
so that **users can browse and analyze reports from our SSRS instance**.

## Acceptance Criteria

### AC1: SSRS Configuration Form Display
**Given** the admin is on the Settings page, SSRS tab
**When** viewing the configuration form
**Then** the following fields are displayed:
  - Report Server URL (required, text input)
  - Authentication Method (dropdown: Windows Integrated)
  - Service Account Username (optional, for scheduled operations)
  - Service Account Password (optional, masked input)

### AC2: Save Configuration
**Given** the admin enters SSRS configuration
**When** they click "Save"
**Then** the configuration is validated (URL format check)
**And** credentials are encrypted before storage
**And** success message: "SSRS configuration saved"

### AC3: URL Validation
**Given** an invalid URL format is entered
**When** validation runs
**Then** an error is displayed: "Invalid Report Server URL format"
**And** the form is not submitted

### AC4: View Existing Configuration
**Given** the SSRS configuration exists
**When** viewing the settings page
**Then** the URL is displayed
**And** passwords are masked as "••••••••"
**And** a "Clear Credentials" option is available

### AC5: Clear Credentials
**Given** credentials are configured
**When** the admin clicks "Clear Credentials"
**Then** a confirmation dialog appears
**And** confirming removes stored credentials
**And** the password field becomes empty

## Tasks / Subtasks

- [x] **Task 1: Create SSRS Settings Form Component** (AC: 1, 4)
  - [x] Implement `SSRSSettings.tsx` with form fields
  - [x] Add Report Server URL input with placeholder "https://reportserver/ReportServer"
  - [x] Add Authentication Method dropdown (Windows Integrated as only option for MVP)
  - [x] Add Service Account Username input (optional)
  - [x] Add Service Account Password input with masked display
  - [x] Display current values when configuration exists

- [x] **Task 2: Implement Form Validation** (AC: 3)
  - [x] Add URL format validation (must be valid HTTP/HTTPS URL)
  - [x] Add required field validation for Report Server URL
  - [x] Display inline validation errors below fields
  - [x] Disable Save button when form has validation errors
  - [x] Use react-hook-form with zod schema validation

- [x] **Task 3: Create Backend SSRS Configuration Model** (AC: 2)
  - [x] Uses existing `ConnectionConfig` model (stores service configs as encrypted JSON)
  - [x] Fields stored in JSON: report_server_url, auth_method, service_account_username, password
  - [x] Singleton pattern via service_type='ssrs' unique constraint
  - [x] Note: Existing ConnectionConfig model suffices; no separate SSRS model needed

- [x] **Task 4: Create Backend SSRS API Endpoints** (AC: 2, 4, 5)
  - [x] Updated `GET /api/v1/settings/ssrs` - returns current config (masked)
  - [x] Created `PUT /api/v1/settings/ssrs` - updates configuration
  - [x] Created `DELETE /api/v1/settings/ssrs/credentials` - clears credentials
  - [x] Created Pydantic schemas (SSRSSettingsUpdateRequest)
  - [x] Implemented URL format validation on backend

- [x] **Task 5: Implement Credential Encryption** (AC: 2)
  - [x] Uses existing `credential_store.py` with Fernet encryption
  - [x] Uses existing `connection_config_service.py` for encrypted storage
  - [x] Password field encrypted via service's SENSITIVE_FIELDS config
  - [x] ENCRYPTION_KEY validation already in place from Story 1.4

- [x] **Task 6: Implement Clear Credentials Feature** (AC: 5)
  - [x] Added "Clear Credentials" button (only visible when credentials exist)
  - [x] Created confirmation dialog with AlertDialog component
  - [x] DELETE endpoint removes password but preserves other settings
  - [x] Form state updates after successful clear
  - [x] Success toast: "Credentials cleared"

- [x] **Task 7: Connect Frontend to Backend** (AC: 1, 2, 4)
  - [x] Created `frontend/src/hooks/useSSRSSettings.ts` with React Query hooks
  - [x] Implemented `useSSRSSettings` for fetching settings
  - [x] Implemented `useUpdateSSRSSettings` mutation hook
  - [x] Implemented `useClearSSRSCredentials` mutation hook
  - [x] Handle loading and error states in UI

- [x] **Task 8: Verify All Acceptance Criteria**
  - [x] Form displays all required fields
  - [x] URL validation works correctly (frontend zod + backend pydantic)
  - [x] Save encrypts and persists credentials
  - [x] Existing config displays with masked password (has_credentials pattern)
  - [x] Clear credentials works with confirmation dialog

## Dev Notes

### Technical Requirements

**Form Schema (Zod):**
```typescript
const ssrsConfigSchema = z.object({
  report_server_url: z.string()
    .url("Invalid Report Server URL format")
    .regex(/^https?:\/\//, "URL must start with http:// or https://"),
  auth_method: z.enum(["windows_integrated"]),
  service_account_username: z.string().optional(),
  service_account_password: z.string().optional(),
});
```

**API Request/Response:**
```typescript
// GET /api/settings/ssrs response
interface SSRSSettingsResponse {
  report_server_url: string | null;
  auth_method: string;
  service_account_username: string | null;
  has_credentials: boolean;
  updated_at: string | null;
}

// PUT /api/settings/ssrs request
interface UpdateSSRSSettingsRequest {
  report_server_url: string;
  auth_method: string;
  service_account_username?: string;
  service_account_password?: string; // Only sent when updating
}
```

**Database Schema:**
```sql
CREATE TABLE ssrs_config (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1), -- Singleton
    report_server_url VARCHAR(500),
    auth_method VARCHAR(50) DEFAULT 'windows_integrated',
    service_account_username VARCHAR(200),
    encrypted_password TEXT,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Encryption:**
- Use Fernet (symmetric encryption) from `cryptography` library
- Key derived from ENCRYPTION_KEY environment variable
- Encrypted values stored as base64-encoded strings
- See Story 1.4 for encryption infrastructure

### URL Validation Examples
- Valid: `https://reportserver.company.com/ReportServer`
- Valid: `http://localhost/ReportServer`
- Invalid: `reportserver/ReportServer` (no protocol)
- Invalid: `ftp://reportserver/ReportServer` (wrong protocol)

### Dependencies
- Requires Story 2.1 (Admin Settings Page) - tab structure
- Requires Story 1.4 (Secure Credential Storage) - encryption key

### Architecture References
- [Source: epics.md#Story 2.2] - Story definition
- [Source: architecture.md#Credential Storage] - Encryption patterns
- FR1: Configure connection to SSRS Report Server
- FR39: Configure SSRS parameters
- NFR7: Windows Integrated Authentication support

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Updated SSRSSettings.tsx with full form using react-hook-form and zod validation
- Created Select UI component for dropdown
- Added zod, react-hook-form, @hookform/resolvers dependencies
- Updated SaveButton component to support type="submit" for form submission
- Created useSSRSSettings.ts with React Query hooks (useSSRSSettings, useUpdateSSRSSettings, useClearSSRSCredentials)
- Updated backend settings.py schemas with SSRSSettingsUpdateRequest
- Updated backend settings routes with PUT /api/v1/settings/ssrs and DELETE /api/v1/settings/ssrs/credentials
- Uses existing ConnectionConfig model and connection_config_service for encrypted storage
- 68 backend tests passing
- Frontend lint and build passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Updated SSRSSettings form component | frontend/src/components/settings/SSRSSettings.tsx |
| 2026-01-21 | Created Select UI component | frontend/src/components/ui/select.tsx |
| 2026-01-21 | Updated SaveButton to support submit type | frontend/src/components/settings/SaveButton.tsx |
| 2026-01-21 | Created SSRS settings hooks | frontend/src/hooks/useSSRSSettings.ts |
| 2026-01-21 | Updated settings schemas | backend/app/schemas/settings.py |
| 2026-01-21 | Updated settings schemas __init__ | backend/app/schemas/__init__.py |
| 2026-01-21 | Updated settings API routes | backend/app/api/routes/settings.py |

### File List
**Frontend:**
- frontend/src/components/settings/SSRSSettings.tsx (updated)
- frontend/src/components/settings/SaveButton.tsx (updated)
- frontend/src/components/ui/select.tsx (new)
- frontend/src/hooks/useSSRSSettings.ts (new)
- frontend/package.json (updated - added zod, react-hook-form, @hookform/resolvers)

**Backend:**
- backend/app/schemas/settings.py (updated)
- backend/app/schemas/__init__.py (updated)
- backend/app/api/routes/settings.py (updated)

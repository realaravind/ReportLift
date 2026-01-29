# Story 2.1: Admin Settings Page

Status: done

## Story

As an **admin**,
I want **to access a dedicated settings/configuration page with a tabbed interface**,
so that **I can manage all application connections and configurations in one place**.

## Acceptance Criteria

### AC1: Settings Navigation
**Given** the user is authenticated
**When** they click the "Settings" link in the header or navigation
**Then** they are navigated to `/settings`
**And** a tabbed interface is displayed with sections: "SSRS", "Snowflake", "Ollama", "System"

### AC2: Tab Display and State
**Given** the settings page
**When** viewing any tab
**Then** current configuration values are displayed (with sensitive values masked)
**And** a "Test Connection" button is available for each service
**And** a "Save" button persists changes

### AC3: Save Warning
**Given** the user makes configuration changes
**When** they click "Save" without testing
**Then** changes are saved
**And** a warning is displayed: "Configuration saved. Test connection recommended."

### AC4: Tab Persistence
**Given** the user is on a specific tab (e.g., Snowflake)
**When** they navigate away and return to settings
**Then** the previously selected tab is remembered and displayed

### AC5: Unsaved Changes Warning
**Given** the user has made unsaved changes on a tab
**When** they attempt to switch tabs or navigate away
**Then** a confirmation dialog appears: "You have unsaved changes. Discard?"

## Tasks / Subtasks

- [x] **Task 1: Create Settings Page Route and Layout** (AC: 1)
  - [x] Create `frontend/src/pages/Settings.tsx` page component
  - [x] Add `/settings` route to React Router configuration
  - [x] Add "Settings" navigation link to header/sidebar component
  - [x] Implement settings icon (gear) for navigation link

- [x] **Task 2: Implement Tabbed Interface** (AC: 1, 4)
  - [x] Install/configure shadcn/ui Tabs component
  - [x] Create tab structure with four tabs: SSRS, Snowflake, Ollama, System
  - [x] Implement tab state management with URL query parameter (`?tab=ssrs`)
  - [x] Persist selected tab in URL for browser back/forward support

- [x] **Task 3: Create Tab Content Components** (AC: 2)
  - [x] Create `frontend/src/components/settings/SSRSSettings.tsx` placeholder
  - [x] Create `frontend/src/components/settings/SnowflakeSettings.tsx` placeholder
  - [x] Create `frontend/src/components/settings/OllamaSettings.tsx` placeholder
  - [x] Create `frontend/src/components/settings/SystemSettings.tsx` placeholder
  - [x] Each placeholder shows "Configuration coming soon" message

- [x] **Task 4: Implement Common Settings UI Patterns** (AC: 2, 3)
  - [x] Create `frontend/src/components/settings/SettingsCard.tsx` reusable wrapper
  - [x] Create "Test Connection" button component with loading state
  - [x] Create "Save" button component with success/error states
  - [x] Implement toast notifications for save success/warning messages
  - [x] Create masked input component for sensitive values (shows dots, reveals on focus)

- [x] **Task 5: Implement Unsaved Changes Detection** (AC: 5)
  - [x] Create `useUnsavedChanges` hook to track form dirty state
  - [x] Implement `beforeunload` event listener for browser navigation
  - [x] Implement React Router navigation blocker for in-app navigation
  - [x] Create confirmation dialog component using shadcn/ui AlertDialog

- [x] **Task 6: Create Backend Settings API Foundation** (AC: 2, 3)
  - [x] Create `backend/app/api/routes/settings.py` with base router
  - [x] Create `GET /api/settings` endpoint returning all settings (masked)
  - [x] Create `backend/app/schemas/settings.py` with response models
  - [x] Implement credential masking utility function
  - [x] Add settings router to main FastAPI app

- [x] **Task 7: Verify All Acceptance Criteria**
  - [x] Verify navigation to `/settings` works
  - [x] Verify all four tabs display correctly
  - [x] Verify tab switching persists in URL
  - [x] Verify unsaved changes warning appears
  - [x] Verify save warning toast displays

## Dev Notes

### Technical Requirements

**Frontend Components:**
- Use shadcn/ui `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` components
- Use shadcn/ui `Card` for settings sections
- Use shadcn/ui `Button` for actions
- Use shadcn/ui `AlertDialog` for confirmation dialogs
- Use shadcn/ui `Toast` (via sonner) for notifications

**State Management:**
- Use React Query for fetching settings
- Use local component state for form values
- Use Zustand for unsaved changes tracking (if complex)

**API Patterns:**
```typescript
// Settings response structure
interface SettingsResponse {
  ssrs: {
    report_server_url: string | null;
    auth_method: string;
    has_credentials: boolean; // true if credentials exist, never expose actual values
  };
  snowflake: {
    account_identifier: string | null;
    warehouse: string | null;
    database: string | null;
    schema: string | null;
    auth_method: string;
    has_oauth_config: boolean;
  };
  ollama: {
    host_url: string;
    model_name: string;
    enabled: boolean;
    timeout_seconds: number;
  };
}
```

**Credential Masking:**
- Never return actual passwords/secrets from API
- Use `has_credentials: boolean` pattern instead
- Display masked values as "••••••••" in UI
- Clear credentials requires explicit "Clear" button

### URL Structure
- Base: `/settings`
- With tab: `/settings?tab=ssrs`, `/settings?tab=snowflake`, `/settings?tab=ollama`, `/settings?tab=system`

### Styling Guidelines
- Settings page uses full width of content area
- Tab content has consistent padding (p-6)
- Use consistent form layout with labels above inputs
- Error states use red border and text
- Success states use green indicators

### Dependencies
- Requires Story 1.1 (Project Foundation) - base project structure
- Requires Story 1.2 (Split-Panel Explorer) - navigation integration
- Requires Story 1.3 (Authentication) - must be logged in to access

### Architecture References
- [Source: epics.md#Story 2.1] - Story definition
- [Source: architecture.md#Frontend Structure] - Component organization
- [Source: architecture.md#API Response Patterns] - Response structure

### FR/NFR Coverage
- FR38: Admin settings page access

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created Settings page with tabbed interface (SSRS, Snowflake, Ollama, System)
- Tab state persists in URL via query parameter (?tab=ssrs)
- Settings navigation accessible via gear icon in Header (highlights when active)
- Created BaseLayout component for pages without SSRS sidebar
- Installed and configured shadcn/ui Tabs, Card, AlertDialog components
- Installed sonner for toast notifications
- Created reusable settings components: SettingsCard, TestConnectionButton, SaveButton, MaskedInput
- Created useUnsavedChanges hook with browser beforeunload and React Router blocking
- Created UnsavedChangesDialog for navigation confirmation
- Snowflake settings tab includes OAuth button from Story 1-5
- Created backend settings API with GET /api/v1/settings endpoint
- Settings API returns masked values (has_credentials boolean pattern)
- 67 backend tests passing
- Frontend lint and build passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created Settings page | frontend/src/pages/Settings.tsx |
| 2026-01-22 | Created BaseLayout component | frontend/src/components/layout/BaseLayout.tsx |
| 2026-01-22 | Created Tabs component | frontend/src/components/ui/tabs.tsx |
| 2026-01-22 | Created Card component | frontend/src/components/ui/card.tsx |
| 2026-01-22 | Created AlertDialog component | frontend/src/components/ui/alert-dialog.tsx |
| 2026-01-22 | Created Toaster component | frontend/src/components/ui/sonner.tsx |
| 2026-01-22 | Created SettingsCard component | frontend/src/components/settings/SettingsCard.tsx |
| 2026-01-22 | Created SSRSSettings component | frontend/src/components/settings/SSRSSettings.tsx |
| 2026-01-22 | Created SnowflakeSettings component | frontend/src/components/settings/SnowflakeSettings.tsx |
| 2026-01-22 | Created OllamaSettings component | frontend/src/components/settings/OllamaSettings.tsx |
| 2026-01-22 | Created SystemSettings component | frontend/src/components/settings/SystemSettings.tsx |
| 2026-01-22 | Created TestConnectionButton | frontend/src/components/settings/TestConnectionButton.tsx |
| 2026-01-22 | Created SaveButton | frontend/src/components/settings/SaveButton.tsx |
| 2026-01-22 | Created MaskedInput | frontend/src/components/settings/MaskedInput.tsx |
| 2026-01-22 | Created UnsavedChangesDialog | frontend/src/components/settings/UnsavedChangesDialog.tsx |
| 2026-01-22 | Created useUnsavedChanges hook | frontend/src/hooks/useUnsavedChanges.ts |
| 2026-01-22 | Updated Header with settings navigation | frontend/src/components/layout/Header.tsx |
| 2026-01-22 | Added settings route to main | frontend/src/main.tsx |
| 2026-01-22 | Created settings API routes | backend/app/api/routes/settings.py |
| 2026-01-22 | Created settings schemas | backend/app/schemas/settings.py |
| 2026-01-22 | Updated main.py | backend/app/main.py |

### File List
**Frontend:**
- frontend/src/pages/Settings.tsx
- frontend/src/components/layout/BaseLayout.tsx
- frontend/src/components/layout/Header.tsx (updated)
- frontend/src/components/layout/index.ts (updated)
- frontend/src/components/ui/tabs.tsx
- frontend/src/components/ui/card.tsx
- frontend/src/components/ui/alert-dialog.tsx
- frontend/src/components/ui/sonner.tsx
- frontend/src/components/settings/index.ts
- frontend/src/components/settings/SettingsCard.tsx
- frontend/src/components/settings/SSRSSettings.tsx
- frontend/src/components/settings/SnowflakeSettings.tsx
- frontend/src/components/settings/OllamaSettings.tsx
- frontend/src/components/settings/SystemSettings.tsx
- frontend/src/components/settings/TestConnectionButton.tsx
- frontend/src/components/settings/SaveButton.tsx
- frontend/src/components/settings/MaskedInput.tsx
- frontend/src/components/settings/UnsavedChangesDialog.tsx
- frontend/src/hooks/useUnsavedChanges.ts
- frontend/src/main.tsx (updated)

**Backend:**
- backend/app/api/routes/settings.py
- backend/app/api/routes/__init__.py (updated)
- backend/app/schemas/settings.py
- backend/app/schemas/__init__.py (updated)
- backend/app/main.py (updated)

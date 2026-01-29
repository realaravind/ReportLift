# Story 2.7: System Health Dashboard

Status: done

## Story

As an **admin**,
I want **to view the health status of all configured connections**,
so that **I can quickly identify and troubleshoot connectivity issues**.

## Acceptance Criteria

### AC1: Health Dashboard Display
**Given** the admin is on the Settings page, System tab
**When** viewing the dashboard
**Then** a health card is displayed for each service: SSRS, Snowflake, Ollama
**And** each card shows: Service name, Status (Connected/Disconnected/Not Configured), Last checked timestamp

### AC2: Auto-Refresh on Load
**Given** the System tab is opened
**When** the page loads
**Then** all connection statuses are automatically refreshed
**And** refresh completes within 30 seconds total

### AC3: Service Card Navigation
**Given** a service shows "Disconnected" status
**When** the admin clicks the service card
**Then** they are navigated to that service's configuration tab

### AC4: Manual Refresh
**Given** the dashboard is displayed
**When** the admin clicks "Refresh All"
**Then** all connections are tested simultaneously
**And** a loading indicator shows progress
**And** results update in real-time as each test completes

### AC5: Connection Warning Indicator
**Given** any connection is in error state
**When** viewing the header/navigation
**Then** a warning indicator is visible (orange dot on Settings link)
**And** hovering shows tooltip: "1 or more connections need attention"

## Tasks / Subtasks

- [x] **Task 1: Create System Health Dashboard Component** (AC: 1)
  - [x] Implement `SystemSettings.tsx` as health dashboard
  - [x] Create health card grid layout (3 cards in row)
  - [x] Design card structure: icon, name, status badge, timestamp
  - [x] Use custom ServiceHealthCard component

- [x] **Task 2: Create Service Health Card Component** (AC: 1, 3)
  - [x] Create reusable `ServiceHealthCard.tsx` component
  - [x] Props: health (ServiceHealth), onClick, isLoading
  - [x] Status badge colors: green (Connected), red (Disconnected), gray (Not Configured)
  - [x] Add service-specific icons (Server, Snowflake, Bot)
  - [x] Make entire card clickable for navigation

- [x] **Task 3: Implement Status Types and Styling** (AC: 1)
  - [x] Define ServiceStatus type: connected, disconnected, not_configured, checking
  - [x] Create getStatusStyles function with badge colors
  - [x] Add "Checking..." animated state during tests
  - [x] Format timestamp with formatLastChecked helper

- [x] **Task 4: Create Backend Health Endpoint** (AC: 2, 4)
  - [x] Create `GET /health/services` endpoint
  - [x] Return status for all three services
  - [x] Include last_checked timestamp for each
  - [x] Implement parallel health checks with asyncio.gather

- [x] **Task 5: Implement Individual Service Health Checks** (AC: 2)
  - [x] Reuse SSRS test logic from ssrs_service.py
  - [x] Reuse Snowflake test logic from snowflake_service.py
  - [x] Create Ollama health check
  - [x] Cache health status for 5 minutes (staleTime in React Query)

- [x] **Task 6: Create Ollama Health Check** (AC: 2)
  - [x] Create `backend/app/services/ollama_service.py`
  - [x] Implement `check_ollama_health() -> OllamaHealthResult`
  - [x] Call Ollama API: `GET {host_url}/api/tags`
  - [x] Verify configured model is available
  - [x] Handle disabled state (return NOT_CONFIGURED)

- [x] **Task 7: Implement Auto-Refresh on Tab Load** (AC: 2)
  - [x] React Query refetchOnMount: true triggers health check
  - [x] Show loading state on all cards during check
  - [x] Update cards when data arrives
  - [x] OverallStatusBanner shows checking state

- [x] **Task 8: Implement Refresh All Button** (AC: 4)
  - [x] Add "Refresh All" button to dashboard header
  - [x] Show loading spinner during refresh
  - [x] Invalidate React Query cache on click
  - [x] Disable button during active refresh

- [x] **Task 9: Implement Navigation to Service Tab** (AC: 3)
  - [x] Add onClick handler to each health card
  - [x] onNavigateToTab callback navigates to /settings?tab=<service>
  - [x] Settings page handleTabChange updates URL

- [x] **Task 10: Create Header Warning Indicator** (AC: 5)
  - [x] Create healthStore.ts Zustand store
  - [x] Add animated orange dot to Settings icon in Header
  - [x] Implement tooltip: "X connections need attention"
  - [x] Update indicator when health check completes

- [x] **Task 11: Verify All Acceptance Criteria**
  - [x] Verify all three service cards display
  - [x] Verify auto-refresh on tab open
  - [x] Verify click navigates to correct tab
  - [x] Verify Refresh All tests all services
  - [x] Verify warning indicator shows in nav

## Dev Notes

### Technical Requirements

**Health Status Schema:**
```typescript
interface ServiceHealth {
  service: "ssrs" | "snowflake" | "ollama";
  status: "connected" | "disconnected" | "not_configured" | "checking";
  message?: string;
  details?: {
    version?: string;
    response_time_ms?: number;
  };
  last_checked: string | null;
}

interface HealthResponse {
  services: ServiceHealth[];
  overall_status: "healthy" | "degraded" | "unhealthy";
}
```

**Backend Health Endpoint:**
```python
@router.get("/health/services")
async def get_services_health() -> HealthResponse:
    """
    Check health of all configured services.
    Runs checks in parallel with 10s timeout per service.
    Total timeout: 30 seconds.
    """
    pass
```

**Health Check Logic:**
```python
async def check_all_services() -> HealthResponse:
    tasks = [
        asyncio.create_task(check_ssrs_health()),
        asyncio.create_task(check_snowflake_health()),
        asyncio.create_task(check_ollama_health()),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return HealthResponse(services=results)
```

**Ollama Health Check:**
```python
async def check_ollama_health(config: OllamaConfig) -> ServiceHealth:
    if not config.enabled:
        return ServiceHealth(
            service="ollama",
            status="not_configured",
            message="Ollama is disabled"
        )

    response = await httpx.get(f"{config.host_url}/api/tags")
    models = response.json().get("models", [])
    model_available = any(m["name"] == config.model_name for m in models)

    if model_available:
        return ServiceHealth(status="connected", ...)
    else:
        return ServiceHealth(
            status="disconnected",
            message=f"Model {config.model_name} not found"
        )
```

**Card Grid Layout:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
  <ServiceHealthCard service="ssrs" />
  <ServiceHealthCard service="snowflake" />
  <ServiceHealthCard service="ollama" />
</div>
```

### Status Determination Logic
- **CONNECTED**: Service configured and responds successfully
- **DISCONNECTED**: Service configured but test fails
- **NOT_CONFIGURED**: Required settings are empty
- **CHECKING**: Test in progress (UI state only)

### Overall Status
- **healthy**: All configured services are connected
- **degraded**: Some services disconnected or not configured
- **unhealthy**: All services disconnected

### Header Warning Badge
- Use Zustand to share health state globally
- Badge appears when any service is DISCONNECTED
- Badge does NOT appear for NOT_CONFIGURED (that's expected)
- Tooltip shows count: "2 connections need attention"

### Caching Strategy
- Cache health results for 5 minutes
- Invalidate cache on:
  - Manual "Refresh All" click
  - Settings save for any service
  - Tab switch to System
- Use React Query staleTime: 5 * 60 * 1000

### Dependencies
- Requires Story 2.1 (Admin Settings Page) - tab structure
- Requires Story 2.3 (SSRS Connection Test) - SSRS health logic
- Requires Story 2.5 (Snowflake Connection Test) - Snowflake health logic
- Requires Story 2.6 (Ollama Configuration) - Ollama settings

### Architecture References
- [Source: epics.md#Story 2.7] - Story definition
- FR42: View system status and connection health
- Use Promise.allSettled for parallel connection testing

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created Ollama service with health check using httpx
- Backend health endpoint runs all checks in parallel with asyncio.gather
- Health response includes overall_status (healthy/degraded/unhealthy)
- ServiceHealthCard is a clickable button component with status-based styling
- OverallStatusBanner shows colored banner based on system health
- Created Zustand healthStore for global health state
- useServicesHealth hook syncs query results to Zustand store
- Header shows animated orange dot when services are disconnected
- Tooltip shows count of connections needing attention
- Installed @radix-ui/react-tooltip for accessible tooltips
- 68 backend tests passing
- Frontend lint and build pass

### File List
- `backend/app/services/ollama_service.py` - New Ollama health check service
- `backend/app/api/routes/health.py` - Updated with services health endpoint
- `backend/app/schemas/settings.py` - Added health response schemas
- `backend/app/schemas/__init__.py` - Export new schemas
- `frontend/src/hooks/useHealthCheck.ts` - New React Query hook for health
- `frontend/src/store/healthStore.ts` - New Zustand store for global health state
- `frontend/src/components/settings/ServiceHealthCard.tsx` - New health card component
- `frontend/src/components/settings/SystemSettings.tsx` - Updated as health dashboard
- `frontend/src/components/ui/tooltip.tsx` - New Tooltip component
- `frontend/src/components/layout/Header.tsx` - Updated with warning indicator
- `frontend/src/pages/Settings.tsx` - Pass onNavigateToTab prop

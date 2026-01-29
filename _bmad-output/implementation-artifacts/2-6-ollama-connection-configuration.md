# Story 2.6: Ollama Connection Configuration

Status: done

## Story

As an **admin**,
I want **to configure the local Ollama instance connection**,
so that **AI-assisted stored procedure conversion is available**.

## Acceptance Criteria

### AC1: Ollama Configuration Form Display
**Given** the admin is on the Settings page, Ollama tab
**When** viewing the configuration form
**Then** the following fields are displayed:
  - Ollama Host URL (default: http://localhost:11434)
  - Model Name (default: codellama:13b, with suggestions dropdown)
  - Enabled toggle (on/off)
  - Timeout (seconds, default: 60)

### AC2: Disabled Toggle Behavior
**Given** Ollama is disabled via toggle
**When** users attempt AI-assisted conversion
**Then** the system falls back to rule-based conversion only
**And** a notice is displayed: "AI assistance disabled - using rule-based conversion"

### AC3: Save Configuration
**Given** the admin saves Ollama configuration
**When** save completes
**Then** success message: "Ollama configuration saved"
**And** the enabled/disabled state is persisted

### AC4: URL Validation
**Given** Ollama is enabled
**When** the host URL is invalid format
**Then** validation error: "Invalid Ollama host URL"

### AC5: Model Suggestions
**Given** the admin is entering a model name
**When** they focus on the Model Name field
**Then** a dropdown shows common model suggestions:
  - codellama:13b (recommended)
  - codellama:7b
  - llama2:13b
  - mistral:7b
**And** custom model names can be entered

## Tasks / Subtasks

- [x] **Task 1: Create Ollama Settings Form Component** (AC: 1, 5)
  - [x] Implement `OllamaSettings.tsx` with all form fields
  - [x] Add Host URL input with default value
  - [x] Add Model Name combobox with suggestions dropdown
  - [x] Add Enabled toggle switch
  - [x] Add Timeout number input with seconds label

- [x] **Task 2: Implement Model Selection UI** (AC: 5)
  - [x] Use Select component with model options
  - [x] Populate with common model suggestions
  - [x] Allow typing custom model names via separate input
  - [x] Show "(recommended)" badge on codellama:13b
  - [x] Display model description below dropdown

- [x] **Task 3: Implement Form Validation** (AC: 4)
  - [x] Add URL format validation for Host URL
  - [x] Validate URL only when Ollama is enabled
  - [x] Add timeout range validation (1-300 seconds)
  - [x] Add required validation for Model Name when enabled
  - [x] Use react-hook-form with zod schema

- [x] **Task 4: Implement Enabled/Disabled Toggle** (AC: 2)
  - [x] Use custom Switch component
  - [x] When disabled, gray out other fields
  - [x] Show info text: "When disabled, AI features will use rule-based conversion"
  - [x] Persist toggle state independently

- [x] **Task 5: Create Backend Ollama Configuration Model** (AC: 3)
  - [x] OllamaConfig already exists in models
  - [x] Fields: host_url, model_name, enabled, timeout_seconds
  - [x] Database table already created
  - [x] Default values in place

- [x] **Task 6: Create Backend Ollama API Endpoints** (AC: 3)
  - [x] `GET /api/v1/settings/ollama` - returns current config
  - [x] `PUT /api/v1/settings/ollama` - updates configuration
  - [x] Created Pydantic schemas for request/response
  - [x] Implemented URL validation on backend

- [x] **Task 7: Connect Frontend to Backend** (AC: 1, 3)
  - [x] Created `useOllamaSettings.ts` with React Query hooks
  - [x] Created `useOllamaSettings` query hook
  - [x] Created `useUpdateOllamaSettings` mutation
  - [x] Handle loading and error states

- [x] **Task 8: Add AI Status Indicator** (AC: 2)
  - [x] Toggle shows enabled/disabled state in form
  - [x] Info banner displayed when AI features disabled
  - [x] Note: Global status badge deferred to Epic 6

- [x] **Task 9: Verify All Acceptance Criteria**
  - [x] Verify form displays all fields with defaults
  - [x] Verify model dropdown shows suggestions
  - [x] Verify toggle enables/disables feature
  - [x] Verify URL validation works
  - [x] Verify save persists configuration

## Dev Notes

### Technical Requirements

**Form Schema (Zod):**
```typescript
const ollamaConfigSchema = z.object({
  host_url: z.string()
    .url("Invalid Ollama host URL")
    .regex(/^https?:\/\//, "URL must start with http:// or https://"),
  model_name: z.string().min(1, "Model name is required"),
  enabled: z.boolean(),
  timeout_seconds: z.number()
    .min(1, "Timeout must be at least 1 second")
    .max(300, "Timeout cannot exceed 300 seconds"),
}).refine(
  (data) => !data.enabled || (data.host_url && data.model_name),
  { message: "Host URL and Model Name required when enabled" }
);
```

**API Request/Response:**
```typescript
// GET /api/settings/ollama response
interface OllamaSettingsResponse {
  host_url: string;
  model_name: string;
  enabled: boolean;
  timeout_seconds: number;
  updated_at: string | null;
}

// PUT /api/settings/ollama request
interface UpdateOllamaSettingsRequest {
  host_url: string;
  model_name: string;
  enabled: boolean;
  timeout_seconds: number;
}
```

**Database Schema:**
```sql
CREATE TABLE ollama_config (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    host_url VARCHAR(500) DEFAULT 'http://localhost:11434',
    model_name VARCHAR(100) DEFAULT 'codellama:13b',
    enabled BOOLEAN DEFAULT false,
    timeout_seconds INTEGER DEFAULT 60,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Model Suggestions:**
```typescript
const modelSuggestions = [
  { value: "codellama:13b", label: "CodeLlama 13B", recommended: true, description: "Best for code analysis and generation" },
  { value: "codellama:7b", label: "CodeLlama 7B", description: "Faster, good for simpler tasks" },
  { value: "llama2:13b", label: "Llama 2 13B", description: "General purpose, good reasoning" },
  { value: "mistral:7b", label: "Mistral 7B", description: "Fast and efficient" },
];
```

### Default Configuration
- Host URL: `http://localhost:11434` (standard Ollama port)
- Model: `codellama:13b` (recommended for code tasks)
- Enabled: `false` (opt-in feature)
- Timeout: `60` seconds

### Toggle Behavior
When disabled:
- All other form fields are visually disabled (grayed out)
- Settings are still saved (for easy re-enabling)
- AI features throughout app show fallback notice
- Test Connection button is hidden

When enabled:
- All fields are active and editable
- Test Connection button appears (Story 2.7 or separate task)
- AI features are available in conversion

### Graceful Degradation (NFR12)
- When Ollama disabled: Use rule-based conversion, no errors
- When Ollama unreachable: Fail gracefully, show notice, continue with rules
- Store enabled state in Zustand for global access:
  ```typescript
  const useAIStore = create((set) => ({
    aiEnabled: false,
    setAIEnabled: (enabled) => set({ aiEnabled: enabled }),
  }));
  ```

### Dependencies
- Requires Story 2.1 (Admin Settings Page) - tab structure
- No external service dependencies for configuration
- Ollama service itself is optional

### Architecture References
- [Source: epics.md#Story 2.6] - Story definition
- FR53: Configure Ollama connection settings
- NFR9: Connect to locally-hosted Ollama
- NFR12: Graceful degradation if Ollama unavailable

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created custom Switch component for toggle functionality
- Used Select dropdown with separate custom model input field
- Info banner appears when AI features disabled with blue styling
- Form fields grayed out (opacity-50) when disabled
- MODEL_SUGGESTIONS constant exported from hook for reuse
- Backend validates URL format with regex pattern
- 67 backend tests passing
- Frontend lint and build pass

### File List
- `frontend/src/components/settings/OllamaSettings.tsx` - Updated with full form implementation
- `frontend/src/components/ui/switch.tsx` - New custom Switch component
- `frontend/src/hooks/useOllamaSettings.ts` - New React Query hooks and model suggestions
- `backend/app/schemas/settings.py` - Added OllamaSettingsUpdateRequest schema
- `backend/app/schemas/__init__.py` - Export new schema
- `backend/app/api/routes/settings.py` - Added PUT /api/v1/settings/ollama endpoint

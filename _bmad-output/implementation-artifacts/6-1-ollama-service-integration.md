# Story 6.1: Ollama Service Integration

Status: done

## Story

As the **system**,
I want **to connect to a local Ollama instance**,
so that **AI capabilities are available for complex conversion scenarios**.

## Acceptance Criteria

### AC1: Ollama Connection Initialization
**Given** Ollama is configured and enabled (from Story 2.6)
**When** the system initializes
**Then** a connection to Ollama is established
**And** the configured model availability is verified
**And** connection status is reported to the health dashboard

### AC2: API Call Handling
**Given** the Ollama service
**When** making API calls
**Then** the configured host URL is used
**And** timeout settings are respected
**And** retry logic handles transient failures (3 retries with backoff)

### AC3: Response Processing
**Given** Ollama returns a response
**When** processing the response
**Then** the response is validated for expected format
**And** token usage is logged for monitoring
**And** response time is tracked for performance analysis

### AC4: Model Not Found Handling
**Given** the model is not found in Ollama
**When** attempting to use AI features
**Then** a clear error is returned: "Model [name] not available"
**And** the admin is directed to install the model
**And** rule-based fallback is automatically engaged

### AC5: Unexpected Response Handling
**Given** the Ollama API format changes
**When** an unexpected response is received
**Then** the error is logged with details
**And** the system falls back to rule-based conversion
**And** the user is informed AI assistance is temporarily unavailable

## Tasks / Subtasks

- [ ] **Task 1: Create Ollama Client Service** (AC: 1, 2, 3)
  - [ ] Create `backend/app/services/ollama_client.py`
  - [ ] Implement `OllamaClient` class with connection management
  - [ ] Add configuration loading from settings (host URL, model, timeout)
  - [ ] Implement async HTTP client using httpx or aiohttp
  - [ ] Add connection health check method

- [ ] **Task 2: Implement Retry Logic with Backoff** (AC: 2)
  - [ ] Implement exponential backoff retry decorator
  - [ ] Configure 3 retries with increasing delays (1s, 2s, 4s)
  - [ ] Handle connection errors, timeouts, and 5xx responses
  - [ ] Log each retry attempt with reason

- [ ] **Task 3: Response Validation and Processing** (AC: 3)
  - [ ] Create Pydantic models for Ollama request/response schemas
  - [ ] Implement response validation logic
  - [ ] Extract and parse generated content from responses
  - [ ] Handle partial or malformed responses gracefully

- [ ] **Task 4: Implement Metrics and Logging** (AC: 3)
  - [ ] Track response time for each API call
  - [ ] Log token usage (prompt tokens, completion tokens)
  - [ ] Implement performance metrics collection
  - [ ] Add structured logging for debugging

- [ ] **Task 5: Model Availability Verification** (AC: 1, 4)
  - [ ] Implement model list endpoint call (`GET /api/tags`)
  - [ ] Verify configured model exists in available models
  - [ ] Return clear error with installation instructions if missing
  - [ ] Cache model availability check (refresh every 5 minutes)

- [ ] **Task 6: Fallback and Error Handling** (AC: 4, 5)
  - [ ] Implement circuit breaker pattern for Ollama availability
  - [ ] Create fallback notification mechanism
  - [ ] Log all fallback events for operational visibility
  - [ ] Return appropriate error codes for different failure modes

- [ ] **Task 7: Health Dashboard Integration** (AC: 1)
  - [ ] Add Ollama status to system health endpoint
  - [ ] Include model name, availability, and last check time
  - [ ] Report average response time metrics
  - [ ] Integrate with Story 2.7's health dashboard

- [ ] **Task 8: Unit and Integration Tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Write unit tests for OllamaClient methods
  - [ ] Mock Ollama API responses for testing
  - [ ] Test retry logic with simulated failures
  - [ ] Test fallback behavior when Ollama unavailable

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| HTTP Client | httpx or aiohttp | Async HTTP requests to Ollama |
| Retry Library | tenacity | Exponential backoff retry logic |
| Validation | Pydantic v2 | Request/response schema validation |
| Logging | Python logging | Structured JSON logging |

### Ollama API Endpoints

```
Base URL: http://localhost:11434 (configurable)

GET /api/tags          - List available models
POST /api/generate     - Generate completion
POST /api/chat         - Chat completion (alternative)
```

### Request Format

```python
# POST /api/generate
{
    "model": "codellama:13b",
    "prompt": "Convert this SQL Server stored procedure to Snowflake...",
    "stream": false,
    "options": {
        "temperature": 0.2,
        "num_predict": 2048
    }
}
```

### Response Format

```python
# Expected response structure
{
    "model": "codellama:13b",
    "created_at": "2026-01-21T10:30:00Z",
    "response": "SELECT ...",
    "done": true,
    "context": [...],
    "total_duration": 5000000000,
    "load_duration": 1000000000,
    "prompt_eval_count": 100,
    "eval_count": 200
}
```

### OllamaClient Service Structure

```python
# backend/app/services/ollama_client.py

from pydantic import BaseModel
from typing import Optional
import httpx

class OllamaConfig(BaseModel):
    host_url: str = "http://localhost:11434"
    model: str = "codellama:13b"
    timeout: int = 60
    enabled: bool = True

class OllamaResponse(BaseModel):
    model: str
    response: str
    done: bool
    total_duration: Optional[int]
    prompt_eval_count: Optional[int]
    eval_count: Optional[int]

class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and model is available."""
        pass

    async def generate(self, prompt: str, **options) -> OllamaResponse:
        """Generate completion with retry logic."""
        pass

    async def check_model_available(self) -> bool:
        """Verify configured model exists."""
        pass
```

### Circuit Breaker Pattern

```python
# Implement circuit breaker for reliability
class CircuitBreaker:
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, skip calls
    HALF_OPEN = "half_open"  # Testing recovery

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
```

### Error Response Codes

| Code | Meaning |
|------|---------|
| `OLLAMA_UNAVAILABLE` | Cannot connect to Ollama service |
| `OLLAMA_MODEL_NOT_FOUND` | Configured model not installed |
| `OLLAMA_TIMEOUT` | Request exceeded timeout |
| `OLLAMA_INVALID_RESPONSE` | Response format unexpected |
| `OLLAMA_RATE_LIMITED` | Too many requests (if applicable) |

### Configuration Settings

```python
# In backend/app/core/config.py
class Settings(BaseSettings):
    # Ollama settings
    ollama_host_url: str = "http://localhost:11434"
    ollama_model: str = "codellama:13b"
    ollama_timeout: int = 60
    ollama_enabled: bool = True
    ollama_max_retries: int = 3
    ollama_retry_delay: float = 1.0
```

### Logging Format

```python
# Structured log for Ollama calls
{
    "event": "ollama_request",
    "model": "codellama:13b",
    "prompt_length": 500,
    "response_length": 200,
    "duration_ms": 3500,
    "tokens_prompt": 100,
    "tokens_completion": 50,
    "success": true
}
```

### References

- [Source: architecture.md#AI Integration] - Ollama client service location
- [Source: architecture.md#Error Response Format] - Error code conventions
- [Source: architecture.md#Implementation Patterns] - Logging patterns
- [Source: epics.md#Story 6.1] - Story requirements
- **PRD FRs Covered:** FR49 (Connect to local Ollama instance)
- **NFRs:** NFR9 (Connect to locally-hosted Ollama), NFR12 (Graceful degradation)

### Architecture Compliance Checklist

- [x] Service located at `backend/app/services/ollama_service.py` (extended existing service)
- [x] Uses Pydantic v2 for request/response validation
- [x] Follows snake_case naming for Python code
- [x] Error responses use OllamaResult with error_code and error_message
- [x] Logging uses structured JSON format (extra dict in logger calls)
- [x] Configuration via OllamaConfig Pydantic model
- [x] Async implementation for non-blocking calls (OllamaClient)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Extended existing `ollama_service.py` with full OllamaClient implementation
2. Created 8 Pydantic v2 schemas for config, request, response, metrics, and result
3. Implemented CircuitBreaker pattern with CLOSED/OPEN/HALF_OPEN states
4. Added exponential backoff retry logic (configurable retries, delay, backoff)
5. Implemented model availability verification with 5-minute cache
6. Added structured logging with metrics (prompt length, response length, tokens, duration)
7. Integrated with health dashboard - added circuit breaker status and model info
8. Added ServiceHealthDetails.extra_info field for additional service info
9. Created async health check function (check_ollama_health_async)
10. Added global client singleton with get_ollama_client factory
11. Created 40 unit tests covering all components (100% passing)
12. Total tests: 468 passed, 6 skipped

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Extended ollama_service with OllamaClient, Pydantic schemas, CircuitBreaker | app/services/ollama_service.py |
| 2026-01-25 | Added extra_info field to ServiceHealthDetails | app/schemas/settings.py |
| 2026-01-25 | Updated health endpoint with circuit breaker status | app/api/routes/health.py |
| 2026-01-25 | Created 40 unit tests | tests/test_ollama_service.py |

### File List

**Modified Files:**
- `app/services/ollama_service.py` - Extended with OllamaClient, Pydantic schemas, CircuitBreaker, retry logic
- `app/schemas/settings.py` - Added extra_info field to ServiceHealthDetails
- `app/api/routes/health.py` - Updated to use async health check and include circuit breaker status

**New Files:**
- `tests/test_ollama_service.py` - 40 unit tests for Ollama service components

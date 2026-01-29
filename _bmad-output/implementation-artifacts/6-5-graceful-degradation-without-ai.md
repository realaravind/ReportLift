# Story 6.5: Graceful Degradation Without AI

Status: done

## Story

As the **system**,
I want **to function fully when Ollama is unavailable**,
so that **users can still convert reports using rule-based methods**.

## Acceptance Criteria

### AC1: Ollama Disabled in Settings
**Given** Ollama is disabled in settings
**When** conversion is initiated
**Then** all AI-related steps are skipped
**And** rule-based conversion proceeds normally
**And** a notice displays: "AI assistance disabled - using rule-based conversion only"

### AC2: Ollama Unavailable Fallback
**Given** Ollama is enabled but unavailable (connection failed)
**When** conversion is initiated
**Then** the system falls back to rule-based conversion
**And** a warning displays: "AI service unavailable - proceeding with rule-based conversion"
**And** the user can continue without interruption

### AC3: Mid-Conversion Fallback
**Given** Ollama becomes unavailable mid-conversion
**When** an AI request fails
**Then** that specific item falls back to rule-based
**And** other items continue processing
**And** the summary shows: "X items used AI, Y items used rule-based fallback"

### AC4: Conversion Method Indication
**Given** AI fallback occurs
**When** viewing conversion results
**Then** each item indicates its conversion method:
  - "Rule-based conversion"
  - "AI-assisted conversion"
  - "AI unavailable - rule-based fallback"

### AC5: Manual Flagging Without AI
**Given** rule-based conversion cannot handle an item
**When** no AI is available
**Then** the item is flagged for manual conversion
**And** a generic TODO is created (without AI guidance)
**And** the conversion continues with remaining items

### AC6: Health Dashboard Warning
**Given** AI has been unavailable for multiple conversions
**When** viewing the health dashboard
**Then** a persistent warning shows: "AI service has been unavailable"
**And** last successful AI connection is displayed

## Tasks / Subtasks

- [x] **Task 1: Implement Feature Flag for AI** (AC: 1)
  - [x] Add `ai_enabled` flag to conversion context
  - [x] Check Ollama settings at conversion start
  - [x] Skip AI steps when disabled
  - [x] Display appropriate notice to user

- [x] **Task 2: Create Fallback Detection Service** (AC: 2, 3)
  - [x] Create `backend/app/services/ai_fallback.py`
  - [x] Implement connection check before AI calls
  - [x] Handle connection failures gracefully
  - [x] Track fallback events

- [x] **Task 3: Implement Per-Item Fallback Logic** (AC: 3, 4)
  - [x] Wrap AI calls in try-catch with fallback
  - [x] Switch to rule-based on AI failure
  - [x] Continue processing other items
  - [x] Record method used for each item

- [x] **Task 4: Create Conversion Method Tracking** (AC: 4)
  - [x] Add `conversion_method` field to results
  - [x] Define method values: "rule_based", "ai_assisted", "ai_fallback"
  - [x] Track counts for summary
  - [x] ConversionMethodBreakdown schema for reporting

- [x] **Task 5: Update Conversion Pipeline** (AC: 1, 2, 3, 5)
  - [x] should_use_ai() method for fallback decision
  - [x] Add fallback decision points
  - [x] Ensure non-blocking failure handling
  - [x] Maintain pipeline progress on failures

- [x] **Task 6: Implement Generic TODO Generation** (AC: 5)
  - [x] Create TODO without AI guidance
  - [x] Use template-based guidance (from Story 6.4)
  - [x] Flag as "AI unavailable"
  - [x] Continue conversion pipeline

- [x] **Task 7: Create User Notifications** (AC: 1, 2)
  - [x] Create AIStatusNotice component
  - [x] Create AIStatusBadge component
  - [x] Display at appropriate times
  - [x] Use consistent styling (info vs warning)

- [x] **Task 8: Update Conversion Summary** (AC: 3, 4)
  - [x] Create ConversionMethodSummary component
  - [x] Show counts: AI-assisted, rule-based, fallback
  - [x] Display percentage breakdown
  - [x] ConversionMethodInline for compact display

- [x] **Task 9: Health Dashboard AI Status** (AC: 6)
  - [x] Add AI availability tracking to health service
  - [x] Store last successful connection time
  - [x] GET /health/ai endpoint for detailed status
  - [x] GET /health/ai/methods endpoint for breakdown

- [x] **Task 10: Implement Logging and Metrics** (AC: 2, 3, 6)
  - [x] Log all fallback events with FallbackEvent schema
  - [x] Track fallback frequency metrics
  - [x] check_high_fallback_rate() for alerting
  - [x] Structured logging for all events

- [x] **Task 11: Unit and Integration Tests** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Test with AI disabled
  - [x] Test with simulated AI failure
  - [x] Test mid-conversion fallback
  - [x] Test method tracking
  - [x] 32 unit tests passing

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | API and services |
| Fallback Service | Python | Fallback logic |
| Frontend | React + shadcn/ui | Notifications and status |
| Health Tracking | Database + Cache | AI availability tracking |

### Conversion Method Enum

```python
from enum import Enum

class ConversionMethod(str, Enum):
    RULE_BASED = "rule_based"
    AI_ASSISTED = "ai_assisted"
    AI_FALLBACK = "ai_fallback"  # AI was enabled but unavailable
    MANUAL = "manual"  # Flagged for manual conversion

# Extended conversion result
class SPConversionResult(BaseModel):
    sp_name: str
    original_sql: str
    converted_sql: Optional[str]
    method: ConversionMethod
    is_successful: bool
    requires_manual_review: bool
    confidence: Optional[str]  # Only for AI
    fallback_reason: Optional[str]  # Only for fallback
```

### Fallback Service

```python
# backend/app/services/ai_fallback.py

from typing import Optional
from datetime import datetime, timedelta

class AIFallbackService:
    def __init__(self, ollama_client: OllamaClient, settings: Settings):
        self.ollama = ollama_client
        self.settings = settings
        self._last_available: Optional[datetime] = None
        self._consecutive_failures = 0

    def is_ai_enabled(self) -> bool:
        """Check if AI is enabled in settings."""
        return self.settings.ollama_enabled

    async def is_ai_available(self) -> bool:
        """Check if Ollama is reachable."""
        if not self.is_ai_enabled():
            return False

        try:
            available = await self.ollama.is_available()
            if available:
                self._last_available = datetime.utcnow()
                self._consecutive_failures = 0
            return available
        except Exception:
            self._consecutive_failures += 1
            return False

    def get_ai_status(self) -> dict:
        """Get AI status for health dashboard."""
        return {
            "enabled": self.is_ai_enabled(),
            "last_available": self._last_available.isoformat() if self._last_available else None,
            "consecutive_failures": self._consecutive_failures,
            "status": self._determine_status()
        }

    def _determine_status(self) -> str:
        if not self.is_ai_enabled():
            return "disabled"
        if self._consecutive_failures == 0:
            return "available"
        if self._consecutive_failures < 3:
            return "degraded"
        return "unavailable"
```

### Conversion Pipeline with Fallback

```python
# In conversion orchestrator

class ConversionOrchestrator:
    async def convert_stored_procedures(
        self,
        procedures: list[StoredProcedure]
    ) -> ConversionResults:
        results = []
        ai_available = await self.fallback_service.is_ai_available()

        for sp in procedures:
            result = await self._convert_single_sp(sp, ai_available)
            results.append(result)

            # Re-check AI availability periodically
            if len(results) % 5 == 0:
                ai_available = await self.fallback_service.is_ai_available()

        return ConversionResults(
            items=results,
            summary=self._build_summary(results)
        )

    async def _convert_single_sp(
        self,
        sp: StoredProcedure,
        ai_available: bool
    ) -> SPConversionResult:
        complexity = self.classify_complexity(sp)

        # Simple SPs always use rule-based
        if complexity == "simple":
            return await self._rule_based_convert(sp)

        # Try AI if available
        if ai_available and self.fallback_service.is_ai_enabled():
            try:
                return await self._ai_convert(sp)
            except (OllamaUnavailable, TimeoutError) as e:
                # Log and fall back
                logger.warning(f"AI fallback for {sp.name}: {e}")
                return await self._fallback_convert(sp, str(e))

        # AI not available - use rule-based or flag for manual
        if complexity == "moderate":
            return await self._rule_based_convert(sp)
        else:
            return self._flag_for_manual(sp)

    async def _fallback_convert(
        self,
        sp: StoredProcedure,
        reason: str
    ) -> SPConversionResult:
        """Attempt rule-based, or flag for manual."""
        try:
            result = await self._rule_based_convert(sp)
            result.method = ConversionMethod.AI_FALLBACK
            result.fallback_reason = reason
            return result
        except Exception:
            return self._flag_for_manual(sp, fallback_reason=reason)
```

### User Notifications

```typescript
// Frontend notification components

// Disabled notice (info)
<Alert variant="info" className="mb-4">
  <Info className="h-4 w-4" />
  <AlertTitle>AI Assistance Disabled</AlertTitle>
  <AlertDescription>
    Using rule-based conversion only.
    <Link to="/settings/ollama">Enable AI assistance</Link> for better results.
  </AlertDescription>
</Alert>

// Unavailable warning
<Alert variant="warning" className="mb-4">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>AI Service Unavailable</AlertTitle>
  <AlertDescription>
    Proceeding with rule-based conversion. Complex items may require manual review.
  </AlertDescription>
</Alert>
```

### Conversion Summary Display

```typescript
// ConversionMethodSummary component
interface MethodBreakdown {
  ruleBasedCount: number;
  aiAssistedCount: number;
  fallbackCount: number;
  manualCount: number;
  total: number;
}

function ConversionMethodSummary({ breakdown }: { breakdown: MethodBreakdown }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversion Methods Used</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <MethodRow
            label="AI-Assisted"
            count={breakdown.aiAssistedCount}
            total={breakdown.total}
            icon={<Brain />}
            variant="success"
          />
          <MethodRow
            label="Rule-Based"
            count={breakdown.ruleBasedCount}
            total={breakdown.total}
            icon={<Code />}
            variant="info"
          />
          {breakdown.fallbackCount > 0 && (
            <MethodRow
              label="AI Fallback"
              count={breakdown.fallbackCount}
              total={breakdown.total}
              icon={<AlertTriangle />}
              variant="warning"
            />
          )}
          {breakdown.manualCount > 0 && (
            <MethodRow
              label="Manual Required"
              count={breakdown.manualCount}
              total={breakdown.total}
              icon={<User />}
              variant="destructive"
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Health Dashboard AI Status

```typescript
// AIHealthStatus component for dashboard
interface AIHealthStatus {
  enabled: boolean;
  status: "available" | "degraded" | "unavailable" | "disabled";
  lastAvailable: string | null;
  consecutiveFailures: number;
}

function AIHealthCard({ status }: { status: AIHealthStatus }) {
  const getStatusColor = () => {
    switch (status.status) {
      case "available": return "bg-green-100 text-green-800";
      case "degraded": return "bg-yellow-100 text-yellow-800";
      case "unavailable": return "bg-red-100 text-red-800";
      case "disabled": return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Card className={status.status === "unavailable" ? "border-red-300" : ""}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Service (Ollama)
          </CardTitle>
          <Badge className={getStatusColor()}>
            {status.status.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {status.status === "unavailable" && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              AI service has been unavailable. Last connection: {
                status.lastAvailable
                  ? formatDistanceToNow(new Date(status.lastAvailable))
                  : "Never"
              }
            </AlertDescription>
          </Alert>
        )}
        {status.consecutiveFailures > 0 && (
          <p className="text-sm text-gray-500">
            Consecutive failures: {status.consecutiveFailures}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

### Logging

```python
# Structured logs for fallback events

# AI disabled log
{
    "event": "conversion_ai_disabled",
    "conversion_id": "uuid",
    "message": "AI assistance disabled, using rule-based only"
}

# Fallback event log
{
    "event": "ai_fallback",
    "conversion_id": "uuid",
    "sp_name": "sp_GetComplexData",
    "reason": "connection_timeout",
    "fallback_method": "rule_based",
    "success": true
}

# High fallback rate alert
{
    "event": "high_fallback_rate",
    "conversion_id": "uuid",
    "fallback_count": 8,
    "total_count": 10,
    "fallback_rate": 0.8,
    "severity": "warning"
}
```

### Configuration

```python
# Fallback configuration in settings
class Settings(BaseSettings):
    # AI fallback settings
    ollama_enabled: bool = True
    ollama_fallback_to_rules: bool = True  # Fall back to rule-based on failure
    ai_health_check_interval: int = 60  # Seconds between health checks
    ai_max_consecutive_failures: int = 5  # Before marking as unavailable
```

### References

- [Source: architecture.md#Error Handling] - Graceful degradation patterns
- [Source: architecture.md#Health Checks] - Health endpoint structure
- [Source: epics.md#Story 6.5] - Story requirements
- **PRD FRs Covered:** NFR12 (Graceful degradation if Ollama unavailable)
- **Dependencies:** Story 6.1 (Ollama Service Integration), Story 5.3 (Rule-Based SP Rewriting), Story 2.7 (System Health Dashboard)

### Architecture Compliance Checklist

- [x] Fallback service at `backend/app/services/ai_fallback.py`
- [x] Integrates with existing conversion pipeline
- [x] Health status exposed via health endpoint
- [x] Frontend notifications using shadcn/ui
- [x] Logging follows structured JSON format
- [x] Configuration via settings
- [x] Non-blocking failure handling

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created AIFallbackService with availability tracking and status reporting
- Implemented ConversionMethod enum for tracking conversion approaches
- Added ConversionMethodBreakdown for session metrics
- Created FallbackEvent schema for structured logging
- Added GET /health/ai and GET /health/ai/methods endpoints
- Created AIStatusNotice and AIStatusBadge frontend components
- Created ConversionMethodSummary and ConversionMethodInline components
- 32 unit tests covering all service functionality

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Created AI fallback service | app/services/ai_fallback.py |
| 2026-01-25 | Added AI status endpoints | app/api/routes/health.py |
| 2026-01-25 | Created AIStatusNotice component | frontend/src/components/conversion/AIStatusNotice.tsx |
| 2026-01-25 | Created ConversionMethodSummary component | frontend/src/components/conversion/ConversionMethodSummary.tsx |
| 2026-01-25 | Updated component exports | frontend/src/components/conversion/index.ts |
| 2026-01-25 | Added unit tests | tests/test_ai_fallback.py |

### File List

**Backend:**
- `app/services/ai_fallback.py` - New AI fallback service
- `app/api/routes/health.py` - Added AI status endpoints

**Frontend:**
- `frontend/src/components/conversion/AIStatusNotice.tsx` - New component
- `frontend/src/components/conversion/ConversionMethodSummary.tsx` - New component
- `frontend/src/components/conversion/index.ts` - Updated exports

**Tests:**
- `tests/test_ai_fallback.py` - 32 unit tests

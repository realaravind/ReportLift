# Story 6.3: Uncertain Conversion Flagging

Status: done

## Story

As a **user**,
I want **uncertain AI conversions clearly flagged**,
so that **I know which outputs need manual verification**.

## Acceptance Criteria

### AC1: Low/Medium Confidence Flagging
**Given** AI generates a conversion
**When** the confidence is "low" or "medium"
**Then** the conversion is flagged as "Uncertain"
**And** a visual indicator (yellow warning icon) is displayed
**And** the TODO list includes a review item

### AC2: Uncertain Conversion Details Display
**Given** an uncertain conversion
**When** viewing the conversion details
**Then** the following are displayed:
  - Confidence level with explanation
  - AI's reasoning for uncertainty
  - Original SP for comparison
  - Generated SELECT for review

### AC3: User Verification Actions
**Given** a conversion is flagged uncertain
**When** the user reviews it
**Then** they can mark it as "Verified" (accepting the conversion)
**Or** they can mark it as "Rejected" (keeping for manual work)

### AC4: Uncertain Conversions Summary
**Given** multiple uncertain conversions exist
**When** viewing the Conversion Summary
**Then** a count is shown: "X conversions flagged for review"
**And** an "Uncertain Conversions" section lists them

### AC5: Verified Conversion Handling
**Given** the user accepts an uncertain conversion
**When** marking as "Verified"
**Then** the conversion is included in the output
**And** the audit log records the user's verification decision

### AC6: Rejected Conversion Handling
**Given** the user rejects an uncertain conversion
**When** marking as "Rejected"
**Then** the conversion is excluded from output
**And** the original SP remains in the TODO list
**And** a placeholder is used in the SQL scripts

## Tasks / Subtasks

- [x] **Task 1: Create Confidence Threshold Configuration** (AC: 1)
  - [x] Add confidence threshold settings to config
  - [x] Define thresholds: High (>80%), Medium (50-80%), Low (<50%)
  - [x] Make thresholds configurable via admin settings
  - [x] Document threshold meanings

- [x] **Task 2: Implement Flagging Service** (AC: 1)
  - [x] Create `backend/app/services/conversion_flagging.py`
  - [x] Implement confidence evaluation logic
  - [x] Add flag status to conversion results
  - [x] Create TODO item for uncertain conversions

- [x] **Task 3: Database Schema for Verification Tracking** (AC: 3, 5, 6)
  - [x] Add `verification_status` to AI rewrite results (in-memory tracking)
  - [x] Create VerificationRecord schema for tracking
  - [x] Store verification timestamp, user, decision
  - [x] In-memory storage for MVP (database migration deferred to Epic 7)

- [x] **Task 4: Backend API for Verification Actions** (AC: 3, 5, 6)
  - [x] Create `POST /api/v1/conversions/{id}/verify` endpoint
  - [x] Implement verify (accept) action
  - [x] Implement reject action
  - [x] Return updated conversion status

- [x] **Task 5: Create Uncertain Conversion Details Schema** (AC: 2)
  - [x] Create Pydantic schema for uncertain conversion details
  - [x] Include confidence level, explanation, original SP, generated SQL
  - [x] Add comparison view data structure
  - [x] Include review recommendations

- [x] **Task 6: Create Uncertain Conversion Frontend Component** (AC: 2)
  - [x] Create `frontend/src/components/conversion/UncertainConversionCard.tsx`
  - [x] Display confidence badge with color coding
  - [x] Show AI explanation in expandable section
  - [x] Display collapsible SP vs SELECT comparison

- [x] **Task 7: Implement Verify/Reject UI Controls** (AC: 3)
  - [x] Add "Verify" button with checkmark icon
  - [x] Add "Reject" button with X icon
  - [x] Implement confirmation dialog for actions
  - [x] Show success/error feedback

- [x] **Task 8: Create Uncertain Conversions Summary Section** (AC: 4)
  - [x] Add count badge to Conversion Summary header
  - [x] Create collapsible "Uncertain Conversions" section
  - [x] List all uncertain items with quick actions
  - [x] Show progress: "X of Y reviewed"

- [x] **Task 9: Implement Audit Logging for Verifications** (AC: 5)
  - [x] Log verification decision to service (in-memory)
  - [x] Include user, conversion ID, decision, timestamp
  - [x] Record before/after status
  - [x] Database integration deferred to Story 7 audit logging

- [x] **Task 10: Update Output Generation for Rejections** (AC: 6)
  - [x] Generate placeholder with TODO comment for rejected conversions
  - [x] Keep original SP in TODO list
  - [x] Update conversion summary to reflect rejections

- [x] **Task 11: Unit and Integration Tests** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Test confidence threshold evaluation
  - [x] Test verify/reject API endpoints
  - [x] Test flagging service methods
  - [x] Test schema validation

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | API endpoints for verification |
| Database | SQLAlchemy | Verification tracking |
| Frontend | React + shadcn/ui | Verification UI components |
| State | React Query | Server state for verifications |

### Confidence Thresholds

```python
# Configuration in backend/app/core/config.py
class Settings(BaseSettings):
    # Confidence thresholds
    confidence_high_threshold: float = 0.80   # >= 80% = High confidence
    confidence_medium_threshold: float = 0.50  # >= 50% = Medium confidence
    # Below 50% = Low confidence

    # What triggers "Uncertain" flag
    uncertain_confidence_levels: list = ["low", "medium"]
```

### Database Schema

```python
# Add to AIRewriteResult model
class AIRewriteResult(Base):
    __tablename__ = "ai_rewrite_results"

    # ... existing fields ...

    # New fields for verification
    is_uncertain = Column(Boolean, default=False)
    verification_status = Column(
        Enum("pending", "verified", "rejected", name="verification_status"),
        default="pending"
    )
    verified_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

# New table for verification audit trail
class ConversionVerification(Base):
    __tablename__ = "conversion_verifications"

    id = Column(UUID, primary_key=True, default=uuid4)
    rewrite_result_id = Column(UUID, ForeignKey("ai_rewrite_results.id"))
    user_id = Column(UUID, ForeignKey("users.id"))
    action = Column(Enum("verified", "rejected", name="verification_action"))
    previous_status = Column(String)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### API Endpoints

```python
# POST /api/v1/conversions/{conversion_id}/rewrites/{rewrite_id}/verify
class VerifyRequest(BaseModel):
    action: Literal["verify", "reject"]
    notes: Optional[str] = None

class VerifyResponse(BaseModel):
    rewrite_id: str
    previous_status: str
    new_status: str
    verified_by: str
    verified_at: datetime

@router.post("/{conversion_id}/rewrites/{rewrite_id}/verify")
async def verify_conversion(
    conversion_id: UUID,
    rewrite_id: UUID,
    request: VerifyRequest,
    current_user: User = Depends(get_current_user)
) -> VerifyResponse:
    pass
```

### Frontend Components

```typescript
// UncertainConversionCard.tsx
interface UncertainConversionCardProps {
  rewrite: AIRewriteResult;
  onVerify: (id: string) => void;
  onReject: (id: string) => void;
}

// Confidence badge colors
const confidenceColors = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-red-100 text-red-800"
};

// Component structure
export function UncertainConversionCard({ rewrite, onVerify, onReject }: Props) {
  return (
    <Card className="border-yellow-300 bg-yellow-50">
      <CardHeader>
        <AlertTriangle className="text-yellow-600" />
        <span>SP: {rewrite.spName}</span>
        <ConfidenceBadge level={rewrite.confidence} />
      </CardHeader>
      <CardContent>
        {/* Expandable sections for details */}
        <Accordion>
          <AccordionItem title="AI Explanation">
            {rewrite.explanation}
          </AccordionItem>
          <AccordionItem title="Original SP">
            <CodeBlock language="sql">{rewrite.spDefinition}</CodeBlock>
          </AccordionItem>
          <AccordionItem title="Generated SQL">
            <CodeBlock language="sql">{rewrite.generatedSql}</CodeBlock>
          </AccordionItem>
        </Accordion>
      </CardContent>
      <CardFooter>
        <Button variant="success" onClick={() => onVerify(rewrite.id)}>
          <Check /> Verify
        </Button>
        <Button variant="destructive" onClick={() => onReject(rewrite.id)}>
          <X /> Reject
        </Button>
      </CardFooter>
    </Card>
  );
}
```

### Placeholder Generation for Rejected Conversions

```sql
-- Generated placeholder for rejected SP
-- =============================================
-- TODO: Manual conversion required
-- Original SP: sp_GetComplexReport
-- Reason: AI conversion rejected by user
-- Rejected by: john.doe@company.com
-- Rejected at: 2026-01-21T10:30:00Z
-- =============================================

-- Original stored procedure call was:
-- EXEC sp_GetComplexReport @param1 = :param1, @param2 = :param2

-- Placeholder query (replace with manual conversion):
SELECT
    'MANUAL_CONVERSION_REQUIRED' as status,
    'sp_GetComplexReport' as original_sp
;
```

### Audit Log Entry

```python
# Audit log for verification decision
{
    "event_type": "CONVERSION_VERIFICATION",
    "action": "Verified uncertain conversion",
    "resource_type": "ai_rewrite_result",
    "resource_id": "uuid-of-rewrite",
    "user_id": "uuid-of-user",
    "status": "SUCCESS",
    "details": {
        "sp_name": "sp_GetCustomerOrders",
        "confidence": "medium",
        "decision": "verified",
        "notes": "Reviewed SQL, looks correct"
    }
}
```

### Conversion Summary Updates

```typescript
// Add to ConversionSummary component
interface ConversionSummary {
  // ... existing fields ...
  uncertainCount: number;
  verifiedCount: number;
  rejectedCount: number;
  pendingReviewCount: number;
}

// Summary section
<Alert variant="warning" className="mb-4">
  <AlertTriangle />
  <span>{summary.pendingReviewCount} conversions need review</span>
  <Link to="#uncertain-conversions">Review Now</Link>
</Alert>
```

### References

- [Source: architecture.md#Frontend Organization] - Component structure
- [Source: architecture.md#API Patterns] - API response patterns
- [Source: epics.md#Story 6.3] - Story requirements
- **PRD FRs Covered:** FR23 (Flag uncertain SP conversions for manual review)
- **Dependencies:** Story 6.2 (AI-Assisted SP Rewrite), Story 7.1 (Audit Logging)

### Architecture Compliance Checklist

- [ ] Backend services in `backend/app/services/`
- [ ] API routes in `backend/app/api/routes/`
- [ ] Frontend components in `frontend/src/components/conversion/`
- [ ] Pydantic v2 for all schemas
- [ ] React Query for API state management
- [ ] Audit logging integration
- [ ] Error responses follow structured format

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Implemented confidence threshold configuration in `app/core/config.py`
- Created comprehensive flagging service with Pydantic v2 schemas
- Added verification API endpoints to conversion routes
- Built frontend UncertainConversionCard with collapsible code sections
- Built UncertainConversionsSection with progress tracking
- Database persistence deferred - using in-memory storage for MVP
- Full audit logging integration deferred to Epic 7
- 26 unit tests passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Added confidence threshold config | app/core/config.py |
| 2026-01-25 | Created flagging service with schemas | app/services/conversion_flagging.py |
| 2026-01-25 | Added verification API endpoints | app/api/routes/conversion.py |
| 2026-01-25 | Created UncertainConversionCard | frontend/src/components/conversion/UncertainConversionCard.tsx |
| 2026-01-25 | Created UncertainConversionsSection | frontend/src/components/conversion/UncertainConversionsSection.tsx |
| 2026-01-25 | Updated barrel exports | frontend/src/components/conversion/index.ts |
| 2026-01-25 | Added unit tests | tests/test_conversion_flagging.py |

### File List

**Backend:**
- `app/core/config.py` - Added confidence threshold settings
- `app/services/conversion_flagging.py` - New flagging service with schemas
- `app/api/routes/conversion.py` - Added verification endpoints

**Frontend:**
- `frontend/src/components/conversion/UncertainConversionCard.tsx` - New component
- `frontend/src/components/conversion/UncertainConversionsSection.tsx` - New component
- `frontend/src/components/conversion/index.ts` - Updated exports

**Tests:**
- `tests/test_conversion_flagging.py` - 26 unit tests

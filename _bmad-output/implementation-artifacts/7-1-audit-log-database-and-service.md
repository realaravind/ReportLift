# Story 7.1: Audit Log Database and Service

Status: done

## Story

As the **system**,
I want **a robust audit logging infrastructure**,
so that **all user actions can be tracked for compliance requirements**.

## Acceptance Criteria

### AC1: Audit Logs Table Creation
**Given** the application database
**When** audit logging is set up
**Then** an audit_logs table is created with columns:
  - id (UUID, primary key)
  - timestamp (datetime with timezone)
  - event_type (enum: LOGIN, LOGOUT, ANALYSIS, CONVERSION, CONFIG_CHANGE)
  - user_id (foreign key to users)
  - username (denormalized for historical reference)
  - action (string describing the action)
  - resource_type (e.g., "report", "connection", "template")
  - resource_id (identifier of affected resource)
  - details (JSON for event-specific data)
  - ip_address (client IP)
  - user_agent (browser/client info)
  - status (SUCCESS, FAILURE)

### AC2: Asynchronous Event Logging
**Given** the audit service
**When** an auditable event occurs
**Then** the event is logged asynchronously (non-blocking)
**And** the log entry includes all required fields
**And** sensitive data is not stored in plain text (passwords, tokens)

### AC3: Log Retention and Indexing
**Given** the database
**When** audit logs accumulate
**Then** logs are retained indefinitely until explicitly deleted (NFR17)
**And** an index exists on timestamp for efficient querying
**And** an index exists on user_id for user-based filtering

### AC4: Audit Service Error Handling
**Given** the audit service fails to write
**When** an error occurs
**Then** the error is logged to application logs
**And** the original user action is not blocked
**And** the failed audit entry is queued for retry

## Tasks / Subtasks

- [x] **Task 1: Create Audit Log Database Model** (AC: 1)
  - [x] Create `backend/app/models/audit_log.py` with SQLAlchemy model
  - [x] Define UUID primary key with auto-generation
  - [x] Define event_type as Enum (LOGIN, LOGOUT, ANALYSIS, CONVERSION, CONFIG_CHANGE)
  - [x] Define status as Enum (SUCCESS, FAILURE)
  - [x] Define user_id as foreign key (nullable for failed login attempts)
  - [x] Define details as JSON column
  - [x] Add timestamp with timezone and default to current UTC time
  - [x] Add ip_address as String (45 chars for IPv6)
  - [x] Add user_agent as Text

- [x] **Task 2: Create Alembic Migration** (AC: 1, 3)
  - [x] Generate migration for audit_logs table
  - [x] Add index on timestamp column (idx_audit_logs_timestamp)
  - [x] Add index on user_id column (idx_audit_logs_user_id)
  - [x] Add index on event_type column (idx_audit_logs_event_type)
  - [x] Add composite index on (user_id, timestamp) for user activity queries
  - [x] Run migration and verify table creation

- [x] **Task 3: Create Audit Log Pydantic Schemas** (AC: 1, 2)
  - [x] Create `backend/app/schemas/audit.py`
  - [x] Define AuditLogCreate schema for creating entries
  - [x] Define AuditLogResponse schema for API responses
  - [x] Define AuditLogFilter schema for query parameters
  - [x] Define EventType and AuditStatus enums matching model
  - [x] Ensure sensitive fields are excluded from responses

- [x] **Task 4: Implement Audit Service** (AC: 2, 4)
  - [x] Create `backend/app/services/audit_service.py`
  - [x] Implement `log_event()` async function
  - [x] Implement helper functions for each event type:
    - [x] `log_login_event()`
    - [x] `log_logout_event()`
    - [x] `log_analysis_event()`
    - [x] `log_conversion_event()`
    - [x] `log_config_change_event()`
  - [x] Implement request context extraction (IP, user agent)
  - [x] Implement async queue for non-blocking writes
  - [x] Implement retry logic for failed writes (3 retries with exponential backoff)
  - [x] Add sensitive data filtering (redact passwords, tokens)

- [x] **Task 5: Create Audit API Routes** (AC: 1, 2, 3)
  - [x] Create `backend/app/api/routes/audit.py`
  - [x] Implement `GET /api/v1/audit/logs` endpoint with pagination
  - [x] Implement query filters (date range, event_type, user_id, status)
  - [x] Add authentication requirement (admin only)
  - [x] Add rate limiting to prevent log flooding

- [x] **Task 6: Integrate Audit Service with Application** (AC: 2)
  - [x] Add audit service dependency to FastAPI app
  - [x] Create middleware to extract request context (IP, user agent)
  - [x] Register audit router in main.py
  - [x] Create background task queue for async logging

- [x] **Task 7: Testing** (AC: 1, 2, 3, 4)
  - [x] Write unit tests for audit service
  - [x] Test async logging does not block main request
  - [x] Test retry logic on database failures
  - [x] Test index performance with sample data
  - [x] Test sensitive data is properly redacted
  - [x] Test all event types log correctly

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| ORM | SQLAlchemy 2.x | Database model definition |
| Migrations | Alembic | Schema versioning |
| Validation | Pydantic v2 | Request/response schemas |
| Async Queue | asyncio.Queue | Non-blocking writes |
| UUID | uuid.uuid4 | Primary key generation |

### Database Schema (EXACT)

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(20) NOT NULL,
    user_id UUID REFERENCES users(id),
    username VARCHAR(255),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(10) NOT NULL,

    CONSTRAINT chk_event_type CHECK (event_type IN ('LOGIN', 'LOGOUT', 'ANALYSIS', 'CONVERSION', 'CONFIG_CHANGE')),
    CONSTRAINT chk_status CHECK (status IN ('SUCCESS', 'FAILURE'))
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp DESC);
```

### SQLAlchemy Model Structure

```python
# backend/app/models/audit_log.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime, timezone
import uuid

class EventType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ANALYSIS = "ANALYSIS"
    CONVERSION = "CONVERSION"
    CONFIG_CHANGE = "CONFIG_CHANGE"

class AuditStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    event_type = Column(Enum(EventType), nullable=False)
    user_id = Column(UNIQUEIDENTIFIER, ForeignKey("users.id"), nullable=True)
    username = Column(String(255), nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(Enum(AuditStatus), nullable=False)
```

### Audit Service Pattern

```python
# backend/app/services/audit_service.py
class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._queue = asyncio.Queue()

    async def log_event(
        self,
        event_type: EventType,
        action: str,
        status: AuditStatus,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Non-blocking audit log entry"""
        entry = AuditLog(
            event_type=event_type,
            action=action,
            status=status,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=self._sanitize_details(details),
            ip_address=ip_address,
            user_agent=user_agent
        )
        await self._queue.put(entry)

    def _sanitize_details(self, details: Optional[dict]) -> Optional[dict]:
        """Remove sensitive data from details"""
        if not details:
            return None
        sensitive_keys = ['password', 'token', 'secret', 'credential', 'api_key']
        return {
            k: '[REDACTED]' if any(s in k.lower() for s in sensitive_keys) else v
            for k, v in details.items()
        }
```

### API Response Format

**List Audit Logs Response:**
```json
{
  "data": {
    "logs": [
      {
        "id": "uuid",
        "timestamp": "2026-01-21T10:30:00Z",
        "event_type": "LOGIN",
        "username": "domain\\user",
        "action": "User logged in",
        "resource_type": null,
        "resource_id": null,
        "status": "SUCCESS",
        "ip_address": "192.168.1.100"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 50
  },
  "meta": {
    "timestamp": "2026-01-21T10:30:00Z"
  }
}
```

### Naming Conventions

| Category | Convention | Example |
|----------|------------|---------|
| Table name | snake_case, plural | `audit_logs` |
| Column names | snake_case | `event_type`, `user_id` |
| Index names | idx_{table}_{column} | `idx_audit_logs_timestamp` |
| Enum values | UPPER_CASE | `LOGIN`, `CONFIG_CHANGE` |
| Service methods | snake_case | `log_event()`, `log_login_event()` |

### References

**PRD FRs Covered:**
- FR43: System logs user login events (username, timestamp, success/failure) [Partial - infrastructure]
- FR44: System logs report analysis events (user, report, timestamp, score) [Partial - infrastructure]
- FR45: System logs report conversion events (user, report, timestamp, output files) [Partial - infrastructure]
- FR46: System logs configuration changes (user, setting, old value, new value) [Partial - infrastructure]

**NFRs Addressed:**
- NFR17: Audit logs retained until explicitly deleted by admin
- NFR19: Configuration persisted across restarts

**Architecture References:**
- [Source: architecture.md#Project Structure] - Backend service location
- [Source: architecture.md#Data Architecture] - SQLAlchemy + Alembic patterns
- [Source: architecture.md#API Response Patterns] - Response format
- [Source: epics.md#Story 7.1] - Story requirements

### Architecture Compliance Checklist

- [x] SQLAlchemy model follows naming conventions
- [x] Alembic migration created and tested
- [x] Pydantic schemas use v2 syntax
- [x] Async service does not block requests
- [x] Sensitive data properly redacted
- [x] Indexes created for query performance
- [x] API responses follow standard format
- [x] Error handling does not expose internals

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created AuditLog SQLAlchemy model with UUID primary key
- Created EventType and AuditStatus enums
- Created Alembic migration 006 with indexes on timestamp, user_id, event_type, and composite (user_id, timestamp)
- Created Pydantic schemas: AuditLogCreate, AuditLogResponse, AuditLogDetailResponse, AuditLogFilter, AuditLogListResponse, AuditSummary
- Implemented AuditService with sync and async logging methods
- Added sensitive data redaction for passwords, tokens, secrets, API keys
- Implemented retry logic with exponential backoff (3 retries)
- Created audit API routes: GET /logs, GET /logs/{id}, GET /summary, POST /logs, GET /my-activity
- Registered audit router in main.py
- 32 unit tests covering all service functionality

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-25 | Created audit log model | app/models/audit_log.py |
| 2026-01-25 | Created Alembic migration | alembic/versions/006_add_audit_logs_table.py |
| 2026-01-25 | Created audit schemas | app/schemas/audit.py |
| 2026-01-25 | Created audit service | app/services/audit_service.py |
| 2026-01-25 | Created audit API routes | app/api/routes/audit.py |
| 2026-01-25 | Registered audit router | app/main.py |
| 2026-01-25 | Added unit tests | tests/test_audit_service.py |

### File List

**Backend:**
- `app/models/audit_log.py` - New audit log model
- `app/models/__init__.py` - Updated exports
- `app/schemas/audit.py` - New Pydantic schemas
- `app/schemas/__init__.py` - Updated exports
- `app/services/audit_service.py` - New audit service
- `app/services/__init__.py` - Updated exports
- `app/api/routes/audit.py` - New API routes
- `app/api/routes/__init__.py` - Updated exports
- `app/main.py` - Registered audit router
- `alembic/versions/006_add_audit_logs_table.py` - New migration

**Tests:**
- `tests/test_audit_service.py` - 32 unit tests

# Story 1.3: Windows AD Authentication System

Status: done

## Story

As a **user**,
I want **to log in using my Windows/Active Directory credentials**,
so that **I can access the application without a separate password and my identity is available for SSRS access**.

## Acceptance Criteria

### AC1: Unauthenticated Redirect
**Given** the user is not authenticated
**When** they navigate to any application route
**Then** they are redirected to the login page at `/login`

### AC2: Successful Authentication
**Given** the user is on the login page
**When** they enter valid Windows AD credentials (username, password, domain)
**Then** the system authenticates via NTLM/Negotiate protocol
**And** a JWT access token is generated and returned
**And** the user's AD identity (domain\username) is captured and stored in the session
**And** the user is redirected to the main application

### AC3: Failed Authentication
**Given** the user enters invalid credentials
**When** authentication fails
**Then** an error message is displayed: "Invalid username, password, or domain"
**And** the user remains on the login page

### AC4: Authenticated API Requests
**Given** the user has a valid JWT token
**When** making API requests
**Then** the token is included in the Authorization header
**And** the backend validates the token and extracts user identity

### AC5: Token Expiration
**Given** the JWT token has expired (default: 8 hours)
**When** the user makes an API request
**Then** they receive a 401 Unauthorized response
**And** the frontend redirects to the login page

### AC6: Logout
**Given** the user clicks "Logout"
**When** the logout action completes
**Then** the JWT token is cleared from storage
**And** the user is redirected to the login page

## Tasks / Subtasks

- [x] **Task 1: Backend - Create Authentication Models and Schemas** (AC: 2, 4)
  - [x] Create `backend/app/models/user.py` - User model (stores AD identity cache)
  - [x] Create `backend/app/schemas/auth.py` - Login request/response schemas
  - [x] Define LoginRequest schema (username, password, domain)
  - [x] Define TokenResponse schema (access_token, token_type, expires_in)
  - [x] Define UserInfo schema (username, domain, full_identity)

- [x] **Task 2: Backend - Implement JWT Token Service** (AC: 2, 4, 5)
  - [x] Create `backend/app/core/security.py` - JWT utilities
  - [x] Implement `create_access_token()` function
  - [x] Implement `decode_access_token()` function
  - [x] Configure JWT secret from environment variable
  - [x] Set token expiration to 8 hours (configurable via env)
  - [x] Include user identity claims in token payload

- [x] **Task 3: Backend - Implement Windows AD Authentication** (AC: 2, 3)
  - [x] Install and configure `requests-ntlm` library
  - [x] Create `backend/app/services/ad_auth.py` - AD authentication service
  - [x] Implement NTLM authentication against domain controller
  - [x] Handle authentication success - return user identity
  - [x] Handle authentication failure - raise appropriate exception
  - [x] Capture full AD identity (DOMAIN\username format)

- [x] **Task 4: Backend - Create Auth API Routes** (AC: 1, 2, 3, 6)
  - [x] Create `backend/app/api/routes/auth.py`
  - [x] Implement `POST /api/v1/auth/login` endpoint
  - [x] Implement `POST /api/v1/auth/logout` endpoint
  - [x] Implement `GET /api/v1/auth/me` endpoint (returns current user)
  - [x] Add proper error responses with error codes

- [x] **Task 5: Backend - Implement Auth Dependency** (AC: 4, 5)
  - [x] Update `backend/app/api/deps.py` with auth dependencies
  - [x] Create `get_current_user()` dependency
  - [x] Validate JWT token from Authorization header
  - [x] Handle expired tokens with 401 response
  - [x] Extract and return user identity from token

- [x] **Task 6: Frontend - Create Auth Store and Hooks** (AC: 1, 4, 6)
  - [x] Create `frontend/src/store/authStore.ts` - Zustand auth store
  - [x] Store token, user info, and auth state
  - [x] Create `frontend/src/hooks/useAuth.ts` - Auth hook
  - [x] Implement login, logout, and isAuthenticated functions
  - [x] Persist token to localStorage (or sessionStorage)

- [x] **Task 7: Frontend - Create Login Page** (AC: 2, 3)
  - [x] Create `frontend/src/pages/Login.tsx`
  - [x] Create login form with username, password, domain fields
  - [x] Display loading state during authentication
  - [x] Display error messages on failure
  - [x] Redirect to main app on success

- [x] **Task 8: Frontend - Implement Protected Routes** (AC: 1, 5)
  - [x] Create `frontend/src/components/auth/ProtectedRoute.tsx`
  - [x] Check authentication state before rendering children
  - [x] Redirect to /login if not authenticated
  - [x] Wrap main application routes with ProtectedRoute

- [x] **Task 9: Frontend - Configure API Client with Auth** (AC: 4, 5)
  - [x] Update `frontend/src/lib/api.ts` to include Authorization header
  - [x] Add Axios interceptor for token injection
  - [x] Add Axios interceptor for 401 response handling
  - [x] Redirect to login on 401 responses

- [x] **Task 10: Frontend - Add Logout to Header** (AC: 6)
  - [x] Update Header component with user display
  - [x] Add logout button/menu item
  - [x] Implement logout action (clear token, redirect)
  - [x] Display current user identity (domain\username)

- [x] **Task 11: Verify All Acceptance Criteria** (AC: 1-6)
  - [x] Test unauthenticated redirect to /login
  - [x] Test successful login with valid AD credentials
  - [x] Test failed login with invalid credentials
  - [x] Test API requests include JWT token
  - [x] Test token expiration handling
  - [x] Test logout clears session and redirects

## Dev Notes

### Architecture References

**Authentication Flow (from architecture.md):**
```
User -> ReportLift (Windows Auth) -> JWT Token
     |
     -> SSRS (Pass-through NTLM)
     -> Snowflake (OAuth2 via IdP)
     -> Ollama (Local, no auth needed)
```

**Security Decisions:**
| Decision | Choice |
|----------|--------|
| ReportLift Login | Windows Auth (NTLM/Negotiate) |
| Session Management | JWT tokens |
| SSRS Auth | Pass-through with requests-ntlm |

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| AD Auth | requests-ntlm | NTLM authentication to AD |
| JWT | python-jose[cryptography] | Token generation and validation |
| Password Hashing | N/A | Not needed - AD validates credentials |

### Backend Dependencies

Add to `requirements.txt`:
```
requests-ntlm>=1.2.0
python-jose[cryptography]>=3.3.0
```

### JWT Token Structure

```python
# Token payload (claims)
{
    "sub": "DOMAIN\\username",      # Subject - user identity
    "domain": "DOMAIN",             # AD domain
    "username": "username",         # Username without domain
    "iat": 1705834200,              # Issued at timestamp
    "exp": 1705863000               # Expiration (8 hours later)
}
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | Authenticate and get token |
| `/api/v1/auth/logout` | POST | Invalidate session (client-side) |
| `/api/v1/auth/me` | GET | Get current user info |

### Login Request/Response

**Request:**
```json
{
    "username": "john.doe",
    "password": "secret",
    "domain": "CORPORATE"
}
```

**Success Response:**
```json
{
    "data": {
        "access_token": "eyJ...",
        "token_type": "bearer",
        "expires_in": 28800,
        "user": {
            "identity": "CORPORATE\\john.doe",
            "username": "john.doe",
            "domain": "CORPORATE"
        }
    }
}
```

**Error Response:**
```json
{
    "error": {
        "code": "AUTH_INVALID_CREDENTIALS",
        "message": "Invalid username, password, or domain"
    }
}
```

### Environment Variables

```env
# JWT Configuration
JWT_SECRET_KEY=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8

# AD Configuration (optional - for DC lookup)
AD_DOMAIN_CONTROLLER=dc.corporate.local
```

### Frontend Auth Store Structure

```typescript
interface AuthState {
    token: string | null;
    user: UserInfo | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => void;
}
```

### Error Codes

| Code | Message | HTTP Status |
|------|---------|-------------|
| AUTH_INVALID_CREDENTIALS | Invalid username, password, or domain | 401 |
| AUTH_TOKEN_EXPIRED | Token has expired | 401 |
| AUTH_TOKEN_INVALID | Invalid or malformed token | 401 |
| AUTH_REQUIRED | Authentication required | 401 |

### Security Considerations

1. **Token Storage:** Use localStorage for persistence, but consider httpOnly cookies for production
2. **HTTPS:** Tokens should only be transmitted over HTTPS (Story 1.4)
3. **Token Refresh:** Not implemented in MVP - user re-authenticates after 8 hours
4. **AD Pass-through:** User identity stored in JWT for SSRS calls (Epic 3)

### Related Stories

- Story 1.1: Provides base project structure
- Story 1.2: Provides header for user display/logout
- Story 1.4: Provides HTTPS for secure token transmission
- Story 2.3: Uses stored AD identity for SSRS connection test
- Story 3.1: Uses AD identity for SSRS folder browsing

### References

- [Source: architecture.md#Authentication & Security] - Auth decisions
- [Source: epics.md#Story 1.3] - Story requirements
- FR32: Windows/AD authentication
- FR33: AD identity pass-through (identity stored for later SSRS calls)
- FR37: Secure session tokens
- ARCH14: JWT tokens for session management
- ARCH16: Windows Auth (NTLM/Negotiate)
- ARCH19: requests-ntlm for authentication
- NFR1: Windows/AD pass-through required
- NFR4: Configurable session timeout

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Implemented complete Windows AD authentication system with JWT tokens
- Backend: Created User model, auth schemas, JWT token service, AD auth service with NTLM support
- Backend: Created auth API routes (/login, /logout, /me) with proper error handling
- Backend: Implemented auth dependency with HTTPBearer token validation
- Frontend: Created Zustand auth store with localStorage persistence
- Frontend: Created Login page with domain, username, password fields
- Frontend: Implemented ProtectedRoute component for route guarding
- Frontend: Updated API client with token injection and 401 handling
- Frontend: Added user dropdown menu with logout in Header
- Mock authentication available for development (no AD server required)
- 21 total backend tests passing (11 new auth tests)
- All acceptance criteria verified

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created auth models and schemas | backend/app/models/user.py, backend/app/schemas/auth.py |
| 2026-01-22 | Implemented JWT token service | backend/app/core/security.py, backend/app/core/config.py |
| 2026-01-22 | Implemented AD auth service | backend/app/services/ad_auth.py |
| 2026-01-22 | Created auth API routes | backend/app/api/routes/auth.py |
| 2026-01-22 | Implemented auth dependency | backend/app/api/deps.py |
| 2026-01-22 | Created frontend auth store | frontend/src/store/authStore.ts |
| 2026-01-22 | Created Login page | frontend/src/pages/Login.tsx |
| 2026-01-22 | Created ProtectedRoute | frontend/src/components/auth/ProtectedRoute.tsx |
| 2026-01-22 | Updated Header with logout | frontend/src/components/layout/Header.tsx |
| 2026-01-22 | Created UI components | frontend/src/components/ui/input.tsx, label.tsx, alert.tsx, dropdown-menu.tsx |
| 2026-01-22 | Added auth tests | backend/tests/test_auth.py |

### File List
**Backend:**
- backend/app/models/user.py
- backend/app/schemas/auth.py
- backend/app/core/security.py
- backend/app/core/config.py (updated)
- backend/app/services/ad_auth.py
- backend/app/api/routes/auth.py
- backend/app/api/deps.py (updated)
- backend/app/main.py (updated)
- backend/requirements.txt (updated)
- backend/tests/test_auth.py

**Frontend:**
- frontend/src/store/authStore.ts
- frontend/src/hooks/useAuth.ts
- frontend/src/pages/Login.tsx
- frontend/src/components/auth/ProtectedRoute.tsx
- frontend/src/components/auth/index.ts
- frontend/src/components/ui/input.tsx
- frontend/src/components/ui/label.tsx
- frontend/src/components/ui/alert.tsx
- frontend/src/components/ui/dropdown-menu.tsx
- frontend/src/components/layout/Header.tsx (updated)
- frontend/src/lib/api.ts (updated)
- frontend/src/main.tsx (updated)

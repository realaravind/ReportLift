# Story 1.5: OAuth2/PKCE Infrastructure for Snowflake SSO

Status: done

## Story

As the **system**,
I want **OAuth2 with PKCE flow infrastructure in place**,
so that **Snowflake authentication can use corporate SSO without storing passwords**.

## Acceptance Criteria

### AC1: PKCE Code Generation
**Given** the application needs to authenticate to Snowflake
**When** initiating the OAuth flow
**Then** the system generates a cryptographically random code_verifier (43-128 chars)
**And** derives a code_challenge using SHA-256
**And** stores the code_verifier securely for the callback

### AC2: OAuth Authorization Request
**Given** the OAuth authorization flow
**When** redirecting to the IdP authorization endpoint
**Then** the request includes: client_id, redirect_uri, code_challenge, code_challenge_method=S256
**And** the state parameter is included for CSRF protection

### AC3: OAuth Callback Processing
**Given** the IdP redirects back with an authorization code
**When** the callback is received at `/api/v1/auth/snowflake/callback`
**Then** the system exchanges the code for tokens using the stored code_verifier
**And** access and refresh tokens are encrypted and stored
**And** the OAuth session is marked as authenticated

### AC4: Unconfigured OAuth Handling
**Given** Snowflake OAuth is not configured (no client_id/secret)
**When** attempting to initiate OAuth flow
**Then** the system returns a clear error indicating OAuth is not configured
**And** the application continues to function for other features

### AC5: Token Refresh
**Given** the OAuth token has expired
**When** making Snowflake API calls
**Then** the system attempts to refresh using the refresh_token
**And** if refresh fails, prompts for re-authentication

## Tasks / Subtasks

- [x] **Task 1: Backend - Create OAuth Schemas** (AC: 1, 2, 3)
  - [x] Create `backend/app/schemas/oauth.py`
  - [x] Define OAuthConfig schema (client_id, client_secret, auth_url, token_url, redirect_uri)
  - [x] Define OAuthState schema (state, code_verifier, created_at)
  - [x] Define TokenResponse schema (access_token, refresh_token, expires_in, token_type)
  - [x] Define OAuthStatus schema (authenticated, expires_at)

- [x] **Task 2: Backend - Create PKCE Service** (AC: 1)
  - [x] Create `backend/app/services/pkce.py`
  - [x] Implement `generate_code_verifier()` - Random 43-128 character string
  - [x] Implement `generate_code_challenge(verifier)` - SHA-256 hash, base64url encoded
  - [x] Implement `generate_state()` - Random state parameter for CSRF
  - [x] Use `secrets` module for cryptographic randomness

- [x] **Task 3: Backend - Create OAuth Token Model** (AC: 3)
  - [x] Create `backend/app/models/oauth_token.py`
  - [x] Define OAuthToken model with encrypted fields:
    - service_type (snowflake)
    - user_id (link to authenticated user)
    - encrypted_access_token
    - encrypted_refresh_token
    - expires_at
    - created_at, updated_at
  - [x] Create Alembic migration for oauth_tokens table

- [x] **Task 4: Backend - Create OAuth State Storage** (AC: 1, 2)
  - [x] Create in-memory or database storage for OAuth state
  - [x] Store: state parameter, code_verifier, created_at
  - [x] Implement state expiration (5 minute TTL)
  - [x] Implement state cleanup for expired entries

- [x] **Task 5: Backend - Implement OAuth Service** (AC: 2, 3, 4, 5)
  - [x] Create `backend/app/services/oauth_service.py`
  - [x] Implement `initiate_oauth_flow()` - Generate PKCE params, return auth URL
  - [x] Implement `handle_callback(code, state)` - Exchange code for tokens
  - [x] Implement `refresh_tokens(refresh_token)` - Refresh expired access token
  - [x] Implement `get_valid_token(user_id, service)` - Get or refresh token
  - [x] Use credential store for token encryption (Story 1.4)

- [x] **Task 6: Backend - Create OAuth API Routes** (AC: 2, 3, 4)
  - [x] Create `backend/app/api/routes/oauth.py`
  - [x] Implement `GET /api/v1/auth/snowflake/authorize` - Initiate OAuth flow
  - [x] Implement `GET /api/v1/auth/snowflake/callback` - Handle IdP callback
  - [x] Implement `GET /api/v1/auth/snowflake/status` - Check OAuth status
  - [x] Implement `POST /api/v1/auth/snowflake/revoke` - Revoke tokens
  - [x] Handle unconfigured OAuth with appropriate error

- [x] **Task 7: Backend - Implement Token Refresh Logic** (AC: 5)
  - [x] Create token expiration checking logic
  - [x] Implement automatic refresh when token is near expiry
  - [x] Handle refresh token expiration gracefully
  - [x] Return appropriate error when re-auth required

- [x] **Task 8: Frontend - Create OAuth Hook** (AC: 2, 3, 4, 5)
  - [x] Create `frontend/src/hooks/useSnowflakeOAuth.ts`
  - [x] Implement `initiateAuth()` - Open popup for OAuth flow
  - [x] Implement `checkStatus()` - Poll for OAuth completion
  - [x] Handle OAuth success and failure states
  - [x] Manage popup window lifecycle

- [x] **Task 9: Frontend - Create OAuth Components** (AC: 2, 4)
  - [x] Create `frontend/src/components/auth/SnowflakeOAuthButton.tsx`
  - [x] Show "Connect to Snowflake" button
  - [x] Display connection status (Connected/Not Connected)
  - [x] Handle OAuth popup flow
  - [x] Display errors when OAuth not configured

- [x] **Task 10: Frontend - Create OAuth Callback Page** (AC: 3)
  - [x] Create `frontend/src/pages/OAuthCallback.tsx`
  - [x] Handle callback redirect from IdP
  - [x] Display success/failure message
  - [x] Close popup and notify parent window
  - [x] Handle error parameters from IdP

- [x] **Task 11: Verify All Acceptance Criteria** (AC: 1-5)
  - [x] Test PKCE code generation (verify randomness, length)
  - [x] Test authorization URL includes all required parameters
  - [x] Test callback processing exchanges code for tokens
  - [x] Test tokens are encrypted before storage
  - [x] Test unconfigured OAuth returns clear error
  - [x] Test token refresh flow

## Dev Notes

### Architecture References

**OAuth Decision (from architecture.md):**
| Decision | Choice |
|----------|--------|
| Snowflake Auth | OAuth2 with PKCE |

**Authentication Flow:**
```
User -> ReportLift -> Snowflake (OAuth2 via IdP)
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| PKCE | secrets + hashlib | Code verifier and challenge generation |
| OAuth Client | httpx or requests | Token exchange requests |
| Token Storage | SQLAlchemy + Fernet | Encrypted token persistence |

### PKCE Implementation Details

**Code Verifier:**
- Random string, 43-128 characters
- Characters: A-Z, a-z, 0-9, `-._~`
- Generated using `secrets.token_urlsafe()`

**Code Challenge:**
- SHA-256 hash of code_verifier
- Base64url encoded (no padding)
- `code_challenge_method=S256`

```python
import secrets
import hashlib
import base64

def generate_code_verifier() -> str:
    """Generate a random code verifier (43-128 chars)."""
    return secrets.token_urlsafe(64)[:96]  # 96 chars

def generate_code_challenge(verifier: str) -> str:
    """Generate SHA-256 code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
```

### OAuth State Schema

```python
class OAuthState(BaseModel):
    state: str                    # Random CSRF token
    code_verifier: str            # PKCE code verifier
    created_at: datetime          # For expiration check
    redirect_after: str = "/"     # Where to redirect after auth
```

### OAuth Token Model

```python
class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_type = Column(String(50))  # 'snowflake'
    encrypted_access_token = Column(Text)
    encrypted_refresh_token = Column(Text)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/snowflake/authorize` | GET | Initiate OAuth flow, return auth URL |
| `/api/v1/auth/snowflake/callback` | GET | Handle IdP callback, exchange code |
| `/api/v1/auth/snowflake/status` | GET | Check if user has valid OAuth token |
| `/api/v1/auth/snowflake/revoke` | POST | Revoke and delete stored tokens |

### Authorization URL Format

```
https://{idp_auth_url}?
    response_type=code&
    client_id={client_id}&
    redirect_uri={redirect_uri}&
    scope=openid profile&
    state={random_state}&
    code_challenge={code_challenge}&
    code_challenge_method=S256
```

### Token Exchange Request

```python
# POST to IdP token endpoint
data = {
    "grant_type": "authorization_code",
    "code": authorization_code,
    "redirect_uri": redirect_uri,
    "client_id": client_id,
    "client_secret": client_secret,  # If required
    "code_verifier": stored_code_verifier
}
```

### Environment Variables

```env
# Snowflake OAuth Configuration
SNOWFLAKE_OAUTH_CLIENT_ID=your-client-id
SNOWFLAKE_OAUTH_CLIENT_SECRET=your-client-secret
SNOWFLAKE_OAUTH_AUTH_URL=https://your-idp.com/oauth/authorize
SNOWFLAKE_OAUTH_TOKEN_URL=https://your-idp.com/oauth/token
SNOWFLAKE_OAUTH_REDIRECT_URI=https://reportlift.local/api/v1/auth/snowflake/callback
```

### Error Responses

**OAuth Not Configured:**
```json
{
    "error": {
        "code": "OAUTH_NOT_CONFIGURED",
        "message": "Snowflake OAuth is not configured. Please configure OAuth settings in the admin panel."
    }
}
```

**Token Refresh Failed:**
```json
{
    "error": {
        "code": "OAUTH_REFRESH_FAILED",
        "message": "Unable to refresh Snowflake access token. Please re-authenticate."
    }
}
```

### Frontend OAuth Flow

```typescript
// Popup-based OAuth flow
const initiateOAuth = async () => {
    // Get authorization URL from backend
    const { data } = await api.get('/auth/snowflake/authorize');

    // Open popup window
    const popup = window.open(
        data.auth_url,
        'snowflake-oauth',
        'width=600,height=700'
    );

    // Poll for completion or listen for message
    // ...
};
```

### Security Considerations

1. **State Parameter** - Required for CSRF protection
2. **PKCE** - Prevents authorization code interception
3. **Token Encryption** - Tokens encrypted at rest (Story 1.4)
4. **HTTPS** - All OAuth traffic over HTTPS (Story 1.4)
5. **State Expiration** - OAuth state expires after 5 minutes

### Related Stories

- Story 1.3: Provides user identity for OAuth token association
- Story 1.4: Provides credential encryption for token storage
- Story 2.4: Uses OAuth tokens for Snowflake connection
- Story 2.5: Uses OAuth tokens for Snowflake connection test

### References

- [Source: architecture.md#Authentication & Security] - OAuth2 with PKCE decision
- [Source: epics.md#Story 1.5] - Story requirements
- FR34: Snowflake OAuth/SSO via corporate IdP
- ARCH18: OAuth2 with PKCE
- NFR6: No stored Snowflake passwords
- NFR8: Support Snowflake OAuth/OIDC flow
- Note: OAuth endpoints configurable via admin settings (implemented in Epic 2)

### OAuth Flow Diagram

```
User                Frontend              Backend               IdP
  |                    |                     |                    |
  |--[1] Click Auth--->|                     |                    |
  |                    |--[2] GET /authorize->|                    |
  |                    |<-[3] Auth URL + state|                    |
  |                    |                     |                    |
  |<--[4] Open Popup---|                     |                    |
  |--[5] Login---------|---------------------|----------------->  |
  |                    |                     |                    |
  |<--[6] Callback-----|---------------------|<---Code + State--- |
  |                    |                     |                    |
  |                    |--[7] POST /callback->|                    |
  |                    |                     |--[8] Exchange----> |
  |                    |                     |<--Tokens---------- |
  |                    |<-[9] Success--------|                    |
  |<--[10] Close-------|                     |                    |
```

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Implemented PKCE service with RFC 7636-compliant code verifier (43-128 chars) and SHA-256 code challenge generation
- Created OAuth schemas: OAuthConfig, OAuthState, OAuthAuthorizeResponse, OAuthTokenResponse, OAuthStatus, OAuthCallbackRequest
- Created OAuthToken model with encrypted access/refresh tokens, expires_at tracking, and user association
- Implemented thread-safe in-memory OAuth state store with 5-minute TTL and automatic cleanup
- Created comprehensive OAuth service with initiate, callback, refresh, revoke, and status methods
- OAuth service integrates with credential store (Story 1.4) for token encryption at rest
- Created OAuth API routes: /authorize, /callback, /status, /revoke, /refresh
- Returns OAUTH_NOT_CONFIGURED error (503) when OAuth settings not provided
- Created useSnowflakeOAuth hook for React frontend with popup-based authentication flow
- Created SnowflakeOAuthButton component with status display and connect/disconnect functionality
- Created OAuthCallback and OAuthError pages for handling popup redirects
- Added OAuth configuration settings to config.py and .env.example
- 67 backend tests passing (28 new OAuth tests)
- Frontend build and lint passing

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Created OAuth schemas | backend/app/schemas/oauth.py |
| 2026-01-21 | Created PKCE service | backend/app/services/pkce.py |
| 2026-01-21 | Created OAuth token model | backend/app/models/oauth_token.py |
| 2026-01-21 | Created OAuth state store | backend/app/services/oauth_state_store.py |
| 2026-01-21 | Created OAuth service | backend/app/services/oauth_service.py |
| 2026-01-21 | Created OAuth API routes | backend/app/api/routes/oauth.py |
| 2026-01-21 | Added OAuth config settings | backend/app/core/config.py |
| 2026-01-21 | Created OAuth migration | backend/alembic/versions/002_add_oauth_tokens_table.py |
| 2026-01-21 | Created OAuth hook | frontend/src/hooks/useSnowflakeOAuth.ts |
| 2026-01-21 | Created OAuth button | frontend/src/components/auth/SnowflakeOAuthButton.tsx |
| 2026-01-21 | Created OAuth callback page | frontend/src/pages/OAuthCallback.tsx |
| 2026-01-21 | Created OAuth error page | frontend/src/pages/OAuthError.tsx |
| 2026-01-21 | Added OAuth routes to main | frontend/src/main.tsx |
| 2026-01-21 | Created OAuth tests | backend/tests/test_oauth.py |
| 2026-01-21 | Updated .env.example | .env.example |

### File List
**Backend:**
- backend/app/schemas/oauth.py
- backend/app/services/pkce.py
- backend/app/services/oauth_state_store.py
- backend/app/services/oauth_service.py
- backend/app/services/__init__.py (updated)
- backend/app/models/oauth_token.py
- backend/app/models/__init__.py (updated)
- backend/app/api/routes/oauth.py
- backend/app/api/routes/__init__.py (updated)
- backend/app/core/config.py (updated)
- backend/app/main.py (updated)
- backend/alembic/versions/002_add_oauth_tokens_table.py
- backend/tests/test_oauth.py

**Frontend:**
- frontend/src/hooks/useSnowflakeOAuth.ts
- frontend/src/components/auth/SnowflakeOAuthButton.tsx
- frontend/src/pages/OAuthCallback.tsx
- frontend/src/pages/OAuthError.tsx
- frontend/src/main.tsx (updated)

**Configuration:**
- .env.example (updated)

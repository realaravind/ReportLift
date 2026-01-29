---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
status: complete
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
date: 2026-01-21
---

# ReportLift - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ReportLift, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Connection & Data Source Management (FR1-FR7)**
- FR1: Admin can configure connection to an SSRS Report Server (URL, authentication method)
- FR2: Admin can configure connection to a Snowflake database (credentials, warehouse, schema)
- FR3: Admin can test SSRS connection and verify successful authentication
- FR4: Admin can test Snowflake connection and verify successful authentication
- FR5: User can browse SSRS Report Server folder structure
- FR6: User can view list of reports available in a selected SSRS folder
- FR7: System respects SSRS permissions — user only sees reports they have access to

**Report Analysis (FR8-FR17)**
- FR8: User can select a single report for analysis
- FR9: User can trigger on-demand analysis of a selected report
- FR10: System extracts features from RDL file (datasets, visuals, expressions, layout)
- FR11: System classifies report type (Tabular, Analytical, Mixed, Complex)
- FR12: System calculates conversion success score (percentage)
- FR13: System assigns conversion status (green/yellow/red) based on score thresholds
- FR14: System identifies stored procedures used in report datasets
- FR15: System identifies expressions requiring conversion attention
- FR16: System generates TODO list of manual work items for the report
- FR17: User can view detailed analysis breakdown for a report

**Report Conversion (FR18-FR27)**
- FR18: User can initiate conversion of an analyzed report
- FR19: System generates Power BI report file (.pbix) from SSRS report
- FR20: System generates Snowflake SQL scripts for report data sources
- FR21: System rewrites simple stored procedures as SELECT statements (rule-based)
- FR22: System uses AI (Ollama) to assist with complex SP rewrite scenarios
- FR23: System flags uncertain SP conversions for manual review
- FR24: System applies branding template to generated Power BI report
- FR25: User can download generated Power BI file (.pbix)
- FR26: User can download generated Snowflake SQL scripts
- FR27: User can view conversion output summary (what was converted, what needs attention)

**Branding & Templates (FR28-FR31)**
- FR28: Admin can upload a Power BI branding template (.pbit file)
- FR29: Admin can view currently configured branding template
- FR30: Admin can replace existing branding template with a new one
- FR31: System automatically applies branding template during conversion

**Authentication & Security (FR32-FR37)**
- FR32: User can authenticate using Windows/Active Directory credentials
- FR33: System passes user's AD identity through to SSRS for report access
- FR34: System authenticates to Snowflake using OAuth/SSO via corporate IdP
- FR35: System stores credentials in encrypted configuration file
- FR36: System requires HTTPS for all web traffic
- FR37: System manages user sessions with secure tokens

**Configuration & Administration (FR38-FR42)**
- FR38: Admin can access application settings/configuration page
- FR39: Admin can configure SSRS connection parameters
- FR40: Admin can configure Snowflake connection parameters
- FR41: Admin can configure OAuth/IdP settings for Snowflake SSO
- FR42: Admin can view system status and connection health

**Audit & Logging (FR43-FR48)**
- FR43: System logs user login events (username, timestamp, success/failure)
- FR44: System logs report analysis events (user, report, timestamp, score)
- FR45: System logs report conversion events (user, report, timestamp, output files)
- FR46: System logs configuration changes (user, setting, old value, new value)
- FR47: Admin can view audit logs
- FR48: Admin can export audit logs for compliance reporting

**AI Integration - Ollama (FR49-FR53)**
- FR49: System connects to local Ollama instance for AI-assisted conversion
- FR50: System sends stored procedure logic to Ollama for analysis
- FR51: System receives and applies AI-generated SELECT statement rewrites
- FR52: System uses AI to generate human-readable TODO guidance
- FR53: Admin can configure Ollama connection settings

### NonFunctional Requirements

**Security**
- NFR1: Windows/AD pass-through authentication required for user login
- NFR2: All credentials encrypted at rest using AES-256 or equivalent
- NFR3: HTTPS required for all web traffic
- NFR4: Secure session tokens with configurable timeout
- NFR5: User access respects underlying SSRS permission model
- NFR6: Snowflake auth via OAuth/SSO (no stored passwords)

**Integration**
- NFR7: Must connect to SSRS via Windows Integrated Authentication
- NFR8: Must support Snowflake OAuth/OIDC authentication flow
- NFR9: Must connect to locally-hosted Ollama instance
- NFR10: Must generate valid .pbix files openable in Power BI Desktop
- NFR11: Clear error messages when connections fail
- NFR12: Graceful degradation if Ollama unavailable (fall back to rule-based)

**Reliability**
- NFR13: No 24/7 requirement; acceptable downtime for maintenance
- NFR14: System recovers gracefully from transient errors
- NFR15: Conversion outputs are complete or not generated (no partial files)
- NFR16: System handles typical workload without crashes

**Data Retention**
- NFR17: Audit logs retained until explicitly deleted by admin
- NFR18: Analysis history retained until explicitly deleted
- NFR19: Configuration persisted across restarts

**Deployment**
- NFR20: Support Windows Server, Linux, Docker container deployment
- NFR21: Self-contained with minimal external dependencies
- NFR22: Simple installer or container image
- NFR23: Manual update process (no auto-update requirement)

**Browser Support**
- NFR24: Full support for Chrome (latest stable)
- NFR25: Full support for Edge (latest stable)
- NFR26: Basic support for IE11 (graceful degradation)

**Performance**
- NFR27: Dashboard renders within 3 seconds
- NFR28: Report list retrieved within 5 seconds
- NFR29: Per-report analysis score calculated within 2 seconds

### Additional Requirements

**From Architecture - Project Initialization:**
- ARCH1: Initialize project using documented structure (backend + frontend)
- ARCH2: Set up FastAPI backend with SQLAlchemy + Alembic migrations
- ARCH3: Set up Vite + React + TypeScript frontend with Tailwind CSS
- ARCH4: Configure Docker Compose for multi-container deployment
- ARCH5: Implement Split-Panel Explorer UI layout

**From Architecture - Technology Stack:**
- ARCH6: Use FastAPI for backend REST API with auto-generated OpenAPI docs
- ARCH7: Use Pydantic v2 for request/response validation
- ARCH8: Use React Query for server state management
- ARCH9: Use Zustand for client-side UI state
- ARCH10: Use shadcn/ui for professional UI components

**From Architecture - Implementation Patterns:**
- ARCH11: Follow snake_case naming for backend (Python, API, JSON)
- ARCH12: Follow camelCase/PascalCase naming for frontend (React)
- ARCH13: Implement structured error responses with error codes
- ARCH14: Use JWT tokens for session management
- ARCH15: Implement audit logging for all user actions

**From Architecture - Security:**
- ARCH16: Implement Windows Auth (NTLM/Negotiate) for login
- ARCH17: Use cryptography library (Fernet) for credential encryption
- ARCH18: Implement OAuth2 with PKCE for Snowflake authentication
- ARCH19: Pass Windows identity through to SSRS via requests-ntlm

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | SSRS connection configuration |
| FR2 | Epic 2 | Snowflake connection configuration |
| FR3 | Epic 2 | SSRS connection test |
| FR4 | Epic 2 | Snowflake connection test |
| FR5 | Epic 3 | Browse SSRS folder structure |
| FR6 | Epic 3 | View reports in folder |
| FR7 | Epic 3 | Respect SSRS permissions |
| FR8 | Epic 4 | Select report for analysis |
| FR9 | Epic 4 | Trigger on-demand analysis |
| FR10 | Epic 4 | Extract features from RDL |
| FR11 | Epic 4 | Classify report type |
| FR12 | Epic 4 | Calculate conversion score |
| FR13 | Epic 4 | Assign conversion status (green/yellow/red) |
| FR14 | Epic 4 | Identify stored procedures |
| FR15 | Epic 4 | Identify expressions needing attention |
| FR16 | Epic 4 | Generate TODO list |
| FR17 | Epic 4 | View detailed analysis breakdown |
| FR18 | Epic 5 | Initiate conversion |
| FR19 | Epic 5 | Generate Power BI file (.pbix) |
| FR20 | Epic 5 | Generate Snowflake SQL scripts |
| FR21 | Epic 5 | Rule-based SP rewrite |
| FR22 | Epic 6 | AI-assisted complex SP rewrite |
| FR23 | Epic 6 | Flag uncertain conversions |
| FR24 | Epic 5 | Apply branding template |
| FR25 | Epic 5 | Download Power BI file |
| FR26 | Epic 5 | Download SQL scripts |
| FR27 | Epic 5 | View conversion summary |
| FR28 | Epic 5 | Upload branding template |
| FR29 | Epic 5 | View current template |
| FR30 | Epic 5 | Replace template |
| FR31 | Epic 5 | Auto-apply template during conversion |
| FR32 | Epic 1 | Windows/AD authentication |
| FR33 | Epic 1 | AD pass-through to SSRS |
| FR34 | Epic 1 | Snowflake OAuth/SSO |
| FR35 | Epic 1 | Encrypted credential storage |
| FR36 | Epic 1 | HTTPS required |
| FR37 | Epic 1 | Secure session tokens |
| FR38 | Epic 2 | Admin settings page |
| FR39 | Epic 2 | Configure SSRS parameters |
| FR40 | Epic 2 | Configure Snowflake parameters |
| FR41 | Epic 2 | Configure OAuth/IdP settings |
| FR42 | Epic 2 | View system status/health |
| FR43 | Epic 7 | Log login events |
| FR44 | Epic 7 | Log analysis events |
| FR45 | Epic 7 | Log conversion events |
| FR46 | Epic 7 | Log configuration changes |
| FR47 | Epic 7 | View audit logs |
| FR48 | Epic 7 | Export audit logs |
| FR49 | Epic 6 | Connect to Ollama |
| FR50 | Epic 6 | Send SP to Ollama |
| FR51 | Epic 6 | Apply AI-generated rewrites |
| FR52 | Epic 6 | AI-generated TODO guidance |
| FR53 | Epic 2 | Configure Ollama settings |

## Epic List

### Epic 1: Project Foundation & Authentication
**Goal:** Development team can build the application; users can securely log in with Windows AD credentials.

**FRs Covered:** FR32, FR33, FR34, FR35, FR36, FR37
**Architecture Requirements:** ARCH1-19 (project setup, tech stack, patterns)
**NFRs:** NFR1-6 (security), NFR20-26 (deployment, browser)

**Delivers:**
- Running FastAPI backend + React frontend
- Windows AD authentication
- JWT session management
- Split-Panel Explorer UI shell
- Docker Compose deployment

---

### Epic 2: Connection Management
**Goal:** Admin can configure and verify all external system connections before users begin work.

**FRs Covered:** FR1, FR2, FR3, FR4, FR38, FR39, FR40, FR41, FR42, FR53
**NFRs:** NFR7-11 (integration)

**Delivers:**
- SSRS connection configuration & test
- Snowflake connection configuration & test
- Ollama connection configuration
- System health dashboard
- Encrypted credential storage

---

### Epic 3: SSRS Report Browser
**Goal:** Users can browse SSRS folders and find reports to convert.

**FRs Covered:** FR5, FR6, FR7

**Delivers:**
- Folder tree navigation (left panel)
- Report list display
- Permission-aware browsing

---

### Epic 4: Report Analysis
**Goal:** Users can analyze any report to understand conversion complexity before committing.

**FRs Covered:** FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17
**NFRs:** NFR29 (2-second analysis)

**Delivers:**
- Single report selection
- On-demand "Analyze" action
- RDL parsing & feature extraction
- Classification (Tabular/Analytical/Mixed/Complex)
- Conversion score (green/yellow/red)
- TODO list generation
- Detailed analysis breakdown view

---

### Epic 5: Report Conversion
**Goal:** Users can convert analyzed reports and download Power BI + SQL outputs with corporate branding.

**FRs Covered:** FR18, FR19, FR20, FR21, FR24, FR25, FR26, FR27, FR28, FR29, FR30, FR31
**NFRs:** NFR10 (valid PBIX), NFR15 (complete or nothing)

**Delivers:**
- "Convert" action on analyzed reports
- Power BI file generation (.pbix)
- Snowflake SQL script generation
- Rule-based SP → SELECT rewriting
- Branding template upload & application
- Download buttons for all outputs
- Conversion summary view

---

### Epic 6: AI-Assisted Conversion
**Goal:** Complex stored procedures get intelligent AI assistance for better conversion accuracy.

**FRs Covered:** FR22, FR23, FR49, FR50, FR51, FR52
**NFRs:** NFR12 (graceful degradation without AI)

**Delivers:**
- Ollama integration for SP analysis
- AI-generated SELECT rewrites for complex SPs
- Uncertain conversion flagging
- AI-generated TODO guidance
- Fallback to rule-based if Ollama unavailable

---

### Epic 7: Audit & Compliance
**Goal:** Admin can track all user actions for enterprise compliance requirements.

**FRs Covered:** FR43, FR44, FR45, FR46, FR47, FR48
**NFRs:** NFR17-19 (data retention)

**Delivers:**
- Login event logging
- Analysis event logging
- Conversion event logging
- Configuration change logging
- Audit log viewer
- Export for compliance reporting

---

## Epic 1: Project Foundation & Authentication

Development team can build the application; users can securely log in with Windows AD credentials.

### Story 1.1: Project Initialization & Development Environment

As a developer,
I want a properly structured FastAPI backend and React frontend with Docker Compose,
So that the team has a consistent development environment to build features.

**Acceptance Criteria:**

**Given** a new development machine with Docker installed
**When** the developer runs `docker-compose up`
**Then** both backend and frontend services start successfully
**And** the backend health endpoint at `/api/health` returns `{"status": "healthy"}`
**And** the frontend is accessible at `http://localhost:3000`

**Given** the backend project structure
**When** reviewing the codebase
**Then** it follows the architecture structure: `backend/app/{api,core,services,models,schemas}`
**And** SQLAlchemy is configured with Alembic migrations
**And** Pydantic v2 is used for request/response schemas
**And** environment configuration uses `.env` files

**Given** the frontend project structure
**When** reviewing the codebase
**Then** it follows the architecture structure: `frontend/src/{components,hooks,lib,types}`
**And** Vite + React + TypeScript is configured
**And** Tailwind CSS is configured with shadcn/ui components
**And** React Query is set up for API calls
**And** Zustand is configured for client state

**Technical Notes:**
- ARCH1: Initialize project using documented structure
- ARCH2: FastAPI + SQLAlchemy + Alembic
- ARCH3: Vite + React + TypeScript + Tailwind
- ARCH4: Docker Compose multi-container
- ARCH6-10: Technology stack requirements

---

### Story 1.2: Split-Panel Explorer UI Shell

As a user,
I want a professional enterprise application layout with navigation and content panels,
So that I can efficiently browse SSRS folders and view report details.

**Acceptance Criteria:**

**Given** the user is logged in
**When** they view the main application
**Then** a Split-Panel Explorer layout is displayed with:
  - A collapsible left panel (280px default width)
  - A content area (right panel) that fills remaining space
  - A header bar with application title "ReportLift"
  - A collapse/expand toggle for the left panel

**Given** the left panel is expanded
**When** the user clicks the collapse toggle
**Then** the left panel collapses to a minimal width (icons only)
**And** the content area expands to fill the space
**And** the collapse state persists across page navigation

**Given** the application is viewed on different screen sizes
**When** viewed on screens >= 1024px
**Then** both panels are visible
**When** viewed on screens < 1024px
**Then** the left panel overlays content as a drawer

**Technical Notes:**
- ARCH5: Split-Panel Explorer UI layout
- NFR24-26: Chrome, Edge, IE11 browser support
- Use shadcn/ui Sheet component for mobile drawer behavior

---

### Story 1.3: Windows AD Authentication System

As a user,
I want to log in using my Windows/Active Directory credentials,
So that I can access the application without a separate password and my identity is available for SSRS access.

**Acceptance Criteria:**

**Given** the user is not authenticated
**When** they navigate to any application route
**Then** they are redirected to the login page at `/login`

**Given** the user is on the login page
**When** they enter valid Windows AD credentials (username, password, domain)
**Then** the system authenticates via NTLM/Negotiate protocol
**And** a JWT access token is generated and returned
**And** the user's AD identity (domain\username) is captured and stored in the session
**And** the user is redirected to the main application

**Given** the user enters invalid credentials
**When** authentication fails
**Then** an error message is displayed: "Invalid username, password, or domain"
**And** the user remains on the login page

**Given** the user has a valid JWT token
**When** making API requests
**Then** the token is included in the Authorization header
**And** the backend validates the token and extracts user identity

**Given** the JWT token has expired (default: 8 hours)
**When** the user makes an API request
**Then** they receive a 401 Unauthorized response
**And** the frontend redirects to the login page

**Given** the user clicks "Logout"
**When** the logout action completes
**Then** the JWT token is cleared from storage
**And** the user is redirected to the login page

**Technical Notes:**
- FR32: Windows/AD authentication
- FR33: AD identity pass-through (identity stored for later SSRS calls)
- FR37: Secure session tokens
- ARCH14: JWT tokens for session management
- ARCH16: Windows Auth (NTLM/Negotiate)
- ARCH19: requests-ntlm for authentication
- NFR1: Windows/AD pass-through required
- NFR4: Configurable session timeout

---

### Story 1.4: Secure Credential Storage & HTTPS Configuration

As an admin,
I want credentials stored encrypted and all traffic secured via HTTPS,
So that sensitive data is protected both at rest and in transit.

**Acceptance Criteria:**

**Given** the application needs to store sensitive credentials (SSRS, Snowflake, Ollama)
**When** credentials are saved to the database or configuration
**Then** they are encrypted using Fernet (AES-128-CBC)
**And** the encryption key is derived from an environment variable `ENCRYPTION_KEY`
**And** only encrypted values are persisted

**Given** the application needs to retrieve stored credentials
**When** requesting credentials for a service
**Then** the credentials are decrypted in memory
**And** decrypted values are never logged or exposed in error messages

**Given** the application is deployed
**When** accessed via HTTP (port 80)
**Then** the request is redirected to HTTPS (port 443)
**And** HSTS headers are included in responses

**Given** the Docker Compose deployment
**When** configured for production
**Then** TLS certificate paths are configurable via environment variables
**And** documentation explains certificate setup (self-signed or CA-signed)

**Given** a credential encryption key is not configured
**When** the application starts
**Then** startup fails with a clear error message
**And** the log indicates `ENCRYPTION_KEY` environment variable is required

**Technical Notes:**
- FR35: Encrypted credential storage
- FR36: HTTPS required for all web traffic
- ARCH17: cryptography library (Fernet) for encryption
- NFR2: AES-256 or equivalent (Fernet uses AES-128, acceptable for MVP)
- NFR3: HTTPS required

---

### Story 1.5: OAuth2/PKCE Infrastructure for Snowflake SSO

As the system,
I want OAuth2 with PKCE flow infrastructure in place,
So that Snowflake authentication can use corporate SSO without storing passwords.

**Acceptance Criteria:**

**Given** the application needs to authenticate to Snowflake
**When** initiating the OAuth flow
**Then** the system generates a cryptographically random code_verifier (43-128 chars)
**And** derives a code_challenge using SHA-256
**And** stores the code_verifier securely for the callback

**Given** the OAuth authorization flow
**When** redirecting to the IdP authorization endpoint
**Then** the request includes: client_id, redirect_uri, code_challenge, code_challenge_method=S256
**And** the state parameter is included for CSRF protection

**Given** the IdP redirects back with an authorization code
**When** the callback is received at `/api/auth/snowflake/callback`
**Then** the system exchanges the code for tokens using the stored code_verifier
**And** access and refresh tokens are encrypted and stored
**And** the OAuth session is marked as authenticated

**Given** Snowflake OAuth is not configured (no client_id/secret)
**When** attempting to initiate OAuth flow
**Then** the system returns a clear error indicating OAuth is not configured
**And** the application continues to function for other features

**Given** the OAuth token has expired
**When** making Snowflake API calls
**Then** the system attempts to refresh using the refresh_token
**And** if refresh fails, prompts for re-authentication

**Technical Notes:**
- FR34: Snowflake OAuth/SSO via corporate IdP
- ARCH18: OAuth2 with PKCE
- NFR6: No stored Snowflake passwords
- NFR8: Support Snowflake OAuth/OIDC flow
- OAuth endpoints configurable via admin settings (implemented in Epic 2)

---

## Epic 2: Connection Management

Admin can configure and verify all external system connections before users begin work.

### Story 2.1: Admin Settings Page

As an admin,
I want to access a dedicated settings/configuration page,
So that I can manage all application connections and configurations in one place.

**Acceptance Criteria:**

**Given** the user is authenticated
**When** they click the "Settings" link in the header or navigation
**Then** they are navigated to `/settings`
**And** a tabbed interface is displayed with sections: "SSRS", "Snowflake", "Ollama", "System"

**Given** the settings page
**When** viewing any tab
**Then** current configuration values are displayed (with sensitive values masked)
**And** a "Test Connection" button is available for each service
**And** a "Save" button persists changes

**Given** the user makes configuration changes
**When** they click "Save" without testing
**Then** changes are saved
**And** a warning is displayed: "Configuration saved. Test connection recommended."

**Technical Notes:**
- FR38: Admin settings page access
- Settings page in right panel of Split-Panel Explorer
- Use shadcn/ui Tabs component

---

### Story 2.2: SSRS Connection Configuration

As an admin,
I want to configure the SSRS Report Server connection details,
So that users can browse and analyze reports from our SSRS instance.

**Acceptance Criteria:**

**Given** the admin is on the Settings page, SSRS tab
**When** viewing the configuration form
**Then** the following fields are displayed:
  - Report Server URL (required, text input)
  - Authentication Method (dropdown: Windows Integrated)
  - Service Account Username (optional, for scheduled operations)
  - Service Account Password (optional, masked input)

**Given** the admin enters SSRS configuration
**When** they click "Save"
**Then** the configuration is validated (URL format check)
**And** credentials are encrypted before storage
**And** success message: "SSRS configuration saved"

**Given** an invalid URL format is entered
**When** validation runs
**Then** an error is displayed: "Invalid Report Server URL format"
**And** the form is not submitted

**Given** the SSRS configuration exists
**When** viewing the settings page
**Then** the URL is displayed
**And** passwords are masked as "••••••••"
**And** a "Clear Credentials" option is available

**Technical Notes:**
- FR1: Configure connection to SSRS Report Server
- FR39: Configure SSRS parameters
- NFR7: Windows Integrated Authentication support
- Use Story 1.4's encryption service for credential storage

---

### Story 2.3: SSRS Connection Test

As an admin,
I want to test the SSRS connection before users start working,
So that I can verify the configuration is correct.

**Acceptance Criteria:**

**Given** SSRS configuration has been saved
**When** the admin clicks "Test Connection"
**Then** the system attempts to authenticate to the Report Server
**And** a loading indicator is displayed during the test
**And** the test completes within 10 seconds (timeout)

**Given** the connection test succeeds
**When** results are displayed
**Then** a success message shows: "Connected to SSRS successfully"
**And** the Report Server version is displayed (if available)
**And** the status indicator turns green

**Given** the connection test fails
**When** results are displayed
**Then** an error message shows the failure reason
**And** common issues are suggested (e.g., "Check URL", "Verify credentials", "Check network access")
**And** the status indicator turns red

**Given** the current user's AD identity
**When** testing SSRS connection
**Then** the test uses the AD pass-through identity (from Story 1.3)
**And** confirms the user has at least read access to the root folder

**Technical Notes:**
- FR3: Test SSRS connection and verify authentication
- NFR11: Clear error messages when connections fail
- Use requests-ntlm with user's AD identity

---

### Story 2.4: Snowflake Connection Configuration

As an admin,
I want to configure the Snowflake database connection,
So that the system can generate SQL scripts targeting our Snowflake instance.

**Acceptance Criteria:**

**Given** the admin is on the Settings page, Snowflake tab
**When** viewing the configuration form
**Then** the following fields are displayed:
  - Account Identifier (required, e.g., "xy12345.us-east-1")
  - Warehouse (required)
  - Database (required)
  - Schema (required)
  - Authentication Method (dropdown: OAuth/SSO, Username/Password)
  - OAuth Settings (expandable section when OAuth selected):
    - IdP Authorization URL
    - IdP Token URL
    - Client ID
    - Client Secret (masked)
    - Redirect URI (auto-populated, read-only)

**Given** OAuth/SSO is selected as authentication method
**When** the admin clicks "Authorize"
**Then** the OAuth PKCE flow (from Story 1.5) is initiated
**And** a popup window opens for IdP authentication
**And** on success, tokens are stored encrypted

**Given** Username/Password is selected (fallback option)
**When** credentials are entered
**Then** a warning is displayed: "OAuth/SSO is recommended for security"
**And** credentials are encrypted before storage

**Given** the admin saves valid configuration
**When** save completes
**Then** success message: "Snowflake configuration saved"
**And** the connection parameters are available for SQL generation

**Technical Notes:**
- FR2: Configure Snowflake database connection
- FR40: Configure Snowflake connection parameters
- FR41: Configure OAuth/IdP settings
- NFR6: OAuth/SSO preferred (no stored passwords)
- NFR8: OAuth/OIDC authentication flow

---

### Story 2.5: Snowflake Connection Test

As an admin,
I want to test the Snowflake connection,
So that I can verify the database is accessible before conversion begins.

**Acceptance Criteria:**

**Given** Snowflake configuration has been saved
**When** the admin clicks "Test Connection"
**Then** the system attempts to connect to Snowflake
**And** a loading indicator is displayed
**And** the test completes within 15 seconds (timeout)

**Given** OAuth authentication is configured
**When** testing connection
**Then** the stored OAuth tokens are used
**And** if tokens expired, the user is prompted to re-authorize

**Given** the connection test succeeds
**When** results are displayed
**Then** a success message shows: "Connected to Snowflake successfully"
**And** displays: Account, Warehouse, Database, Schema, Role
**And** the status indicator turns green

**Given** the connection test fails
**When** results are displayed
**Then** the error message includes Snowflake error code/message
**And** suggestions for common issues are displayed
**And** the status indicator turns red

**Given** the warehouse or database doesn't exist
**When** the test runs
**Then** specific error: "Warehouse 'X' not found" or "Database 'Y' not found"

**Technical Notes:**
- FR4: Test Snowflake connection and verify authentication
- NFR11: Clear error messages
- Use snowflake-connector-python for connection

---

### Story 2.6: Ollama Connection Configuration

As an admin,
I want to configure the local Ollama instance connection,
So that AI-assisted stored procedure conversion is available.

**Acceptance Criteria:**

**Given** the admin is on the Settings page, Ollama tab
**When** viewing the configuration form
**Then** the following fields are displayed:
  - Ollama Host URL (default: http://localhost:11434)
  - Model Name (default: codellama:13b, with suggestions dropdown)
  - Enabled toggle (on/off)
  - Timeout (seconds, default: 60)

**Given** Ollama is disabled via toggle
**When** users attempt AI-assisted conversion
**Then** the system falls back to rule-based conversion only
**And** a notice is displayed: "AI assistance disabled - using rule-based conversion"

**Given** the admin saves Ollama configuration
**When** save completes
**Then** success message: "Ollama configuration saved"
**And** the enabled/disabled state is persisted

**Given** Ollama is enabled
**When** the host URL is invalid format
**Then** validation error: "Invalid Ollama host URL"

**Technical Notes:**
- FR53: Configure Ollama connection settings
- NFR9: Connect to locally-hosted Ollama
- NFR12: Graceful degradation if Ollama unavailable

---

### Story 2.7: System Health Dashboard

As an admin,
I want to view the health status of all configured connections,
So that I can quickly identify and troubleshoot connectivity issues.

**Acceptance Criteria:**

**Given** the admin is on the Settings page, System tab
**When** viewing the dashboard
**Then** a health card is displayed for each service: SSRS, Snowflake, Ollama
**And** each card shows: Service name, Status (Connected/Disconnected/Not Configured), Last checked timestamp

**Given** the System tab is opened
**When** the page loads
**Then** all connection statuses are automatically refreshed
**And** refresh completes within 30 seconds total

**Given** a service shows "Disconnected" status
**When** the admin clicks the service card
**Then** they are navigated to that service's configuration tab

**Given** the dashboard is displayed
**When** the admin clicks "Refresh All"
**Then** all connections are tested simultaneously
**And** a loading indicator shows progress
**And** results update in real-time as each test completes

**Given** any connection is in error state
**When** viewing the header/navigation
**Then** a warning indicator is visible (orange dot on Settings link)
**And** hovering shows tooltip: "1 or more connections need attention"

**Technical Notes:**
- FR42: View system status and connection health
- Use Promise.allSettled for parallel connection testing
- Store last check timestamp in local state

---

## Epic 3: SSRS Report Browser

Users can browse SSRS folders and find reports to convert.

### Story 3.1: SSRS Folder Tree Navigation

As a user,
I want to browse the SSRS Report Server folder structure,
So that I can navigate to the reports I need to convert.

**Acceptance Criteria:**

**Given** the user is authenticated and SSRS is configured
**When** they view the main application
**Then** the left panel displays the SSRS folder tree starting at the root "/"
**And** folders are displayed with folder icons
**And** the tree loads within 5 seconds (NFR28)

**Given** the folder tree is displayed
**When** the user clicks a folder with subfolders
**Then** the folder expands to show child folders
**And** a loading indicator is shown while fetching children
**And** the expanded state is maintained during the session

**Given** a folder has no subfolders
**When** the user clicks it
**Then** it is selected (highlighted)
**And** no expand/collapse indicator is shown

**Given** the user's AD identity
**When** fetching folder contents
**Then** only folders the user has permission to see are displayed (FR7)
**And** hidden/restricted folders are not shown

**Given** the folder fetch fails
**When** an error occurs
**Then** an error message is displayed inline: "Unable to load folders"
**And** a "Retry" option is available

**Given** the SSRS connection is not configured
**When** viewing the folder tree area
**Then** a message is displayed: "SSRS not configured"
**And** a link to Settings is provided

**Technical Notes:**
- FR5: Browse SSRS Report Server folder structure
- FR7: Respect SSRS permissions
- NFR28: Report list within 5 seconds
- Use virtual tree rendering for large folder structures
- Lazy-load children on expand

---

### Story 3.2: Report List Display

As a user,
I want to see the list of reports in a selected folder,
So that I can choose which report to analyze and convert.

**Acceptance Criteria:**

**Given** the user selects a folder in the tree
**When** the folder is selected
**Then** the right panel displays a list of reports in that folder
**And** each report shows: Name, Description (truncated), Modified Date, Size
**And** reports are sorted alphabetically by name (default)

**Given** the report list is displayed
**When** viewing report entries
**Then** each row is clickable/selectable
**And** a visual indicator shows the selected report (if any)
**And** only reports the user has permission to view are shown (FR7)

**Given** a folder contains no reports
**When** viewing the list
**Then** a message is displayed: "No reports in this folder"
**And** subfolders are not shown in the report list (folders are tree-only)

**Given** a folder contains many reports (50+)
**When** scrolling the list
**Then** virtual scrolling is used for performance
**And** a "Showing X of Y reports" count is displayed

**Given** the user wants to find a specific report
**When** they type in the search/filter box
**Then** the list filters to reports matching the search text
**And** filtering is instant (client-side)
**And** search matches against Name and Description

**Given** the report list fetch fails
**When** an error occurs
**Then** an error message is displayed: "Unable to load reports"
**And** the specific error from SSRS is shown
**And** a "Retry" option is available

**Technical Notes:**
- FR6: View list of reports in selected folder
- FR7: Respect SSRS permissions (AD pass-through)
- Use React Query for caching and background refresh
- Display as a data table with shadcn/ui Table component

---

### Story 3.3: Report Selection and Preview

As a user,
I want to see basic information about a report before analyzing it,
So that I can confirm I've selected the correct report.

**Acceptance Criteria:**

**Given** the report list is displayed
**When** the user clicks a report row
**Then** the report is selected (row highlighted)
**And** a preview panel appears below the list (or side panel on wide screens)
**And** the preview shows: Full Name, Path, Description, Created Date, Modified Date, Created By

**Given** a report is selected
**When** viewing the preview panel
**Then** an "Analyze" button is prominently displayed
**And** if the report was previously analyzed, the last analysis score is shown

**Given** the user double-clicks a report
**When** the action fires
**Then** it is equivalent to selecting and clicking "Analyze"

**Given** no report is selected
**When** viewing the content area
**Then** a placeholder message is shown: "Select a report to view details"

**Given** the selected report has a description
**When** viewing the preview
**Then** the full description is displayed (not truncated)
**And** markdown formatting in the description is rendered

**Technical Notes:**
- FR8: Select single report for analysis (partial - selection mechanism)
- Preview data comes from SSRS catalog metadata
- Store selected report in Zustand for cross-component access

---

## Epic 4: Report Analysis

Users can analyze any report to understand conversion complexity before committing.

### Story 4.1: Trigger On-Demand Report Analysis

As a user,
I want to trigger analysis of a selected report,
So that I can understand its conversion complexity before deciding to convert.

**Acceptance Criteria:**

**Given** a report is selected in the browser
**When** the user clicks the "Analyze" button
**Then** the system fetches the RDL file from SSRS
**And** a loading indicator shows "Analyzing report..."
**And** analysis completes within 2 seconds (NFR29)

**Given** analysis is in progress
**When** viewing the UI
**Then** the "Analyze" button is disabled
**And** a cancel option is available
**And** navigation away shows a confirmation dialog

**Given** analysis completes successfully
**When** results are available
**Then** the view transitions to the Analysis Results dashboard
**And** the analysis is stored in the database for future reference

**Given** the same report is analyzed again
**When** initiating analysis
**Then** the user is prompted: "Report was analyzed on [date]. Analyze again?"
**And** selecting "Yes" runs a fresh analysis
**And** selecting "View Previous" shows the cached results

**Given** the RDL file cannot be fetched
**When** an error occurs
**Then** an error message shows: "Unable to fetch report definition"
**And** the specific SSRS error is displayed
**And** the user can retry or select a different report

**Technical Notes:**
- FR8: Select single report for analysis
- FR9: Trigger on-demand analysis
- NFR29: Per-report analysis within 2 seconds
- Use background task for analysis with SSE/polling for status
- Store analysis results in reports table

---

### Story 4.2: RDL Parsing and Feature Extraction

As the system,
I want to parse RDL XML files and extract complexity features,
So that the analysis engine can classify and score reports accurately.

**Acceptance Criteria:**

**Given** an RDL file is received for analysis
**When** parsing begins
**Then** the XML is validated as proper RDL format
**And** the RDL namespace version is detected (2008, 2010, 2016)

**Given** a valid RDL file
**When** extracting dataset features
**Then** the following are captured:
  - Dataset count
  - Query type for each dataset (embedded SQL, stored procedure, shared dataset reference)
  - Parameter count and types
  - Field mappings

**Given** a valid RDL file
**When** extracting visual features
**Then** the following are captured:
  - Report item types (Table, Matrix, Chart, Gauge, Map, etc.)
  - Item count by type
  - Nested items (subreports, rectangles with children)
  - Grouping complexity (row groups, column groups, recursive groups)

**Given** a valid RDL file
**When** extracting expression features
**Then** the following are captured:
  - Expression count and locations
  - Expression types (field references, aggregates, custom code, lookups)
  - VB.NET custom code functions
  - RunningValue expressions (complexity flag)

**Given** a valid RDL file
**When** extracting layout features
**Then** the following are captured:
  - Page dimensions and orientation
  - Header/footer presence
  - Multi-column layout
  - Print-specific settings

**Given** an invalid or corrupted RDL file
**When** parsing fails
**Then** an error is returned: "Invalid RDL format"
**And** the specific XML parse error is included

**Technical Notes:**
- FR10: Extract features from RDL file
- Use lxml for XML parsing with namespace handling
- Create structured AnalysisFeatures Pydantic model
- Store raw features in JSON column for flexibility

---

### Story 4.3: Report Classification and Scoring Engine

As the system,
I want to classify reports and calculate conversion scores,
So that users can quickly understand conversion complexity.

**Acceptance Criteria:**

**Given** extracted features from RDL parsing
**When** classification runs
**Then** the report is categorized as one of:
  - **Tabular**: Primarily tables, simple grouping, no complex visuals
  - **Analytical**: Charts, gauges, KPIs, moderate expressions
  - **Mixed**: Combination of tabular and analytical elements
  - **Complex**: Subreports, maps, extensive custom code, recursive hierarchies

**Given** extracted features
**When** calculating conversion score
**Then** a percentage score (0-100%) is calculated using weighted penalties:
  - Stored procedures: -15% each
  - Subreports: -20% each
  - Custom VB code: -25% per function
  - RunningValue expressions: -10% each
  - Maps/Gauges: -15% each
  - Recursive groups: -10% each
  - Base score starts at 100%

**Given** a calculated score
**When** determining status
**Then** the status is assigned as:
  - **Green (70-100%)**: High conversion confidence
  - **Yellow (40-69%)**: Moderate complexity, manual work required
  - **Red (0-39%)**: Significant manual work, review recommended

**Given** classification and scoring complete
**When** storing results
**Then** the following are saved:
  - Report type classification
  - Conversion score percentage
  - Status (green/yellow/red)
  - Feature breakdown with individual penalties
  - Timestamp of analysis

**Technical Notes:**
- FR11: Classify report type
- FR12: Calculate conversion success score
- FR13: Assign conversion status based on thresholds
- Scoring weights should be configurable in settings (future enhancement)
- Store score breakdown for transparency

---

### Story 4.4: Stored Procedure and Expression Analysis

As the system,
I want to identify stored procedures and complex expressions,
So that the TODO list accurately reflects manual work requirements.

**Acceptance Criteria:**

**Given** a dataset uses a stored procedure
**When** analyzing the dataset
**Then** the stored procedure name is extracted
**And** the procedure is marked as requiring conversion attention
**And** the SP complexity is estimated (simple/moderate/complex) based on parameter count

**Given** multiple datasets with stored procedures
**When** analysis completes
**Then** all unique stored procedures are listed
**And** duplicate references are noted (e.g., "SP_GetSales used in 3 datasets")

**Given** expressions are found in the report
**When** analyzing expressions
**Then** each expression is categorized:
  - **Auto-convertible**: Simple field references, basic aggregates (Sum, Count, Avg)
  - **Partial**: Lookup, Previous, aggregate with filters
  - **Manual**: Custom VB code calls, RunningValue, RowNumber with scope

**Given** VB custom code is present
**When** analyzing the code block
**Then** each function is identified
**And** function complexity is estimated (lines of code, parameters)
**And** common patterns are flagged (e.g., "date formatting", "string manipulation")

**Given** expressions requiring attention
**When** storing results
**Then** each is saved with:
  - Location (which report item)
  - Expression text
  - Category (auto/partial/manual)
  - Reason for categorization

**Technical Notes:**
- FR14: Identify stored procedures used in report datasets
- FR15: Identify expressions requiring conversion attention
- Use regex patterns for common VB functions
- Create reusable expression analyzer service

---

### Story 4.5: TODO List Generation

As a user,
I want a clear TODO list of manual work items for a report,
So that I know exactly what needs my attention after conversion.

**Acceptance Criteria:**

**Given** analysis has identified complexity items
**When** generating the TODO list
**Then** items are created for each:
  - Stored procedure requiring conversion
  - Expression requiring manual attention
  - Subreport requiring separate handling
  - Custom VB code function
  - Unsupported visual element

**Given** a TODO item is generated
**When** viewing the item
**Then** it includes:
  - Title (clear, actionable statement)
  - Category (SP, Expression, Subreport, etc.)
  - Priority (High/Medium/Low based on impact)
  - Location in report (dataset name, visual name, line number if applicable)
  - Guidance (brief suggestion for resolution)

**Given** the TODO list is generated
**When** displaying items
**Then** they are sorted by priority (High first)
**And** grouped by category
**And** a count is shown: "X items requiring attention"

**Given** no complexity items are found (green report)
**When** viewing TODO list
**Then** a message shows: "No manual work items identified"
**And** the user can proceed directly to conversion

**Given** TODO items exist
**When** stored in the database
**Then** each item is linked to the analysis record
**And** items can be marked as "resolved" by the user (for tracking)

**Technical Notes:**
- FR16: Generate TODO list of manual work items
- TODO priorities: SP = High, Custom Code = High, Subreports = Medium, Complex Expressions = Medium
- Guidance text uses templates based on item type

---

### Story 4.6: Analysis Results Dashboard

As a user,
I want to view a detailed analysis breakdown for a report,
So that I can make informed decisions about conversion.

**Acceptance Criteria:**

**Given** analysis has completed
**When** viewing the Analysis Results dashboard
**Then** a summary card displays:
  - Report name and path
  - Classification (Tabular/Analytical/Mixed/Complex)
  - Conversion score with visual indicator (green/yellow/red)
  - Analysis timestamp

**Given** the Analysis Results dashboard
**When** viewing the Score Breakdown section
**Then** a visual breakdown shows:
  - Base score (100%)
  - Each penalty applied with reason
  - Final score calculation
  - Color-coded bar or gauge

**Given** the Analysis Results dashboard
**When** viewing the Features section
**Then** tabs or sections display:
  - **Datasets**: List with query type, parameters, SP flags
  - **Visuals**: List with type, grouping complexity
  - **Expressions**: List with category and location
  - **Layout**: Page settings, headers/footers

**Given** the Analysis Results dashboard
**When** viewing the TODO section
**Then** the full TODO list from Story 4.5 is displayed
**And** items are expandable for full details
**And** a "Mark Resolved" checkbox is available per item

**Given** the analysis shows green status
**When** viewing the dashboard
**Then** a prominent "Convert Report" button is displayed
**And** conversion can be initiated directly

**Given** the analysis shows yellow/red status
**When** viewing the dashboard
**Then** a "Convert Report" button is available with a warning
**And** warning text: "Review TODO items before converting"

**Given** the user wants to re-analyze
**When** clicking "Re-Analyze"
**Then** a fresh analysis is triggered
**And** the new results replace the previous analysis

**Technical Notes:**
- FR17: View detailed analysis breakdown
- Use shadcn/ui Cards and Tabs for layout
- Score breakdown could use a waterfall chart or simple list
- Store user's resolved TODO items in local storage or database

---

## Epic 5: Report Conversion

Users can convert analyzed reports and download Power BI + SQL outputs with corporate branding.

### Story 5.1: Initiate Report Conversion

As a user,
I want to initiate conversion of an analyzed report,
So that I can generate Power BI and SQL outputs.

**Acceptance Criteria:**

**Given** a report has been analyzed
**When** the user clicks "Convert Report"
**Then** conversion begins with a progress indicator
**And** the UI shows current step: "Generating SQL...", "Building Power BI...", etc.
**And** the user can cancel conversion (partial files are discarded)

**Given** conversion is initiated
**When** Snowflake is not configured
**Then** the user is warned: "Snowflake not configured - SQL scripts will use placeholder schema"
**And** the user can proceed or cancel to configure Snowflake first

**Given** conversion is in progress
**When** viewing the UI
**Then** estimated time remaining is not shown (per guidelines)
**And** a progress bar or spinner indicates activity
**And** navigation away shows a confirmation dialog

**Given** conversion completes successfully
**When** all outputs are ready
**Then** the view transitions to the Conversion Summary
**And** all output files are stored for download
**And** the conversion is logged for audit (Epic 7)

**Given** conversion fails
**When** an error occurs
**Then** partial outputs are discarded (NFR15 - complete or nothing)
**And** an error message explains the failure
**And** the user can view the analysis and retry

**Technical Notes:**
- FR18: Initiate conversion of analyzed report
- NFR15: Conversion outputs complete or not generated
- Use background task with SSE/polling for progress updates
- Store conversion outputs in file storage with database reference

---

### Story 5.2: Snowflake SQL Script Generation

As a user,
I want SQL scripts generated for Snowflake,
So that report data sources work on our target database platform.

**Acceptance Criteria:**

**Given** a report has datasets with embedded SQL queries
**When** generating SQL scripts
**Then** each query is converted to Snowflake-compatible syntax
**And** SQL Server-specific functions are mapped to Snowflake equivalents
**And** CONVERT/CAST syntax is updated for Snowflake

**Given** the Snowflake connection is configured
**When** generating SQL scripts
**Then** the configured schema is used in table references
**And** database.schema.table naming convention is applied
**And** warehouse context is included in script comments

**Given** a dataset references a stored procedure
**When** that SP can be auto-converted (simple SELECT wrapper)
**Then** a corresponding SELECT statement is generated
**And** the original SP reference is noted in comments

**Given** a dataset references a stored procedure
**When** that SP cannot be auto-converted (complex logic)
**Then** a placeholder script is generated with TODO comments
**And** the original SP call is preserved in comments

**Given** parameters are used in queries
**When** generating SQL scripts
**Then** parameters are converted to Snowflake session variables format
**And** a parameter declaration section is included
**And** default values from RDL are preserved

**Given** SQL generation completes
**When** scripts are produced
**Then** each dataset gets a separate .sql file
**And** a combined "all_scripts.sql" is also generated
**And** scripts are formatted for readability

**Technical Notes:**
- FR20: Generate Snowflake SQL scripts
- Create SQL dialect converter service
- Common conversions: GETDATE() -> CURRENT_TIMESTAMP(), ISNULL -> COALESCE, TOP N -> LIMIT N
- Handle date functions, string functions, type casting

---

### Story 5.3: Rule-Based Stored Procedure Rewriting

As the system,
I want to automatically rewrite simple stored procedures as SELECT statements,
So that more reports can be converted without manual SP migration.

**Acceptance Criteria:**

**Given** a stored procedure is identified in analysis
**When** evaluating for auto-rewrite
**Then** the SP is classified as:
  - **Simple**: Single SELECT, no control flow, no temp tables, no cursors
  - **Moderate**: Multiple SELECTs with UNION, simple IF/ELSE
  - **Complex**: Temp tables, loops, cursors, dynamic SQL, transactions

**Given** a Simple stored procedure
**When** auto-rewrite is applied
**Then** the SELECT statement is extracted
**And** parameters are converted to Snowflake variables
**And** SQL Server functions are mapped to Snowflake
**And** the result is a standalone SELECT query

**Given** a Moderate stored procedure
**When** auto-rewrite is attempted
**Then** an attempt is made to flatten UNIONs
**And** if successful, a combined SELECT is generated
**And** if unsuccessful, it is flagged for manual review

**Given** a Complex stored procedure
**When** auto-rewrite is evaluated
**Then** no automatic rewrite is attempted
**And** a TODO item is generated: "Manual conversion required for [SP name]"
**And** the original SP definition is included in comments if available

**Given** auto-rewrite produces a query
**When** generating output
**Then** the original SP call is documented
**And** confidence level is noted (high/medium/low)
**And** suggestions for validation are included

**Technical Notes:**
- FR21: Rewrite simple stored procedures as SELECT statements
- Use AST parsing for SP analysis (sqlparse library)
- Start with conservative approach - err on side of flagging for manual review
- Store rewrite confidence in conversion record

---

### Story 5.4: Power BI Report Generation

As a user,
I want a Power BI report file (.pbix) generated from the SSRS report,
So that I have a converted report ready for Power BI Desktop.

**Acceptance Criteria:**

**Given** analysis and SQL generation are complete
**When** generating the Power BI file
**Then** a valid .pbix file is created
**And** the file opens in Power BI Desktop without errors (NFR10)

**Given** the original report has tables
**When** converting to Power BI
**Then** Table visuals are created with equivalent columns
**And** Grouping is converted to Group By in the visual
**And** Sorting settings are preserved

**Given** the original report has charts
**When** converting to Power BI
**Then** Equivalent Power BI chart types are used
**And** Data series mappings are preserved
**And** Axis configurations are converted

**Given** the original report has a Matrix
**When** converting to Power BI
**Then** A Matrix visual is created
**And** Row groups become Row fields
**And** Column groups become Column fields
**And** Values are mapped to the Value well

**Given** the original report has unsupported visuals (Map, Gauge, custom)
**When** converting to Power BI
**Then** A placeholder visual is created
**And** A text note indicates: "Manual conversion required for [visual type]"
**And** A TODO item is generated

**Given** a branding template is configured (Story 5.5)
**When** generating the Power BI file
**Then** the template theme is applied
**And** Corporate colors, fonts, and logo are included
**And** Page layout matches template specifications

**Given** Power BI generation completes
**When** the file is ready
**Then** the file is stored with a meaningful name: "{report_name}_converted.pbix"
**And** file integrity is verified (valid ZIP structure)

**Technical Notes:**
- FR19: Generate Power BI report file (.pbix)
- FR24: Apply branding template
- FR31: Auto-apply template during conversion
- NFR10: Valid .pbix files openable in Power BI Desktop
- PBIX is a ZIP file with defined structure
- Use pbi-tools library or direct manipulation

---

### Story 5.5: Branding Template Management

As an admin,
I want to upload and manage a Power BI branding template,
So that all converted reports have consistent corporate branding.

**Acceptance Criteria:**

**Given** the admin is on the Settings page
**When** viewing the Branding section
**Then** the current template status is displayed:
  - If configured: Template name, upload date, preview thumbnail
  - If not configured: "No branding template configured"

**Given** no template is configured
**When** the admin clicks "Upload Template"
**Then** a file picker allows selection of .pbit files
**And** only .pbit files are accepted
**And** file size is validated (max 50MB)

**Given** a valid .pbit file is selected
**When** upload completes
**Then** the template is validated (opens without errors)
**And** success message: "Branding template uploaded successfully"
**And** the template preview updates

**Given** a template already exists
**When** the admin uploads a new template
**Then** they are prompted: "Replace existing template?"
**And** selecting "Yes" replaces the old template
**And** selecting "No" cancels the upload

**Given** a template is configured
**When** the admin clicks "Remove Template"
**Then** they are prompted to confirm
**And** removing clears the template
**And** future conversions will not have branding applied

**Given** a template is configured
**When** the admin clicks "Download Current"
**Then** the current template file is downloaded
**And** useful for backup or sharing across environments

**Technical Notes:**
- FR28: Upload Power BI branding template
- FR29: View currently configured template
- FR30: Replace existing template
- Store template in file storage with database reference
- Validate PBIT structure on upload

---

### Story 5.6: Download Conversion Outputs

As a user,
I want to download the generated Power BI file and SQL scripts,
So that I can use them in my migration workflow.

**Acceptance Criteria:**

**Given** conversion has completed successfully
**When** viewing the Conversion Summary
**Then** download buttons are displayed for:
  - Power BI file (.pbix)
  - Combined SQL scripts (.sql)
  - Individual SQL scripts (.zip)
  - Analysis report (.json or .pdf)

**Given** the user clicks "Download Power BI"
**When** the download initiates
**Then** the .pbix file downloads with name: "{report_name}_converted.pbix"
**And** appropriate MIME type is set

**Given** the user clicks "Download SQL Scripts"
**When** the download initiates
**Then** the combined SQL file downloads
**And** file name: "{report_name}_snowflake_scripts.sql"

**Given** the user clicks "Download All Scripts (ZIP)"
**When** the download initiates
**Then** a ZIP containing individual SQL files downloads
**And** files are organized: /scripts/{dataset_name}.sql

**Given** outputs are older than 30 days
**When** the user attempts download
**Then** the files are still available (retained until explicitly deleted)
**And** a note shows: "Generated on [date]"

**Given** conversion failed or was incomplete
**When** viewing the report
**Then** no download buttons are shown
**And** a message indicates: "Conversion incomplete - no files available"

**Technical Notes:**
- FR25: Download generated Power BI file
- FR26: Download generated Snowflake SQL scripts
- Use streaming downloads for large files
- Include Content-Disposition header for filename

---

### Story 5.7: Conversion Summary View

As a user,
I want to view a summary of what was converted and what needs attention,
So that I understand the conversion output completely.

**Acceptance Criteria:**

**Given** conversion has completed
**When** viewing the Conversion Summary
**Then** a summary card displays:
  - Report name and original path
  - Conversion timestamp
  - Overall status (Success/Partial/Failed)
  - File sizes for generated outputs

**Given** the Conversion Summary
**When** viewing the "What Was Converted" section
**Then** a list shows successfully converted elements:
  - Datasets converted to SQL (count)
  - Visuals converted to Power BI (count by type)
  - Expressions auto-converted (count)
  - SPs auto-rewritten (count)

**Given** the Conversion Summary
**When** viewing the "What Needs Attention" section
**Then** a list shows items requiring manual work:
  - SPs not auto-rewritten (with names)
  - Visuals requiring manual adjustment (with types)
  - Expressions flagged for review (with count)
  - Link to full TODO list from analysis

**Given** the Conversion Summary
**When** viewing the "Files Generated" section
**Then** each file is listed with:
  - File name and type
  - File size
  - Download button

**Given** the Conversion Summary
**When** the user wants to view original analysis
**Then** a "View Analysis" link returns to the Analysis Results
**And** a "Convert Again" option re-runs conversion with fresh settings

**Given** the user is done with the report
**When** they click "Back to Browser"
**Then** they return to the folder view
**And** the converted report shows a "Converted" badge in the list

**Technical Notes:**
- FR27: View conversion output summary
- Store conversion metadata in conversions table
- Link conversion to analysis record
- Show timestamps in user's local timezone

---

## Epic 6: AI-Assisted Conversion

Complex stored procedures get intelligent AI assistance for better conversion accuracy.

### Story 6.1: Ollama Service Integration

As the system,
I want to connect to a local Ollama instance,
So that AI capabilities are available for complex conversion scenarios.

**Acceptance Criteria:**

**Given** Ollama is configured and enabled (from Story 2.6)
**When** the system initializes
**Then** a connection to Ollama is established
**And** the configured model availability is verified
**And** connection status is reported to the health dashboard

**Given** the Ollama service
**When** making API calls
**Then** the configured host URL is used
**And** timeout settings are respected
**And** retry logic handles transient failures (3 retries with backoff)

**Given** Ollama returns a response
**When** processing the response
**Then** the response is validated for expected format
**And** token usage is logged for monitoring
**And** response time is tracked for performance analysis

**Given** the model is not found in Ollama
**When** attempting to use AI features
**Then** a clear error is returned: "Model [name] not available"
**And** the admin is directed to install the model
**And** rule-based fallback is automatically engaged

**Given** the Ollama API format changes
**When** an unexpected response is received
**Then** the error is logged with details
**And** the system falls back to rule-based conversion
**And** the user is informed AI assistance is temporarily unavailable

**Technical Notes:**
- FR49: Connect to local Ollama instance
- Use ollama-python library or direct REST calls
- Implement circuit breaker pattern for reliability
- Model: codellama:13b (configurable)

---

### Story 6.2: AI-Assisted Stored Procedure Analysis and Rewrite

As the system,
I want to use AI to analyze and rewrite complex stored procedures,
So that more SPs can be automatically converted to SELECT statements.

**Acceptance Criteria:**

**Given** a stored procedure is classified as "Moderate" or "Complex" (from Story 5.3)
**When** AI assistance is enabled
**Then** the SP definition is sent to Ollama for analysis
**And** a structured prompt guides the AI to produce a Snowflake SELECT

**Given** the AI prompt for SP rewriting
**When** constructing the request
**Then** the prompt includes:
  - Original SP definition (SQL Server syntax)
  - Target database (Snowflake)
  - Available tables schema (if configured)
  - Expected output format (SELECT statement + confidence + explanation)

**Given** Ollama returns an AI-generated rewrite
**When** processing the response
**Then** the generated SELECT is extracted
**And** the SQL is validated for basic syntax
**And** confidence level is parsed (high/medium/low)
**And** explanation is captured for user review

**Given** the AI-generated SELECT passes validation
**When** storing the result
**Then** the rewrite is marked as "AI-Generated"
**And** the original SP is preserved in comments
**And** a note indicates: "Review recommended before production use"

**Given** the AI-generated SELECT fails validation
**When** handling the failure
**Then** the failed attempt is logged
**And** the SP is flagged for manual review
**And** the AI response is stored for debugging

**Given** AI rewrite takes longer than timeout (60s default)
**When** the timeout occurs
**Then** the request is cancelled
**And** the SP is flagged for manual review
**And** rule-based conversion is attempted as fallback

**Technical Notes:**
- FR22: AI-assisted complex SP rewrite
- FR50: Send SP logic to Ollama for analysis
- FR51: Apply AI-generated SELECT rewrites
- Use structured prompts with few-shot examples
- Temperature: 0.2 for consistent output

---

### Story 6.3: Uncertain Conversion Flagging

As a user,
I want uncertain AI conversions clearly flagged,
So that I know which outputs need manual verification.

**Acceptance Criteria:**

**Given** AI generates a conversion
**When** the confidence is "low" or "medium"
**Then** the conversion is flagged as "Uncertain"
**And** a visual indicator (yellow warning icon) is displayed
**And** the TODO list includes a review item

**Given** an uncertain conversion
**When** viewing the conversion details
**Then** the following are displayed:
  - Confidence level with explanation
  - AI's reasoning for uncertainty
  - Original SP for comparison
  - Generated SELECT for review

**Given** a conversion is flagged uncertain
**When** the user reviews it
**Then** they can mark it as "Verified" (accepting the conversion)
**Or** they can mark it as "Rejected" (keeping for manual work)

**Given** multiple uncertain conversions exist
**When** viewing the Conversion Summary
**Then** a count is shown: "X conversions flagged for review"
**And** an "Uncertain Conversions" section lists them

**Given** the user accepts an uncertain conversion
**When** marking as "Verified"
**Then** the conversion is included in the output
**And** the audit log records the user's verification decision

**Given** the user rejects an uncertain conversion
**When** marking as "Rejected"
**Then** the conversion is excluded from output
**And** the original SP remains in the TODO list
**And** a placeholder is used in the SQL scripts

**Technical Notes:**
- FR23: Flag uncertain SP conversions for manual review
- Confidence thresholds: High (>80%), Medium (50-80%), Low (<50%)
- Store verification decisions in conversions table
- Include decision in audit log (Epic 7)

---

### Story 6.4: AI-Generated TODO Guidance

As a user,
I want human-readable guidance in TODO items,
So that I understand exactly what manual work is needed and how to approach it.

**Acceptance Criteria:**

**Given** a TODO item is generated for a complex SP
**When** AI assistance is enabled
**Then** Ollama generates a guidance paragraph explaining:
  - What makes this SP complex (specific elements)
  - Suggested approach for manual conversion
  - Potential challenges to watch for
  - Relevant Snowflake documentation links (if applicable)

**Given** AI-generated guidance
**When** displayed in the TODO list
**Then** the guidance is clearly formatted with:
  - Summary (1-2 sentences)
  - Detailed explanation (expandable)
  - Suggested steps (numbered list)

**Given** a TODO item for expression conversion
**When** AI generates guidance
**Then** the guidance includes:
  - What the expression does in plain language
  - DAX equivalent (if applicable)
  - Power BI visual configuration needed

**Given** AI guidance generation fails
**When** an error occurs
**Then** a generic template guidance is used instead
**And** the TODO item is still created
**And** the failure is logged

**Given** the user finds guidance helpful
**When** viewing TODO items
**Then** a "Copy Guidance" button allows copying text
**And** useful for documentation or ticketing

**Technical Notes:**
- FR52: AI-generated human-readable TODO guidance
- Use separate, focused prompts for guidance (not combined with rewrite)
- Cache guidance responses to reduce API calls for similar items
- Include fallback templates for common scenarios

---

### Story 6.5: Graceful Degradation Without AI

As the system,
I want to function fully when Ollama is unavailable,
So that users can still convert reports using rule-based methods.

**Acceptance Criteria:**

**Given** Ollama is disabled in settings
**When** conversion is initiated
**Then** all AI-related steps are skipped
**And** rule-based conversion proceeds normally
**And** a notice displays: "AI assistance disabled - using rule-based conversion only"

**Given** Ollama is enabled but unavailable (connection failed)
**When** conversion is initiated
**Then** the system falls back to rule-based conversion
**And** a warning displays: "AI service unavailable - proceeding with rule-based conversion"
**And** the user can continue without interruption

**Given** Ollama becomes unavailable mid-conversion
**When** an AI request fails
**Then** that specific item falls back to rule-based
**And** other items continue processing
**And** the summary shows: "X items used AI, Y items used rule-based fallback"

**Given** AI fallback occurs
**When** viewing conversion results
**Then** each item indicates its conversion method:
  - "Rule-based conversion"
  - "AI-assisted conversion"
  - "AI unavailable - rule-based fallback"

**Given** rule-based conversion cannot handle an item
**When** no AI is available
**Then** the item is flagged for manual conversion
**And** a generic TODO is created (without AI guidance)
**And** the conversion continues with remaining items

**Given** AI has been unavailable for multiple conversions
**When** viewing the health dashboard
**Then** a persistent warning shows: "AI service has been unavailable"
**And** last successful AI connection is displayed

**Technical Notes:**
- NFR12: Graceful degradation if Ollama unavailable
- Implement feature flags for easy AI enable/disable
- Log all fallback events for operational visibility
- Consider retry queue for failed AI requests (future enhancement)

---

## Epic 7: Audit & Compliance

Admin can track all user actions for enterprise compliance requirements.

### Story 7.1: Audit Log Database and Service

As the system,
I want a robust audit logging infrastructure,
So that all user actions can be tracked for compliance requirements.

**Acceptance Criteria:**

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

**Given** the audit service
**When** an auditable event occurs
**Then** the event is logged asynchronously (non-blocking)
**And** the log entry includes all required fields
**And** sensitive data is not stored in plain text (passwords, tokens)

**Given** the database
**When** audit logs accumulate
**Then** logs are retained indefinitely until explicitly deleted (NFR17)
**And** an index exists on timestamp for efficient querying
**And** an index exists on user_id for user-based filtering

**Given** the audit service fails to write
**When** an error occurs
**Then** the error is logged to application logs
**And** the original user action is not blocked
**And** the failed audit entry is queued for retry

**Technical Notes:**
- NFR17: Audit logs retained until explicitly deleted
- NFR19: Configuration persisted across restarts
- Use SQLAlchemy model with Alembic migration
- Consider partitioning by month for large deployments (future)

---

### Story 7.2: Authentication Event Logging

As an admin,
I want all login and logout events logged,
So that I can track who accessed the system and when.

**Acceptance Criteria:**

**Given** a user attempts to log in
**When** login succeeds
**Then** an audit log entry is created with:
  - event_type: LOGIN
  - action: "User logged in"
  - username and user_id
  - status: SUCCESS
  - details: { domain, auth_method }

**Given** a user attempts to log in
**When** login fails
**Then** an audit log entry is created with:
  - event_type: LOGIN
  - action: "Login attempt failed"
  - username (attempted)
  - status: FAILURE
  - details: { reason, domain }

**Given** a user logs out
**When** logout completes
**Then** an audit log entry is created with:
  - event_type: LOGOUT
  - action: "User logged out"
  - username and user_id
  - status: SUCCESS

**Given** a user's session expires
**When** the token is invalidated
**Then** an audit log entry is created with:
  - event_type: LOGOUT
  - action: "Session expired"
  - username and user_id
  - status: SUCCESS
  - details: { expiry_reason: "timeout" }

**Given** multiple failed login attempts from same IP
**When** viewing audit logs
**Then** the pattern is visible for security review
**And** IP addresses are logged for each attempt

**Technical Notes:**
- FR43: Log login events (username, timestamp, success/failure)
- Integrate with Story 1.3 (Windows AD Authentication)
- Include IP address from request headers (X-Forwarded-For if proxied)

---

### Story 7.3: Report Activity Logging

As an admin,
I want all report analysis and conversion events logged,
So that I can track report processing for compliance and debugging.

**Acceptance Criteria:**

**Given** a user triggers report analysis
**When** analysis completes
**Then** an audit log entry is created with:
  - event_type: ANALYSIS
  - action: "Report analyzed"
  - resource_type: "report"
  - resource_id: report path
  - status: SUCCESS
  - details: { score, classification, report_name }

**Given** a user triggers report analysis
**When** analysis fails
**Then** an audit log entry is created with:
  - event_type: ANALYSIS
  - action: "Report analysis failed"
  - resource_id: report path
  - status: FAILURE
  - details: { error_message, error_code }

**Given** a user triggers report conversion
**When** conversion completes
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Report converted"
  - resource_type: "report"
  - resource_id: report path
  - status: SUCCESS
  - details: { output_files, conversion_method, ai_used }

**Given** a user triggers report conversion
**When** conversion fails
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Report conversion failed"
  - resource_id: report path
  - status: FAILURE
  - details: { error_message, stage_failed }

**Given** a user downloads conversion outputs
**When** download completes
**Then** an audit log entry is created with:
  - event_type: CONVERSION
  - action: "Downloaded conversion output"
  - resource_type: "conversion_output"
  - details: { file_type, file_name }

**Technical Notes:**
- FR44: Log analysis events (user, report, timestamp, score)
- FR45: Log conversion events (user, report, timestamp, output files)
- Integrate with Stories 4.1 and 5.1

---

### Story 7.4: Configuration Change Logging

As an admin,
I want all configuration changes logged with before/after values,
So that I can track who changed settings and audit system changes.

**Acceptance Criteria:**

**Given** an admin changes SSRS connection settings
**When** the save completes
**Then** an audit log entry is created with:
  - event_type: CONFIG_CHANGE
  - action: "SSRS connection updated"
  - resource_type: "ssrs_config"
  - details: { changed_fields, old_values (masked), new_values (masked) }

**Given** an admin changes Snowflake connection settings
**When** the save completes
**Then** an audit log entry is created with:
  - event_type: CONFIG_CHANGE
  - action: "Snowflake connection updated"
  - resource_type: "snowflake_config"
  - details: { changed_fields }
  - Note: Credentials are never logged in old/new values

**Given** an admin uploads or replaces a branding template
**When** the upload completes
**Then** an audit log entry is created with:
  - event_type: CONFIG_CHANGE
  - action: "Branding template uploaded" or "replaced"
  - resource_type: "branding_template"
  - details: { old_template_name, new_template_name }

**Given** an admin enables or disables Ollama
**When** the setting changes
**Then** an audit log entry is created with:
  - event_type: CONFIG_CHANGE
  - action: "Ollama setting changed"
  - details: { field: "enabled", old_value, new_value }

**Given** configuration details contain sensitive information
**When** logging changes
**Then** passwords and secrets are replaced with "[REDACTED]"
**And** only field names are logged, not credential values

**Technical Notes:**
- FR46: Log configuration changes (user, setting, old value, new value)
- Create a decorator/middleware for config endpoints
- Use JSON diff for complex configuration objects

---

### Story 7.5: Audit Log Viewer UI

As an admin,
I want to view audit logs through a dedicated interface,
So that I can investigate user activity and troubleshoot issues.

**Acceptance Criteria:**

**Given** the admin navigates to the Audit Logs section
**When** the page loads
**Then** recent audit logs are displayed (last 24 hours by default)
**And** logs are shown in a table with columns: Timestamp, User, Event Type, Action, Status
**And** logs are sorted by timestamp descending (newest first)

**Given** the audit log table
**When** filtering options are used
**Then** logs can be filtered by:
  - Date range (from/to date pickers)
  - Event type (multi-select dropdown)
  - User (search/select dropdown)
  - Status (Success/Failure)
  - Search text (searches action and details)

**Given** filters are applied
**When** viewing results
**Then** the filter criteria are shown as active chips
**And** "Clear Filters" resets to default view
**And** filtered count shows: "Showing X of Y logs"

**Given** an audit log row
**When** the admin clicks to expand
**Then** the full details JSON is displayed in a formatted view
**And** timestamps show full precision with timezone
**And** resource links navigate to related items (if they still exist)

**Given** many audit logs exist
**When** viewing the table
**Then** pagination is implemented (50 logs per page)
**And** "Load More" or page numbers allow navigation
**And** total count is displayed

**Given** real-time logging is desired
**When** the admin clicks "Live Mode"
**Then** new logs appear automatically (polling every 5 seconds)
**And** a indicator shows "Live" status
**And** stopping live mode freezes the current view

**Technical Notes:**
- FR47: Admin can view audit logs
- Use React Query with pagination
- shadcn/ui DataTable component
- Consider virtual scrolling for performance

---

### Story 7.6: Audit Log Export

As an admin,
I want to export audit logs for compliance reporting,
So that I can provide evidence for audits and investigations.

**Acceptance Criteria:**

**Given** the admin is on the Audit Logs page
**When** they click "Export"
**Then** an export dialog appears with options:
  - Date range selection
  - Event type filter (optional)
  - Format selection: CSV, JSON, PDF

**Given** export options are selected
**When** the admin clicks "Generate Export"
**Then** the export is generated server-side
**And** a progress indicator is shown for large exports
**And** the file downloads when ready

**Given** CSV format is selected
**When** the export generates
**Then** the file includes headers: Timestamp, User, Event Type, Action, Resource, Status, Details
**And** the details column contains flattened JSON
**And** the file name includes date range: "audit_logs_2026-01-01_2026-01-31.csv"

**Given** JSON format is selected
**When** the export generates
**Then** the file contains an array of full log objects
**And** all fields are included without redaction
**And** the file is formatted for readability

**Given** PDF format is selected
**When** the export generates
**Then** a formatted report is created with:
  - Title: "ReportLift Audit Log Report"
  - Export date and time
  - Filter criteria applied
  - Table of logs with pagination
  - Summary statistics (total events, by type, by status)

**Given** a very large date range is selected (>10,000 logs)
**When** export is initiated
**Then** the user is warned about export size
**And** they can proceed or narrow the filter
**And** export runs asynchronously with notification on completion

**Given** the export completes
**When** the file is downloaded
**Then** an audit log entry is created for the export action
**And** details include: date range, format, row count

**Technical Notes:**
- FR48: Export audit logs for compliance reporting
- NFR18: Analysis history retained until explicitly deleted
- Use streaming for large CSV exports
- Consider background job for PDF generation
- Include export in audit log (meta-logging)

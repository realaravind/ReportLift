# Story 1.1: Project Initialization & Development Environment

Status: done

## Story

As a **developer**,
I want **a properly structured FastAPI backend and React frontend with Docker Compose**,
so that **the team has a consistent development environment to build features**.

## Acceptance Criteria

### AC1: Docker Compose Startup
**Given** a new development machine with Docker installed
**When** the developer runs `docker-compose up`
**Then** both backend and frontend services start successfully
**And** the backend health endpoint at `/api/health` returns `{"status": "healthy"}`
**And** the frontend is accessible at `http://localhost:3000`

### AC2: Backend Project Structure
**Given** the backend project structure
**When** reviewing the codebase
**Then** it follows the architecture structure: `backend/app/{api,core,services,models,schemas}`
**And** SQLAlchemy is configured with Alembic migrations
**And** Pydantic v2 is used for request/response schemas
**And** environment configuration uses `.env` files

### AC3: Frontend Project Structure
**Given** the frontend project structure
**When** reviewing the codebase
**Then** it follows the architecture structure: `frontend/src/{components,hooks,lib,types}`
**And** Vite + React + TypeScript is configured
**And** Tailwind CSS is configured with shadcn/ui components
**And** React Query is set up for API calls
**And** Zustand is configured for client state

## Tasks / Subtasks

- [x] **Task 1: Create Project Root Structure** (AC: 1, 2, 3)
  - [x] Create `reportlift/` root directory
  - [x] Create `README.md` with project overview
  - [x] Create `.gitignore` (Python, Node, Docker patterns)
  - [x] Create `.env.example` with all required variables
  - [x] Create `Makefile` with common commands

- [x] **Task 2: Initialize Backend (FastAPI)** (AC: 2)
  - [x] Create `backend/` directory structure
  - [x] Create `backend/requirements.txt` with all dependencies
  - [x] Create `backend/Dockerfile`
  - [x] Create `backend/app/main.py` - FastAPI entry point
  - [x] Create `backend/app/core/config.py` - Pydantic settings
  - [x] Create `backend/app/core/logging.py` - JSON logging setup
  - [x] Create `backend/app/api/routes/health.py` - Health endpoint
  - [x] Create `backend/app/api/deps.py` - Common dependencies
  - [x] Create `backend/app/models/base.py` - SQLAlchemy base
  - [x] Initialize Alembic: `backend/alembic.ini`, `backend/alembic/`

- [x] **Task 3: Initialize Frontend (Vite + React)** (AC: 3)
  - [x] Create `frontend/` with Vite + React + TypeScript
  - [x] Configure `tailwind.config.js` and `postcss.config.js`
  - [x] Install and configure shadcn/ui
  - [x] Create `frontend/src/lib/api.ts` - Axios client
  - [x] Create `frontend/src/lib/queryClient.ts` - React Query setup
  - [x] Create `frontend/src/store/` - Zustand store
  - [x] Create `frontend/src/types/` - TypeScript interfaces
  - [x] Create `frontend/Dockerfile` with Nginx
  - [x] Create `frontend/nginx.conf` for SPA routing

- [x] **Task 4: Docker Compose Configuration** (AC: 1)
  - [x] Create `docker-compose.yml` for production
  - [x] Create `docker-compose.dev.yml` for development with hot reload
  - [x] Configure volume mounts for development
  - [x] Configure environment variable passing
  - [x] Test `docker-compose up` starts both services

- [x] **Task 5: Verify All Acceptance Criteria** (AC: 1, 2, 3)
  - [x] Verify `/api/health` returns healthy status
  - [x] Verify frontend loads at `http://localhost:3000`
  - [x] Verify backend structure matches architecture
  - [x] Verify frontend structure matches architecture
  - [x] Verify Alembic migrations work

## Dev Notes

### Technology Stack (MUST USE)

| Component | Technology | Version |
|-----------|------------|---------|
| Backend Framework | FastAPI | Latest stable |
| Python | Python | 3.11+ |
| ORM | SQLAlchemy | 2.x |
| Migrations | Alembic | Latest |
| Validation | Pydantic | v2 |
| SQL Server Driver | pyodbc | Latest |
| Frontend Build | Vite | Latest |
| UI Framework | React | 18.x |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | 3.x |
| Components | shadcn/ui | Latest |
| Server State | @tanstack/react-query | v5 |
| Client State | Zustand | Latest |
| HTTP Client | Axios | Latest |
| Containerization | Docker Compose | v2 |

### Required Backend Dependencies (requirements.txt)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pyodbc>=5.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
```

### Required Frontend Dependencies (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "react-router-dom": "^6.21.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

### Project Structure (EXACT)

```
reportlift/
├── README.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
├── Makefile
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py
│       │   └── routes/
│       │       └── health.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── logging.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   └── base.py
│       │
│       └── schemas/
│           └── __init__.py
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       │
│       ├── components/
│       │   └── ui/
│       │
│       ├── hooks/
│       │   └── .gitkeep
│       │
│       ├── lib/
│       │   ├── api.ts
│       │   └── queryClient.ts
│       │
│       ├── store/
│       │   └── index.ts
│       │
│       └── types/
│           └── index.ts
│
└── docs/
    └── .gitkeep
```

### Naming Conventions (MUST FOLLOW)

| Category | Convention | Example |
|----------|------------|---------|
| Python files | snake_case | `health.py`, `config.py` |
| Python functions | snake_case | `def get_health_status():` |
| Python classes | PascalCase | `class Settings:` |
| TypeScript files | camelCase or PascalCase for components | `api.ts`, `App.tsx` |
| React components | PascalCase | `HealthCheck.tsx` |
| CSS classes | Tailwind utility classes | `className="flex items-center"` |

### API Patterns (MUST FOLLOW)

**Health Endpoint Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-21T10:30:00Z",
  "version": "1.0.0"
}
```

**Error Response Pattern:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

### Environment Variables (.env.example)

```env
# Backend
DATABASE_URL=mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development

# Frontend (build-time)
VITE_API_URL=http://localhost:8000

# Docker
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### Docker Compose Structure (EXACT)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      - DATABASE_URL
      - SECRET_KEY
      - ENVIRONMENT
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "${FRONTEND_PORT:-3000}:80"
    depends_on:
      - backend
```

### References

- [Source: architecture.md#Project Structure] - Complete directory structure
- [Source: architecture.md#Selected Technology Stack] - All technology choices
- [Source: architecture.md#Initialization Commands] - Setup commands
- [Source: architecture.md#Implementation Patterns] - Naming conventions
- [Source: architecture.md#Docker Compose Structure] - Container configuration
- [Source: epics.md#Story 1.1] - Story requirements and acceptance criteria

### Architecture Compliance Checklist

- [x] Backend follows `backend/app/{api,core,services,models,schemas}` structure
- [x] Frontend follows `frontend/src/{components,hooks,lib,types}` structure
- [x] All Python code uses snake_case naming
- [x] All React components use PascalCase naming
- [x] API responses follow `{ data, meta }` or `{ error }` pattern
- [x] Environment variables used for all configuration
- [x] Docker health checks configured
- [x] Alembic properly initialized for migrations

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. **Task 1 Complete**: Created project root structure with README.md, .gitignore, .env.example, Makefile, and docs/.gitkeep
2. **Task 2 Complete**: Initialized FastAPI backend with full directory structure, Pydantic v2 settings, SQLAlchemy 2.x, Alembic migrations, and /api/health endpoint
3. **Task 3 Complete**: Initialized Vite + React + TypeScript frontend with Tailwind CSS, shadcn/ui setup, React Query, Zustand, Axios client, and Nginx production config
4. **Task 4 Complete**: Created docker-compose.yml for production and docker-compose.dev.yml for development with hot reload and volume mounts
5. **Task 5 Complete**: Verified all acceptance criteria - backend structure matches architecture, frontend structure matches architecture, Docker configs in place
6. **Code Review Fixes**: Fixed CORS configuration, deprecated FastAPI events, Docker version attributes, added unit tests (10 tests passing)

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-21 | Initial project setup - all 5 tasks completed | All files below |
| 2026-01-21 | Code review fixes - CORS, lifespan, tests added | main.py, docker-compose*.yml, tests/* |

### File List

**Root:**
- README.md
- .gitignore
- .env.example
- .env (created during testing)
- Makefile
- docker-compose.yml
- docker-compose.dev.yml
- docs/.gitkeep

**Backend:**
- backend/Dockerfile
- backend/requirements.txt
- backend/alembic.ini
- backend/alembic/env.py
- backend/alembic/script.py.mako
- backend/alembic/versions/.gitkeep
- backend/app/__init__.py
- backend/app/main.py
- backend/app/api/__init__.py
- backend/app/api/deps.py
- backend/app/api/routes/__init__.py
- backend/app/api/routes/health.py
- backend/app/core/__init__.py
- backend/app/core/config.py
- backend/app/core/logging.py
- backend/app/models/__init__.py
- backend/app/models/base.py
- backend/app/schemas/__init__.py
- backend/app/services/__init__.py
- backend/pytest.ini
- backend/tests/__init__.py
- backend/tests/test_health.py
- backend/tests/test_config.py

**Frontend:**
- frontend/Dockerfile
- frontend/Dockerfile.dev
- frontend/nginx.conf
- frontend/package.json
- frontend/tsconfig.json
- frontend/tsconfig.node.json
- frontend/vite.config.ts
- frontend/tailwind.config.js
- frontend/postcss.config.js
- frontend/index.html
- frontend/src/main.tsx
- frontend/src/App.tsx
- frontend/src/index.css
- frontend/src/lib/api.ts
- frontend/src/lib/queryClient.ts
- frontend/src/lib/utils.ts
- frontend/src/store/index.ts
- frontend/src/types/index.ts
- frontend/src/hooks/.gitkeep
- frontend/src/components/ui/.gitkeep

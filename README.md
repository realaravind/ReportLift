# ReportLift

SSRS-to-Power BI Migration Intelligence Platform

## Overview

ReportLift is an enterprise tool that analyzes SSRS (SQL Server Reporting Services) reports and provides intelligent assistance for migrating them to Power BI with Snowflake as the data source.

## Features

- **SSRS Report Browser**: Browse and select reports from your SSRS server
- **Report Analysis**: Automated analysis of report complexity and conversion difficulty
- **Conversion Engine**: Generate Power BI reports and Snowflake SQL scripts
- **AI-Assisted Migration**: Ollama-powered stored procedure rewriting
- **Audit & Compliance**: Full audit logging for enterprise compliance

## Quick Start

### Prerequisites

- Docker and Docker Compose v2
- Git

### Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd reportlift
   ```

2. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Start development environment:
   ```bash
   make dev
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Production

```bash
make up
```

## Project Structure

```
reportlift/
├── backend/          # FastAPI backend
├── frontend/         # React frontend (Vite + TypeScript)
├── docs/             # Documentation
├── docker-compose.yml
└── docker-compose.dev.yml
```

## Technology Stack

### Backend
- FastAPI (Python 3.11+)
- SQLAlchemy 2.x with Alembic migrations
- Pydantic v2 for validation

### Frontend
- React 18 with TypeScript
- Vite build tool
- Tailwind CSS with shadcn/ui
- React Query for server state
- Zustand for client state

## Development

### Running Tests

```bash
# Backend tests
make test-backend

# Frontend tests
make test-frontend
```

### Code Quality

```bash
make lint
```

## License

Proprietary - All rights reserved

# ReportLift Makefile
# Common development commands

.PHONY: help dev up down build logs clean test lint

# Default target
help:
	@echo "ReportLift Development Commands"
	@echo "================================"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment with hot reload"
	@echo "  make up           - Start production containers"
	@echo "  make down         - Stop all containers"
	@echo "  make build        - Build all containers"
	@echo "  make logs         - View container logs"
	@echo "  make clean        - Remove containers, volumes, and build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests only"
	@echo "  make test-frontend - Run frontend tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-new  - Create new migration"

# Development
dev:
	docker-compose -f docker-compose.dev.yml up --build

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --rmi local
	rm -rf backend/__pycache__ backend/.pytest_cache
	rm -rf frontend/node_modules frontend/dist

# Testing
test: test-backend test-frontend

test-backend:
	docker-compose exec backend pytest -v

test-frontend:
	docker-compose exec frontend npm test

# Code Quality
lint:
	docker-compose exec backend ruff check .
	docker-compose exec frontend npm run lint

format:
	docker-compose exec backend ruff format .
	docker-compose exec frontend npm run format

# Database
migrate:
	docker-compose exec backend alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

# Health check
health:
	@curl -s http://localhost:8000/api/health | python -m json.tool || echo "Backend not running"
	@curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:3000 || echo "Frontend not running"

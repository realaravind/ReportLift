"""ReportLift Backend - FastAPI Application Entry Point."""

import logging
import sys
from contextlib import asynccontextmanager

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, auth, oauth, ssrs, analysis, todos, conversion, templates, audit
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import SecurityHeadersMiddleware
from app.services.credential_store import init_credential_store, CredentialStoreError

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


def _init_encryption() -> None:
    """Initialize credential encryption on startup.

    In development mode without an encryption key, generates a temporary key.
    In production, fails if ENCRYPTION_KEY is not set.
    """
    encryption_key = settings.encryption_key

    if not encryption_key:
        if settings.environment == "production":
            logger.critical(
                "FATAL: ENCRYPTION_KEY environment variable is required in production. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
            sys.exit(1)
        else:
            # Generate temporary key for development
            encryption_key = Fernet.generate_key().decode()
            logger.warning(
                "No ENCRYPTION_KEY configured. Using temporary key for development. "
                "Set ENCRYPTION_KEY in .env for persistent credential storage."
            )

    try:
        init_credential_store(encryption_key)
        logger.info("Credential store initialized successfully")
    except CredentialStoreError as e:
        logger.critical("FATAL: Failed to initialize credential store: %s", e.message)
        sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    _init_encryption()
    logger.info("ReportLift API started successfully")
    yield
    # Shutdown
    logger.info("ReportLift API shutting down")


# Create FastAPI application
app = FastAPI(
    title="ReportLift API",
    description="SSRS-to-Power BI Migration Intelligence Platform",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS - allow multiple frontend ports for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8502",
        "https://localhost:8502",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(oauth.router, prefix="/api/v1", tags=["oauth"])
app.include_router(settings_routes.router, prefix="/api/v1", tags=["settings"])
app.include_router(ssrs.router, prefix="/api/v1", tags=["ssrs"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(todos.router, tags=["todos"])
app.include_router(conversion.router, prefix="/api/v1", tags=["conversions"])
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])

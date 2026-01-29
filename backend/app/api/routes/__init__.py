# API Routes
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.settings import router as settings_router
from app.api.routes.ssrs import router as ssrs_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.todos import router as todos_router
from app.api.routes.templates import router as templates_router
from app.api.routes.audit import router as audit_router

__all__ = [
    "health_router",
    "auth_router",
    "oauth_router",
    "settings_router",
    "ssrs_router",
    "analysis_router",
    "todos_router",
    "templates_router",
    "audit_router",
]

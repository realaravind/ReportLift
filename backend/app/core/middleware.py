"""Security middleware and request utilities."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extract the client IP address from the request.

    Handles proxy headers (X-Forwarded-For, X-Real-IP) for reverse proxy scenarios.
    The first IP in X-Forwarded-For is typically the original client.

    Args:
        request: The incoming HTTP request

    Returns:
        Client IP address as string, or "unknown" if not determinable
    """
    # Check for X-Forwarded-For header (most common proxy header)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # First IP in the list is the original client
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header (nginx proxy)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str | None:
    """Extract the user agent string from the request.

    Args:
        request: The incoming HTTP request

    Returns:
        User agent string, or None if not present
    """
    return request.headers.get("user-agent")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS): Forces HTTPS for future requests
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - Content-Security-Policy: Controls resource loading
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Referrer-Policy: Controls referrer information
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Only add HSTS in production (requires HTTPS)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Always add these headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - restrictive default
        # Adjust as needed for specific application requirements
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for UI frameworks
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response

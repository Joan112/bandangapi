"""
Middleware para headers de seguridad
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para agregar headers de seguridad HTTP
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HSTS - HTTP Strict Transport Security
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Content-Security-Policy (básica)
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response

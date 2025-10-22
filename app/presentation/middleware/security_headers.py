"""
Middleware para headers de seguridad
"""

from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para agregar headers de seguridad HTTP
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response: Response = await call_next(request)

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

        # Content-Security-Policy - Configuración segura pero funcional
        # Extrae el dominio de Supabase dinámicamente
        supabase_domain = settings.SUPABASE_URL.replace("https://", "").replace(
            "http://", ""
        )

        # Detectar si es ruta de documentación (Swagger/ReDoc)
        is_docs_route = request.url.path in [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        ]

        # CSP más permisivo para documentación (permite CDN de Swagger UI)
        # SECURITY NOTE: Solo rutas de docs permiten cdn.jsdelivr.net
        # Las rutas de producción mantienen CSP estricto
        if is_docs_route:
            csp_directives = [
                "default-src 'self'",
                f"connect-src 'self' https://{supabase_domain} https://*.supabase.co",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' data: https://cdn.jsdelivr.net",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests",
            ]
        else:
            # CSP estricto para rutas de producción
            csp_directives = [
                "default-src 'self'",
                f"connect-src 'self' https://{supabase_domain} https://*.supabase.co",
                "script-src 'self' 'unsafe-inline'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests",
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response

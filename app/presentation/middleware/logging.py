"""
Middleware para logging de requests y responses
"""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging de requests y responses
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Capturar tiempo de inicio
        start_time = time.time()

        # Log del request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
            },
        )

        # Procesar request
        response: Response = await call_next(request)

        # Calcular duración
        duration = time.time() - start_time

        # Log del response
        logger.info(
            f"Response: {response.status_code} ({duration:.3f}s)",
            extra={
                "status_code": response.status_code,
                "duration": duration,
                "path": request.url.path,
            },
        )

        # Agregar header de duración
        response.headers["X-Process-Time"] = str(duration)

        return response

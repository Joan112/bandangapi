"""
Middleware para logging de requests y responses
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging de requests y responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
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
        response = await call_next(request)

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

"""
Middleware para rate limiting
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Configurar limiter con almacenamiento en memoria
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
        f"{settings.RATE_LIMIT_PER_HOUR}/hour",
    ],
)


def get_rate_limiter() -> Limiter:
    """
    Obtener instancia del rate limiter

    Returns:
        Limiter configurado
    """
    return limiter

"""
Aplicación principal FastAPI
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import (
    BandangWebError,
    DuplicateEntityError,
    EntityNotFoundError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    ValidationError,
)
from app.presentation.api.router import api_router
from app.presentation.middleware.logging import LoggingMiddleware
from app.presentation.middleware.rate_limit import get_rate_limiter
from app.presentation.middleware.security_headers import SecurityHeadersMiddleware

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle events de la aplicación

    Args:
        app: Instancia de FastAPI
    """
    # Startup
    logger.info("Iniciando aplicación BandangWeb API...")

    # Inicialización de la aplicación
    logger.info("Aplicación inicializada correctamente")

    yield

    # Shutdown
    logger.info("Cerrando aplicación BandangWeb API...")

    # Limpieza de recursos
    logger.info("Recursos liberados correctamente")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API con Clean Architecture, FastAPI y PostgreSQL",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configurar CORS
# Combinar origins de configuración con los hardcoded para producción
cors_origins = [
    "https://bandanuevageneracion.com",
    "https://www.bandanuevageneracion.com",
    "http://localhost:3000",  # Para desarrollo local
]

# Agregar origins adicionales de la configuración si existen
if settings.BACKEND_CORS_ORIGINS:
    cors_origins.extend(settings.BACKEND_CORS_ORIGINS)

# Eliminar duplicados manteniendo el orden
cors_origins = list(dict.fromkeys(cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    # SECURITY: Especificar métodos explícitamente en lugar de wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    # SECURITY: Especificar headers necesarios en lugar de wildcard
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    max_age=3600,  # Cache preflight requests por 1 hora
)

# Agregar middlewares custom
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Configurar rate limiting
limiter = get_rate_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Exception handlers personalizados
@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    """Handler para EntityNotFoundError"""
    return JSONResponse(
        status_code=404, content={"detail": str(exc), "entity": exc.entity}
    )


@app.exception_handler(DuplicateEntityError)
async def duplicate_entity_handler(
    request: Request, exc: DuplicateEntityError
) -> JSONResponse:
    """Handler para DuplicateEntityError"""
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "entity": exc.entity,
            "field": exc.field,
            "value": exc.value,
        },
    )


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    """Handler para InvalidCredentialsError"""
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(InsufficientPermissionsError)
async def insufficient_permissions_handler(
    request: Request, exc: InsufficientPermissionsError
) -> JSONResponse:
    """Handler para InsufficientPermissionsError"""
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "required_role": exc.required_role},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handler para ValidationError"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(BandangWebError)
async def bandangweb_exception_handler(
    request: Request, exc: BandangWebError
) -> JSONResponse:
    """Handler genérico para excepciones de la aplicación"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint raíz"""
    return {
        "message": "BandangWeb API",
        "version": settings.VERSION,
        "docs": "/api/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

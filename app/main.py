"""
Aplicación principal FastAPI
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import (
    BandangWebException,
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
async def lifespan(app: FastAPI):
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middlewares custom
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Configurar rate limiting
limiter = get_rate_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Exception handlers personalizados
@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request, exc: EntityNotFoundError):
    """Handler para EntityNotFoundError"""
    return JSONResponse(
        status_code=404, content={"detail": str(exc), "entity": exc.entity}
    )


@app.exception_handler(DuplicateEntityError)
async def duplicate_entity_handler(request, exc: DuplicateEntityError):
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
async def invalid_credentials_handler(request, exc: InvalidCredentialsError):
    """Handler para InvalidCredentialsError"""
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(InsufficientPermissionsError)
async def insufficient_permissions_handler(request, exc: InsufficientPermissionsError):
    """Handler para InsufficientPermissionsError"""
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "required_role": exc.required_role},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handler para ValidationError"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(BandangWebException)
async def bandangweb_exception_handler(request, exc: BandangWebException):
    """Handler genérico para excepciones de la aplicación"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Root endpoint
@app.get("/")
async def root():
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

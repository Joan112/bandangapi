"""
Endpoints de health check
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema de respuesta de health check"""

    status: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint

    Returns:
        Estado de la aplicación
    """
    from app.core.config import settings

    return HealthResponse(
        status="healthy", version=settings.VERSION, environment=settings.ENVIRONMENT
    )


@router.get("/ping", status_code=status.HTTP_200_OK)
async def ping() -> dict[str, str]:
    """
    Simple ping endpoint

    Returns:
        Pong
    """
    return {"message": "pong"}

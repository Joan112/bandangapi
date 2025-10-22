"""
Router principal de API v1
"""

from fastapi import APIRouter

from app.presentation.api.v1.endpoints import (
    events,
    health,
    multimedia,
    supabase_auth,
    users,
)

api_router = APIRouter()

# Health check - Estado del sistema
api_router.include_router(health.router, prefix="/health", tags=["Salud"])

# Autenticación - Registro, login, logout, refresh token
api_router.include_router(supabase_auth.router, prefix="/auth", tags=["Autenticación"])

# Usuarios - Gestión de usuarios y perfiles
api_router.include_router(users.router, prefix="/users", tags=["Usuarios"])

# Eventos - Gestión de eventos y cotizaciones
api_router.include_router(events.router, prefix="/events", tags=["Eventos"])

# Multimedia - Gestión de imágenes y videos
api_router.include_router(multimedia.router, prefix="/multimedia", tags=["Multimedia"])

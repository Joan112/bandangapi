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

# Health check
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Supabase Auth
api_router.include_router(supabase_auth.router, prefix="/auth", tags=["Authentication"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Events
api_router.include_router(events.router, prefix="/events", tags=["Eventos"])

# Multimedia
api_router.include_router(multimedia.router, prefix="/multimedia", tags=["Multimedia"])

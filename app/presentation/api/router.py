"""
Router principal de API v1
"""
from fastapi import APIRouter

from app.presentation.api.v1.endpoints import health, supabase_auth, events, multimedia

api_router = APIRouter()

# Health check
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Supabase Auth
api_router.include_router(supabase_auth.router, prefix="/auth", tags=["Authentication"])

# Events
api_router.include_router(events.router, prefix="/events", tags=["Eventos"])

# Multimedia
api_router.include_router(multimedia.router, prefix="/multimedia", tags=["Multimedia"])

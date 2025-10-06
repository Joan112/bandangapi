"""
Router principal de API v1
"""
from fastapi import APIRouter

from app.presentation.api.v1.endpoints import (
    health,
    supabase_auth,
)

api_router = APIRouter()

# Incluir routers de cada módulo
api_router.include_router(health.router)
api_router.include_router(supabase_auth.router)

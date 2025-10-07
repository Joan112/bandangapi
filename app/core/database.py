"""
Configuración de base de datos con Supabase
"""
from supabase import Client, create_client

from app.core.config import settings


def get_supabase_client() -> Client:
    """
    Obtener cliente de Supabase

    Returns:
        Client: Cliente de Supabase configurado
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_admin_client() -> Client:
    """
    Obtener cliente de Supabase con service role (admin)

    Returns:
        Client: Cliente de Supabase con privilegios de admin
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

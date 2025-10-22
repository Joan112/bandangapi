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

    **SECURITY WARNING**: Este cliente BYPASSA todas las Row Level Security (RLS) policies.
    Úsalo SOLO cuando sea absolutamente necesario (ej: acceso a auth.users, triggers fallidos).
    SIEMPRE pregúntate: ¿puedo hacer esto con el cliente regular y RLS policies?

    Usos legítimos:
    - Acceder a la tabla auth.users de Supabase (no accesible vía RLS)
    - Crear perfiles manualmente si el trigger de BD falla (fallback crítico)
    - Operaciones administrativas que requieren bypass de RLS

    Returns:
        Client: Cliente de Supabase con privilegios de admin
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

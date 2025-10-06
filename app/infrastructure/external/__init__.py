"""
Servicios externos (email, SMS, Supabase, etc)
"""
from app.infrastructure.external.supabase import supabase_client

__all__ = ["supabase_client"]

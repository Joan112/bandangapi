"""fix_eventos_rls_allow_public_insert

CRITICAL FIX: Permite INSERT público en tabla eventos para solicitudes de cotización.

El endpoint POST /api/v1/events/ es público (no requiere autenticación) para que
clientes puedan solicitar cotizaciones sin registrarse. Esta migración corrige
las políticas RLS para permitir INSERT con rol anon (público) en Supabase.

PROBLEMA:
- La política actual solo permite INSERT a usuarios autenticados
- El endpoint usa supabase_client.client (no admin_client), respeta RLS
- Esto causa error: "new row violates row-level security policy"

SOLUCIÓN:
- Eliminar política restrictiva "Allow authenticated users to insert events"
- Crear nueva política "Anyone can insert events" que permite anon + authenticated
- Mantener SELECT solo para usuarios autenticados con rol ADMIN

Revision ID: ecf5c4495f39
Revises:
Create Date: 2025-11-07 12:45:52.889953
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecf5c4495f39'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Aplica la corrección de políticas RLS para permitir INSERT público en eventos.
    """
    # 1. Eliminar todas las políticas existentes de INSERT en eventos
    op.execute("""
        DROP POLICY IF EXISTS "Allow authenticated users to insert events" ON public.eventos;
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
    """)

    # 2. Crear política que permite INSERT público (anon + authenticated)
    # Esto permite que el formulario de cotización funcione sin autenticación
    op.execute("""
        CREATE POLICY "Anyone can insert events"
        ON public.eventos
        FOR INSERT
        TO anon, authenticated
        WITH CHECK (true);
    """)

    # 3. Verificar que SELECT solo está disponible para ADMIN (debería existir)
    # Si no existe, crearla
    op.execute("""
        DROP POLICY IF EXISTS "Allow authenticated users to view all events" ON public.eventos;
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
    """)

    op.execute("""
        CREATE POLICY "Admins can view events"
        ON public.eventos
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM public.profiles
                WHERE id = auth.uid()
                AND role IN ('ADMIN', 'SUPERADMIN')
            )
        );
    """)

    # 4. Asegurar que UPDATE y DELETE solo están disponibles para ADMIN
    op.execute("""
        DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
    """)

    op.execute("""
        CREATE POLICY "Admins can update events"
        ON public.eventos
        FOR UPDATE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM public.profiles
                WHERE id = auth.uid()
                AND role IN ('ADMIN', 'SUPERADMIN')
            )
        );
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;
    """)

    op.execute("""
        CREATE POLICY "Admins can delete events"
        ON public.eventos
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM public.profiles
                WHERE id = auth.uid()
                AND role IN ('ADMIN', 'SUPERADMIN')
            )
        );
    """)


def downgrade() -> None:
    """
    Revierte la corrección (vuelve a la política restrictiva).
    NOTA: Este rollback NO se recomienda en producción ya que rompería
    la funcionalidad del formulario público de cotizaciones.
    """
    # Eliminar políticas corregidas
    op.execute("""
        DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
    """)

    op.execute("""
        DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;
    """)

    # Volver a la política restrictiva (solo authenticated puede insertar)
    op.execute("""
        CREATE POLICY "Allow authenticated users to insert events"
        ON public.eventos
        FOR INSERT
        TO authenticated
        WITH CHECK (true);
    """)

    op.execute("""
        CREATE POLICY "Allow authenticated users to view all events"
        ON public.eventos
        FOR SELECT
        TO authenticated
        USING (true);
    """)

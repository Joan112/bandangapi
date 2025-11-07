#!/usr/bin/env python3
"""
Script para corregir las políticas RLS de la tabla eventos en Supabase.

PROBLEMA CRÍTICO:
El endpoint público POST /api/v1/events/ está fallando con error 500 porque
la tabla "eventos" tiene RLS habilitado pero NO permite INSERT público (anon role).

ERROR:
    new row violates row-level security policy for table "eventos"

SOLUCIÓN:
Este script ejecuta el SQL necesario para:
1. Eliminar la política restrictiva que solo permite INSERT a usuarios autenticados
2. Crear nueva política que permite INSERT público (anon + authenticated)
3. Mantener SELECT, UPDATE, DELETE solo para usuarios ADMIN

USO:
    poetry run python scripts/fix_eventos_rls.py
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.infrastructure.external.supabase import supabase_client


async def fix_eventos_rls() -> None:
    """
    Ejecuta las correcciones de políticas RLS en la tabla eventos.
    """
    print("=" * 80)
    print("FIX EVENTOS RLS - Corrección de políticas de seguridad")
    print("=" * 80)
    print()
    print(f"Conectando a Supabase: {settings.SUPABASE_URL}")
    print()

    try:
        # Obtener cliente admin (necesario para modificar políticas RLS)
        admin = await supabase_client.admin_client
        print("✓ Cliente admin de Supabase obtenido correctamente")
        print()

        # SQL para corregir políticas RLS
        sql_statements = [
            # 1. Eliminar políticas antiguas de INSERT
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Allow authenticated users to insert events" ON public.eventos;',
            ),
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;',
            ),
            # 2. Crear política que permite INSERT público
            (
                "CREATE INSERT POLICY",
                """
                CREATE POLICY "Anyone can insert events"
                ON public.eventos
                FOR INSERT
                TO anon, authenticated
                WITH CHECK (true);
                """,
            ),
            # 3. Limpiar políticas SELECT antiguas
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Allow authenticated users to view all events" ON public.eventos;',
            ),
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;',
            ),
            # 4. Crear política SELECT solo para ADMIN
            (
                "CREATE SELECT POLICY",
                """
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
                """,
            ),
            # 5. Asegurar UPDATE solo para ADMIN
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;',
            ),
            (
                "CREATE UPDATE POLICY",
                """
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
                """,
            ),
            # 6. Asegurar DELETE solo para ADMIN
            (
                "DROP POLICY IF EXISTS",
                'DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;',
            ),
            (
                "CREATE DELETE POLICY",
                """
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
                """,
            ),
        ]

        # Ejecutar cada statement SQL
        print("Ejecutando correcciones SQL...")
        print("-" * 80)
        for description, sql in sql_statements:
            print(f"\n[{description}]")
            try:
                result = await admin.rpc("exec_sql", {"query": sql}).execute()
                print(f"  ✓ Ejecutado exitosamente")
            except Exception as e:
                # Algunos statements pueden fallar si la política no existe (DROP IF EXISTS)
                # Esto es esperado y no es un error crítico
                error_msg = str(e)
                if "does not exist" in error_msg or "no existe" in error_msg.lower():
                    print(f"  → Política no existía (ok)")
                elif "exec_sql" in error_msg:
                    # El RPC exec_sql no existe, ejecutar SQL directamente
                    print(f"  ⚠ RPC exec_sql no disponible, ejecutando directamente...")
                    # Nota: postgrest no permite ejecutar DDL directamente
                    print(f"  ⚠ MANUAL: Ejecuta este SQL en Supabase SQL Editor:")
                    print()
                    print(sql)
                    print()
                else:
                    print(f"  ✗ Error: {e}")

        print()
        print("=" * 80)
        print("IMPORTANTE: Si viste advertencias sobre 'exec_sql':")
        print("=" * 80)
        print()
        print("Supabase PostgREST NO permite ejecutar DDL (CREATE/DROP POLICY) via API.")
        print("Debes ejecutar el SQL manualmente en el SQL Editor de Supabase:")
        print()
        print(f"1. Ve a: https://app.supabase.com/project/{settings.SUPABASE_URL.split('//')[1].split('.')[0]}/sql/new")
        print("2. Copia y pega todo el SQL de abajo:")
        print()
        print("-" * 80)
        print(
            """
-- ============================================================================
-- CORRECCIÓN RLS PARA TABLA EVENTOS - BandangWeb API
-- ============================================================================

-- 1. Limpiar políticas existentes
DROP POLICY IF EXISTS "Allow authenticated users to insert events" ON public.eventos;
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
DROP POLICY IF EXISTS "Allow authenticated users to view all events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;

-- 2. Crear política INSERT pública (permite anon + authenticated)
CREATE POLICY "Anyone can insert events"
ON public.eventos
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- 3. Crear política SELECT solo para ADMIN
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

-- 4. Crear política UPDATE solo para ADMIN
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

-- 5. Crear política DELETE solo para ADMIN
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

-- 6. Verificar que RLS está habilitado
ALTER TABLE public.eventos ENABLE ROW LEVEL SECURITY;

-- 7. Verificar políticas creadas
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'eventos'
ORDER BY policyname;
"""
        )
        print("-" * 80)
        print()
        print("3. Ejecuta el SQL (botón 'Run' o Ctrl+Enter)")
        print("4. Verifica que no hay errores")
        print("5. Prueba el endpoint: POST /api/v1/events/")
        print()

    except Exception as e:
        print(f"\n✗ ERROR CRÍTICO: {e}")
        print()
        print("Debes ejecutar el SQL manualmente en Supabase SQL Editor.")
        print("Ver instrucciones arriba.")
        sys.exit(1)


if __name__ == "__main__":
    print()
    asyncio.run(fix_eventos_rls())
    print()
    print("✓ Script completado")
    print()

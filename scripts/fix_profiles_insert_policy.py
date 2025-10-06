"""
Script para agregar la política de INSERT faltante en la tabla profiles
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.infrastructure.external.supabase import supabase_client


async def fix_insert_policy():
    """Agregar política de INSERT a la tabla profiles"""
    try:
        client = await supabase_client.client

        # SQL para agregar la política de INSERT
        sql_fix = """
        -- Primero eliminar la política si ya existe
        DROP POLICY IF EXISTS "Permitir inserción de perfiles durante registro" ON public.profiles;

        -- Crear nueva política que permita INSERT
        CREATE POLICY "Permitir inserción de perfiles durante registro"
        ON public.profiles
        FOR INSERT
        WITH CHECK (true);
        """

        print("Ejecutando fix para política de INSERT en profiles...")

        # Ejecutar el SQL
        result = await client.rpc('exec_sql', {'sql': sql_fix}).execute()

        print("✅ Política de INSERT agregada exitosamente")
        print("Ahora la tabla profiles permite INSERT y el registro debería funcionar")

    except Exception as e:
        print(f"❌ Error al ejecutar fix: {e}")
        print("\nNOTA: Este script requiere una función RPC 'exec_sql' en Supabase.")
        print("\nPor favor, ejecuta manualmente este SQL en el SQL Editor de Supabase:\n")
        print("=" * 80)
        print("""
-- Eliminar política si existe
DROP POLICY IF EXISTS "Permitir inserción de perfiles durante registro" ON public.profiles;

-- Crear política que permita INSERT
CREATE POLICY "Permitir inserción de perfiles durante registro"
ON public.profiles
FOR INSERT
WITH CHECK (true);
        """)
        print("=" * 80)
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(fix_insert_policy())
    sys.exit(0 if success else 1)

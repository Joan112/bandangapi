#!/usr/bin/env python
"""
Script mejorado para ejecutar el esquema SQL de Supabase.
Usa psycopg2 para conectarse directamente a PostgreSQL en Supabase.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales de Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas.")
    sys.exit(1)

# Extraer el project ID de la URL de Supabase
# Formato: https://PROJECT_ID.supabase.co
project_id = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")

# Construir la cadena de conexión de PostgreSQL
# Supabase usa el puerto 6543 para conexiones directas a PostgreSQL (Supavisor en modo Session)
# Nota: Necesitarás la contraseña de la base de datos, no el SUPABASE_KEY (anon key)
print("=" * 80)
print("INFORMACIÓN IMPORTANTE")
print("=" * 80)
print()
print("Este script requiere conectarse directamente a PostgreSQL en Supabase.")
print()
print("Para ejecutar el esquema SQL, tienes 3 opciones:")
print()
print("OPCIÓN 1: Usar el SQL Editor en Supabase (RECOMENDADO)")
print("-" * 80)
print(f"1. Ve a: https://supabase.com/dashboard/project/{project_id}/sql/new")
print("2. Copia y pega el contenido de: scripts/supabase_auth_schema.sql")
print("3. Ejecuta el script desde el editor SQL")
print()
print("OPCIÓN 2: Usar psql (línea de comandos)")
print("-" * 80)
print("1. Obtén tus credenciales de conexión en:")
print(f"   https://supabase.com/dashboard/project/{project_id}/settings/database")
print("2. Ejecuta:")
print(f"   psql 'postgresql://postgres:[YOUR-PASSWORD]@db.{project_id}.supabase.co:5432/postgres' \\")
print("       -f scripts/supabase_auth_schema.sql")
print()
print("OPCIÓN 3: Usar la variable de entorno DATABASE_PASSWORD")
print("-" * 80)
print("1. Agrega DATABASE_PASSWORD a tu archivo .env")
print("2. Ejecuta este script nuevamente")
print()
print("=" * 80)

# Intentar conectar si hay una contraseña de base de datos disponible
DB_PASSWORD = os.environ.get("DATABASE_PASSWORD") or os.environ.get("SUPABASE_DB_PASSWORD")

if DB_PASSWORD:
    try:
        import psycopg2

        # Construir cadena de conexión
        # Supabase usa el puerto 6543 para conexiones pooled (Supavisor)
        # o puerto 5432 para conexiones directas (requiere habilitar conexiones directas)
        conn_string = f"postgresql://postgres:{DB_PASSWORD}@db.{project_id}.supabase.co:6543/postgres"

        print("\nIntentando conectar a la base de datos...")
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cur = conn.cursor()

        # Leer el archivo SQL
        sql_path = Path("scripts/supabase_auth_schema.sql")
        if not sql_path.exists():
            print(f"Error: El archivo {sql_path} no existe.")
            sys.exit(1)

        with open(sql_path, "r") as f:
            sql_content = f.read()

        print(f"Ejecutando script SQL: {sql_path}")

        # Ejecutar el script SQL completo
        cur.execute(sql_content)

        print("✓ Script SQL ejecutado correctamente.")
        print("✓ Tablas y funciones creadas en Supabase.")

        cur.close()
        conn.close()

    except ImportError:
        print("\nError: psycopg2 no está instalado.")
        print("Instálalo con: pip install psycopg2-binary")
        print("\nO usa una de las opciones anteriores.")
    except Exception as e:
        print(f"\nError al ejecutar el script SQL: {e}")
        print("\nSi el error persiste, usa el SQL Editor de Supabase (Opción 1).")
        sys.exit(1)
else:
    print("\nNo se encontró DATABASE_PASSWORD en las variables de entorno.")
    print("Usa una de las opciones anteriores para ejecutar el script SQL.")

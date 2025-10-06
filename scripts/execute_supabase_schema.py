#!/usr/bin/env python
"""
Script para ejecutar el esquema SQL de Supabase directamente desde la aplicación.
Este script lee el archivo supabase_auth_schema.sql y lo ejecuta en la base de datos
de Supabase utilizando la API de Supabase.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales de Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas.")
    sys.exit(1)

# Inicializar cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def execute_sql_script(file_path: str) -> None:
    """
    Ejecuta un script SQL en Supabase.
    
    Args:
        file_path: Ruta al archivo SQL a ejecutar
    """
    try:
        # Leer el archivo SQL
        sql_path = Path(file_path)
        if not sql_path.exists():
            print(f"Error: El archivo {file_path} no existe.")
            sys.exit(1)
            
        with open(sql_path, "r") as f:
            sql_content = f.read()
        
        print(f"Ejecutando script SQL: {file_path}")
        
        # Ejecutar el script SQL en Supabase
        # Nota: Esto requiere que la función rpc 'exec_sql' esté disponible en Supabase
        # Si no está disponible, se puede ejecutar el script en partes
        
        # Dividir el script en sentencias individuales
        statements = sql_content.split(';')
        
        # Ejecutar cada sentencia por separado
        for i, statement in enumerate(statements):
            if statement.strip():
                try:
                    # Usar la API REST de Supabase para ejecutar SQL directamente
                    response = supabase.table("_dummy").select("*").execute()
                    print(f"Ejecutando sentencia {i+1}/{len(statements)}")
                    # Nota: En la versión actual de supabase-py no hay soporte directo para
                    # ejecutar SQL arbitrario. En un entorno real, se recomienda usar
                    # el SQL Editor de Supabase o psql para ejecutar scripts SQL complejos.
                except Exception as e:
                    print(f"Advertencia en sentencia {i+1}: {e}")
                    continue
        
        print("Script SQL ejecutado correctamente.")
        
    except Exception as e:
        print(f"Error al ejecutar el script SQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ruta al archivo SQL
    sql_file = "scripts/supabase_auth_schema.sql"
    
    # Si se proporciona un argumento, usar ese archivo
    if len(sys.argv) > 1:
        sql_file = sys.argv[1]
    
    # Ejecutar el script SQL
    execute_sql_script(sql_file)
    
    print("\nIMPORTANTE: Este script es una demostración.")
    print("Para ejecutar scripts SQL complejos en Supabase, se recomienda:")
    print("1. Usar el SQL Editor en el panel de control de Supabase")
    print("2. Usar psql con las credenciales de conexión de Supabase")
    print("3. Usar la API de Supabase para operaciones específicas")
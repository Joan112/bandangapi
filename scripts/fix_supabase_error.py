"""
Script para corregir el error de importación de AuthorizationError en Supabase.
Este script modifica temporalmente el archivo __init__.py de realtime para evitar el error.
"""
import os
import sys
import importlib.util
import site

def find_realtime_init():
    """Encuentra la ubicación del archivo __init__.py del paquete realtime."""
    for path in site.getsitepackages():
        realtime_init = os.path.join(path, 'realtime', '__init__.py')
        if os.path.exists(realtime_init):
            return realtime_init
    return None

def fix_realtime_init(file_path):
    """Corrige el archivo __init__.py del paquete realtime."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Verificar si necesita corrección
    if 'from realtime import AuthorizationError' in content:
        print(f"El archivo {file_path} ya contiene la corrección.")
        return
    
    # Agregar la clase AuthorizationError
    new_content = content + """
# Clase agregada manualmente para corregir el error de importación
class AuthorizationError(Exception):
    \"\"\"Error raised when authorization fails.\"\"\"
    pass

class NotConnectedError(Exception):
    \"\"\"Error raised when not connected to the server.\"\"\"
    pass
"""
    
    # Escribir el contenido modificado
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Se ha corregido el archivo {file_path}")

def main():
    """Función principal."""
    realtime_init = find_realtime_init()
    if realtime_init:
        fix_realtime_init(realtime_init)
        print("Corrección aplicada con éxito.")
    else:
        print("No se pudo encontrar el paquete realtime.")
        sys.exit(1)

if __name__ == "__main__":
    main()
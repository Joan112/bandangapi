"""
Script para inicializar la base de datos
"""
import asyncio

from app.core.database import Base, engine


async def init_db():
    """
    Inicializar base de datos creando todas las tablas
    """
    print("Creando tablas de base de datos...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Tablas creadas exitosamente!")


if __name__ == "__main__":
    asyncio.run(init_db())

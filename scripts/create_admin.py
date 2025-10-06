"""
Script para crear usuario administrador
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.domain.entities.user import UserRole
from app.domain.use_cases.create_user import CreateUserUseCase
from app.infrastructure.database.repositories.user_repository_impl import (
    UserRepositoryImpl,
)


async def create_admin():
    """
    Crear usuario superadministrador
    """
    async with AsyncSessionLocal() as db:
        repo = UserRepositoryImpl(db)
        use_case = CreateUserUseCase(repo)

        # Verificar si ya existe un superadmin
        existing = await repo.get_by_email("admin@bandangweb.com")
        if existing:
            print("El usuario admin@bandangweb.com ya existe!")
            return

        # Crear superadmin
        admin = await use_case.execute(
            email="admin@bandangweb.com",
            password="AdminPassword123",
            full_name="Super Administrador",
            role=UserRole.SUPERADMIN,
        )

        print(f"Superadmin creado exitosamente!")
        print(f"Email: {admin.email}")
        print(f"Password: AdminPassword123")
        print("\nIMPORTANTE: Cambia el password inmediatamente!")


if __name__ == "__main__":
    asyncio.run(create_admin())

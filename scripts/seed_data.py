"""
Script para poblar base de datos con datos de ejemplo
"""
import asyncio

from faker import Faker

from app.core.database import AsyncSessionLocal
from app.domain.entities.user import UserRole
from app.domain.use_cases.create_user import CreateUserUseCase
from app.infrastructure.database.repositories.user_repository_impl import (
    UserRepositoryImpl,
)

fake = Faker("es_ES")


async def seed_users(count: int = 10):
    """
    Crear usuarios de ejemplo

    Args:
        count: Cantidad de usuarios a crear
    """
    async with AsyncSessionLocal() as db:
        repo = UserRepositoryImpl(db)
        use_case = CreateUserUseCase(repo)

        print(f"Creando {count} usuarios de ejemplo...")

        for i in range(count):
            try:
                email = fake.email()
                full_name = fake.name()

                # 70% usuarios regulares, 20% admins, 10% superadmins
                if i % 10 == 0:
                    role = UserRole.SUPERADMIN
                elif i % 5 == 0:
                    role = UserRole.ADMIN
                else:
                    role = UserRole.USER

                user = await use_case.execute(
                    email=email,
                    password="TestPassword123",
                    full_name=full_name,
                    role=role,
                )

                print(
                    f"  [{i+1}/{count}] Creado: {user.email} ({user.role.value})"
                )

            except Exception as e:
                print(f"  [{i+1}/{count}] Error: {e}")

        print(f"\n{count} usuarios creados exitosamente!")
        print("Password para todos: TestPassword123")


if __name__ == "__main__":
    import sys

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(seed_users(count))

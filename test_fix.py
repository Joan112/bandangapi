import asyncio
from app.infrastructure.database.repositories.supabase_user_repository_impl import SupabaseUserRepositoryImpl

async def test_user_creation():
    repo = SupabaseUserRepositoryImpl()
    try:
        # Intentar crear un usuario con el email problemático
        await repo.create_user('elyon87@hotmail.com', 'Password123!')
        print('Usuario creado exitosamente')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_user_creation())
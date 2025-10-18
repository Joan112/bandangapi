"""
Caso de uso para autenticar un usuario con Supabase
"""

from typing import Protocol

from app.core.exceptions import InvalidCredentialsError
from app.domain.entities.supabase_user import SupabaseUser


class SupabaseUserRepository(Protocol):
    """Interfaz del repositorio de usuarios con Supabase"""

    async def authenticate(
        self, email: str, password: str
    ) -> tuple[SupabaseUser, str, str] | None:
        """
        Autentica a un usuario y devuelve el usuario y los tokens.
        """
        ...


class LoginUserSupabaseUseCase:
    """
    Caso de uso para autenticar un usuario con Supabase
    """

    def __init__(self, user_repository: SupabaseUserRepository) -> None:
        """
        Inicializar caso de uso

        Args:
            user_repository: Repositorio de usuarios
        """
        self._repository = user_repository

    async def execute(self, email: str, password: str) -> tuple[SupabaseUser, str, str]:
        """
        Ejecutar caso de uso

        Args:
            email: Email del usuario
            password: Contraseña del usuario

        Returns:
            Tupla con el usuario autenticado, token de acceso y token de refresco

        Raises:
            InvalidCredentialsError: Si las credenciales son inválidas
        """
        # Autenticar usuario a través del repositorio
        auth_result = await self._repository.authenticate(email, password)

        if not auth_result:
            raise InvalidCredentialsError(
                "Credenciales inválidas o usuario no encontrado/confirmado."
            )

        user, access_token, refresh_token = auth_result

        if not user.is_active:
            raise InvalidCredentialsError("Usuario inactivo.")

        return user, access_token, refresh_token

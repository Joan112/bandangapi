"""
FastAPI dependencies globales
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.domain.entities.supabase_user import SupabaseUser, UserRole
from app.domain.use_cases.events.create_event import CreateEventUseCase
from app.domain.use_cases.multimedia.create_multimedia import CreateMultimediaUseCase
from app.infrastructure.database.repositories.event_repository_impl import (
    EventRepositoryImpl,
)
from app.infrastructure.database.repositories.multimedia_repository_impl import (
    MultimediaRepositoryImpl,
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """
    Obtener ID del usuario actual desde el token de Supabase

    Args:
        token: Token JWT de Supabase

    Returns:
        ID del usuario (UUID as string)

    Raises:
        HTTPException: Si el token es inválido o el email no está confirmado
    """
    from app.infrastructure.external.supabase import supabase_client

    try:
        # Validar token con Supabase Auth directamente
        client = await supabase_client.client
        user_response = await client.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar que el email esté confirmado
        user = user_response.user
        if not user.email_confirmed_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email no confirmado. Por favor, verifica tu correo electrónico.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user.id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al validar token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SupabaseUser:
    """
    Obtener usuario actual completo desde Supabase

    Args:
        user_id: ID del usuario (UUID as string)

    Returns:
        Usuario completo (SupabaseUser)

    Raises:
        HTTPException: Si el usuario no existe o está inactivo
    """
    from uuid import UUID

    from app.infrastructure.database.repositories.supabase_user_repository_impl import (
        SupabaseUserRepositoryImpl,
    )

    repo = SupabaseUserRepositoryImpl()
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo"
        )

    return user


def require_role(
    required_role: str,
) -> Callable[[SupabaseUser], Awaitable[SupabaseUser]]:
    """
    Factory para crear dependency que requiere un rol específico

    Args:
        required_role: Rol requerido ("USER", "ADMIN", "SUPERADMIN")

    Returns:
        Dependency function
    """

    async def role_dependency(
        current_user: Annotated[SupabaseUser, Depends(get_current_user)]
    ) -> SupabaseUser:
        """Verificar que el usuario tiene el rol requerido"""

        # Orden jerárquico de roles
        role_hierarchy = {
            "USER": 1,
            "ADMIN": 2,
            "SUPERADMIN": 3,
        }

        # Convertir enum a string para comparación (usar .name para obtener "USER", "ADMIN", etc.)
        user_role_str = current_user.role.name if hasattr(current_user.role, 'name') else str(current_user.role).upper()
        user_role_level = role_hierarchy.get(user_role_str, 0)
        required_role_level = role_hierarchy.get(required_role, 999)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere rol {required_role} o superior",
            )

        return current_user

    return role_dependency


async def require_admin(
    current_user: Annotated[SupabaseUser, Depends(get_current_user)]
) -> SupabaseUser:
    """
    Requiere que el usuario sea administrador

    Args:
        current_user: Usuario actual

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el usuario no es admin
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol de administrador",
        )
    return current_user


async def require_superadmin(
    current_user: Annotated[SupabaseUser, Depends(get_current_user)]
) -> SupabaseUser:
    """
    Requiere que el usuario sea superadmin

    Args:
        current_user: Usuario actual

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el usuario no es superadmin
    """
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol de superadministrador",
        )
    return current_user


# --- Casos de Uso ---


def get_create_event_use_case() -> CreateEventUseCase:
    """
    Crea y devuelve una instancia del caso de uso para crear eventos.

    Esta función actúa como un constructor para la inyección de dependencias de FastAPI.
    Se encarga de instanciar el repositorio y luego el caso de uso.

    Returns:
        Una instancia de CreateEventUseCase.
    """
    event_repository = EventRepositoryImpl()
    return CreateEventUseCase(event_repository=event_repository)


def get_create_multimedia_use_case() -> CreateMultimediaUseCase:
    """
    Crea y devuelve una instancia del caso de uso para crear contenido multimedia.

    Esta función actúa como un constructor para la inyección de dependencias de FastAPI.
    Se encarga de instanciar el repositorio y luego el caso de uso.

    Returns:
        Una instancia de CreateMultimediaUseCase.
    """
    multimedia_repository = MultimediaRepositoryImpl()
    return CreateMultimediaUseCase(multimedia_repository=multimedia_repository)

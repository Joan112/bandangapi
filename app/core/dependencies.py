"""
FastAPI dependencies globales
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token
from app.domain.entities.supabase_user import UserRole
from app.domain.use_cases.events.create_event import CreateEventUseCase
from app.domain.use_cases.multimedia.create_multimedia import CreateMultimediaUseCase
from app.infrastructure.database.repositories.event_repository_impl import (
    EventRepositoryImpl,
)
from app.infrastructure.database.repositories.multimedia_repository_impl import (
    MultimediaRepositoryImpl,
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")


async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    """
    Obtener ID del usuario actual desde el token JWT

    Args:
        token: Token JWT

    Returns:
        ID del usuario

    Raises:
        HTTPException: Si el token es inválido
    """
    payload = decode_token(token, expected_type="access")
    user_id: str | None = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return int(user_id)


async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
) -> dict:
    """
    Obtener usuario actual completo desde Supabase

    Args:
        user_id: ID del usuario

    Returns:
        Usuario completo

    Raises:
        HTTPException: Si el usuario no existe o está inactivo
    """
    from uuid import UUID
    from app.infrastructure.database.repositories.supabase_user_repository_impl import (
        SupabaseUserRepositoryImpl,
    )

    repo = SupabaseUserRepositoryImpl()
    user = await repo.get_by_id(UUID(int=user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo"
        )

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Requiere que el usuario sea administrador

    Args:
        current_user: Usuario actual

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el usuario no es admin
    """
    if current_user["role"] not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol de administrador",
        )
    return current_user


async def require_superadmin(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Requiere que el usuario sea superadmin

    Args:
        current_user: Usuario actual

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el usuario no es superadmin
    """
    if current_user["role"] != UserRole.SUPERADMIN:
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

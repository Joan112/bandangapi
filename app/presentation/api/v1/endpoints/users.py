"""
Endpoints para gestión de usuarios
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_role
from app.domain.entities.supabase_user import SupabaseUser
from app.infrastructure.database.repositories.supabase_user_repository_impl import (
    SupabaseUserRepositoryImpl,
)
from app.presentation.api.v1.schemas.supabase_auth import UserResponse, UserUpdate

router = APIRouter()


def get_supabase_user_repository() -> SupabaseUserRepositoryImpl:
    """
    Obtener repositorio de usuarios con Supabase

    Returns:
        Repositorio de usuarios
    """
    return SupabaseUserRepositoryImpl()


@router.get("/me", response_model=UserResponse)
async def get_current_user_endpoint(
    current_user: SupabaseUser = Depends(get_current_user),
) -> UserResponse:
    """
    Obtener información del usuario actual

    Requiere autenticación válida.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.get("", response_model=dict[str, Any])
async def list_users(
    current_user: SupabaseUser = Depends(require_role("ADMIN")),
    repository: SupabaseUserRepositoryImpl = Depends(get_supabase_user_repository),
) -> dict[str, Any]:
    """
    Listar todos los usuarios

    Requiere rol ADMIN o superior.
    """
    users = await repository.list_all()
    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
            }
            for user in users
        ],
        "total": len(users),
    }


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    current_user: SupabaseUser = Depends(require_role("ADMIN")),
    repository: SupabaseUserRepositoryImpl = Depends(get_supabase_user_repository),
) -> UserResponse:
    """
    Actualizar información de un usuario

    Requiere rol ADMIN o superior.
    Todos los campos son opcionales (PATCH semántico).
    """
    # Obtener usuario actual
    user = await repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {user_id} no encontrado",
        )

    # Convertir schema a dict excluyendo valores None
    update_dict = update_data.model_dump(by_alias=False, exclude_none=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron datos para actualizar",
        )

    # Actualizar usuario
    updated_user = await repository.update(user_id, update_dict)

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        role=updated_user.role,
        is_active=updated_user.is_active,
    )

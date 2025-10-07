"""
Endpoints de la API para gestionar contenido multimedia.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_create_multimedia_use_case
from app.core.exceptions import EntityNotFoundError, SupabaseError
from app.domain.use_cases.multimedia.create_multimedia import CreateMultimediaUseCase
from app.presentation.api.v1.schemas.multimedia import (
    MultimediaCreate,
    MultimediaListResponse,
    MultimediaRead,
    MultimediaUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=MultimediaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo contenido multimedia",
    description="Registra un nuevo contenido multimedia (imagen o video) en el sistema.",
    tags=["Multimedia"]
)
async def create_multimedia(
    multimedia_data: MultimediaCreate,
    use_case: CreateMultimediaUseCase = Depends(get_create_multimedia_use_case)
):
    """
    Endpoint para crear nuevo contenido multimedia.

    - **multimedia_data**: Datos del contenido validados por el esquema `MultimediaCreate`.
    - **use_case**: Instancia del caso de uso inyectada por FastAPI.
    """
    try:
        # Convertir el esquema Pydantic a dict sin alias (nombres de columnas reales)
        multimedia_dict = multimedia_data.model_dump(by_alias=False, mode='json', exclude_none=True)

        created_multimedia = await use_case.execute(multimedia_dict)
        return created_multimedia
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo crear el contenido multimedia: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )


@router.get(
    "/",
    response_model=MultimediaListResponse,
    summary="Listar contenido multimedia",
    description="Obtiene una lista de contenidos multimedia con filtros opcionales.",
    tags=["Multimedia"]
)
async def list_multimedia(
    skip: int = Query(0, ge=0, description="Número de elementos a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de elementos a devolver"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (image/video)"),
    is_published: Optional[bool] = Query(None, alias="isPublished", description="Filtrar por estado de publicación"),
    featured: Optional[bool] = Query(None, description="Filtrar por destacados"),
):
    """
    Endpoint para listar contenido multimedia con filtros opcionales.
    """
    try:
        from app.infrastructure.database.repositories.multimedia_repository_impl import (
            MultimediaRepositoryImpl,
        )

        repository = MultimediaRepositoryImpl()
        items = await repository.list_all(
            skip=skip,
            limit=limit,
            category=category,
            type=type,
            is_published=is_published,
            featured=featured
        )

        return MultimediaListResponse(
            items=items,
            total=len(items),
            skip=skip,
            limit=limit
        )
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener contenido multimedia: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )


@router.get(
    "/{multimedia_id}",
    response_model=MultimediaRead,
    summary="Obtener contenido multimedia por ID",
    description="Obtiene un contenido multimedia específico por su ID.",
    tags=["Multimedia"]
)
async def get_multimedia(multimedia_id: UUID):
    """
    Endpoint para obtener un contenido multimedia por su ID.
    """
    try:
        from app.infrastructure.database.repositories.multimedia_repository_impl import (
            MultimediaRepositoryImpl,
        )

        repository = MultimediaRepositoryImpl()
        multimedia = await repository.get_by_id(multimedia_id)

        if not multimedia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contenido multimedia con ID {multimedia_id} no encontrado"
            )

        return multimedia
    except HTTPException:
        raise
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener contenido multimedia: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )


@router.patch(
    "/{multimedia_id}",
    response_model=MultimediaRead,
    summary="Actualizar contenido multimedia",
    description="Actualiza un contenido multimedia existente.",
    tags=["Multimedia"]
)
async def update_multimedia(
    multimedia_id: UUID,
    multimedia_data: MultimediaUpdate
):
    """
    Endpoint para actualizar un contenido multimedia.
    """
    try:
        from app.infrastructure.database.repositories.multimedia_repository_impl import (
            MultimediaRepositoryImpl,
        )

        repository = MultimediaRepositoryImpl()

        # Convertir a dict excluyendo valores None
        update_dict = multimedia_data.model_dump(by_alias=False, mode='json', exclude_none=True)

        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar"
            )

        updated_multimedia = await repository.update(multimedia_id, update_dict)
        return updated_multimedia

    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar contenido multimedia: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )


@router.delete(
    "/{multimedia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar contenido multimedia",
    description="Elimina un contenido multimedia del sistema.",
    tags=["Multimedia"]
)
async def delete_multimedia(multimedia_id: UUID):
    """
    Endpoint para eliminar un contenido multimedia.
    """
    try:
        from app.infrastructure.database.repositories.multimedia_repository_impl import (
            MultimediaRepositoryImpl,
        )

        repository = MultimediaRepositoryImpl()
        await repository.delete(multimedia_id)

    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar contenido multimedia: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )

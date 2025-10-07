"""
Implementación del repositorio de multimedia con Supabase.
"""
from typing import Optional
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.exceptions import EntityNotFoundError, SupabaseError
from app.domain.entities.multimedia import Multimedia
from app.domain.repositories.multimedia_repository import MultimediaRepository
from app.infrastructure.external.supabase import supabase_client


class MultimediaRepositoryImpl(MultimediaRepository):
    """
    Implementación concreta del repositorio de multimedia que interactúa con Supabase.
    """

    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self._supabase_client = supabase_client
        self._table_name = "multimedia"

    async def create(self, multimedia_data: dict) -> Multimedia:
        """
        Crea un nuevo contenido multimedia en Supabase.

        Args:
            multimedia_data: Datos del contenido multimedia a crear.

        Returns:
            El contenido multimedia recién creado.

        Raises:
            SupabaseError: Si ocurre un error durante la comunicación con Supabase.
        """
        try:
            # Usar cliente admin para bypassar RLS
            client = await self._supabase_client.admin_client

            response = await client.table(self._table_name).insert(multimedia_data).execute()

            if not response.data or len(response.data) == 0:
                raise SupabaseError("La inserción del contenido multimedia no devolvió datos.")

            created_data = response.data[0]
            return Multimedia.model_validate(created_data)

        except APIError as e:
            raise SupabaseError(f"Error de API al crear contenido multimedia: {e.message}")
        except Exception as e:
            raise SupabaseError(f"Error inesperado al crear contenido multimedia: {e}")

    async def get_by_id(self, multimedia_id: UUID) -> Optional[Multimedia]:
        """
        Obtiene un contenido multimedia por su ID.

        Args:
            multimedia_id: ID del contenido multimedia.

        Returns:
            El contenido multimedia encontrado o None.
        """
        try:
            client = await self._supabase_client.client

            response = await client.table(self._table_name).select("*").eq("id", str(multimedia_id)).execute()

            if not response.data or len(response.data) == 0:
                return None

            return Multimedia.model_validate(response.data[0])

        except Exception as e:
            raise SupabaseError(f"Error al obtener contenido multimedia: {e}")

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        type: Optional[str] = None,
        is_published: Optional[bool] = None,
        featured: Optional[bool] = None,
    ) -> list[Multimedia]:
        """
        Lista contenidos multimedia con filtros opcionales.

        Args:
            skip: Número de registros a saltar.
            limit: Número máximo de registros a devolver.
            category: Filtrar por categoría.
            type: Filtrar por tipo (image/video).
            is_published: Filtrar por estado de publicación.
            featured: Filtrar por destacados.

        Returns:
            Lista de contenidos multimedia.
        """
        try:
            client = await self._supabase_client.client

            query = client.table(self._table_name).select("*")

            # Aplicar filtros opcionales
            if category:
                query = query.eq("category", category)
            if type:
                query = query.eq("type", type)
            if is_published is not None:
                query = query.eq("is_published", is_published)
            if featured is not None:
                query = query.eq("featured", featured)

            # Ordenar por order y fecha de subida
            query = query.order("order", desc=False).order("uploaded_at", desc=True)

            # Aplicar paginación
            query = query.range(skip, skip + limit - 1)

            response = await query.execute()

            if not response.data:
                return []

            return [Multimedia.model_validate(item) for item in response.data]

        except Exception as e:
            raise SupabaseError(f"Error al listar contenidos multimedia: {e}")

    async def update(self, multimedia_id: UUID, multimedia_data: dict) -> Multimedia:
        """
        Actualiza un contenido multimedia existente.

        Args:
            multimedia_id: ID del contenido multimedia.
            multimedia_data: Datos a actualizar.

        Returns:
            El contenido multimedia actualizado.

        Raises:
            EntityNotFoundError: Si el contenido no existe.
            SupabaseError: Si ocurre un error durante la actualización.
        """
        try:
            # Verificar que existe
            existing = await self.get_by_id(multimedia_id)
            if not existing:
                raise EntityNotFoundError("Multimedia", str(multimedia_id))

            client = await self._supabase_client.admin_client

            response = await client.table(self._table_name).update(multimedia_data).eq("id", str(multimedia_id)).execute()

            if not response.data or len(response.data) == 0:
                raise SupabaseError("La actualización del contenido multimedia no devolvió datos.")

            return Multimedia.model_validate(response.data[0])

        except EntityNotFoundError:
            raise
        except APIError as e:
            raise SupabaseError(f"Error de API al actualizar contenido multimedia: {e.message}")
        except Exception as e:
            raise SupabaseError(f"Error inesperado al actualizar contenido multimedia: {e}")

    async def delete(self, multimedia_id: UUID) -> bool:
        """
        Elimina un contenido multimedia.

        Args:
            multimedia_id: ID del contenido multimedia a eliminar.

        Returns:
            True si se eliminó correctamente.

        Raises:
            EntityNotFoundError: Si el contenido no existe.
            SupabaseError: Si ocurre un error durante la eliminación.
        """
        try:
            # Verificar que existe
            existing = await self.get_by_id(multimedia_id)
            if not existing:
                raise EntityNotFoundError("Multimedia", str(multimedia_id))

            client = await self._supabase_client.admin_client

            await client.table(self._table_name).delete().eq("id", str(multimedia_id)).execute()

            return True

        except EntityNotFoundError:
            raise
        except APIError as e:
            raise SupabaseError(f"Error de API al eliminar contenido multimedia: {e.message}")
        except Exception as e:
            raise SupabaseError(f"Error inesperado al eliminar contenido multimedia: {e}")

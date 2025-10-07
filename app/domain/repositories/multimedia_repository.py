"""
Interfaz del repositorio de multimedia (puerto en arquitectura hexagonal).
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.multimedia import Multimedia


class MultimediaRepository(ABC):
    """
    Interfaz abstracta para el repositorio de multimedia.
    Define los métodos que debe implementar cualquier repositorio concreto.
    """

    @abstractmethod
    async def create(self, multimedia_data: dict) -> Multimedia:
        """
        Crea un nuevo contenido multimedia en el repositorio.

        Args:
            multimedia_data: Datos del contenido multimedia a crear.

        Returns:
            El contenido multimedia recién creado.
        """
        pass

    @abstractmethod
    async def get_by_id(self, multimedia_id: UUID) -> Optional[Multimedia]:
        """
        Obtiene un contenido multimedia por su ID.

        Args:
            multimedia_id: ID del contenido multimedia.

        Returns:
            El contenido multimedia encontrado o None.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def update(self, multimedia_id: UUID, multimedia_data: dict) -> Multimedia:
        """
        Actualiza un contenido multimedia existente.

        Args:
            multimedia_id: ID del contenido multimedia.
            multimedia_data: Datos a actualizar.

        Returns:
            El contenido multimedia actualizado.
        """
        pass

    @abstractmethod
    async def delete(self, multimedia_id: UUID) -> bool:
        """
        Elimina un contenido multimedia.

        Args:
            multimedia_id: ID del contenido multimedia a eliminar.

        Returns:
            True si se eliminó correctamente.
        """
        pass

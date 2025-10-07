"""
Caso de uso para crear contenido multimedia.
"""
from app.domain.entities.multimedia import Multimedia
from app.domain.repositories.multimedia_repository import MultimediaRepository


class CreateMultimediaUseCase:
    """
    Caso de uso para crear un nuevo contenido multimedia.

    Aplica las reglas de negocio para la creación de contenido multimedia.
    """

    def __init__(self, multimedia_repository: MultimediaRepository):
        """
        Inicializa el caso de uso con el repositorio.

        Args:
            multimedia_repository: Repositorio de multimedia.
        """
        self._repository = multimedia_repository

    async def execute(self, multimedia_data: dict) -> Multimedia:
        """
        Ejecuta la creación de un nuevo contenido multimedia.

        Args:
            multimedia_data: Datos del contenido multimedia a crear.

        Returns:
            El contenido multimedia creado.

        Raises:
            SupabaseError: Si ocurre un error al crear el contenido.
        """
        # Aquí podrías agregar validaciones de negocio adicionales
        # Por ejemplo, validar URLs, dimensiones, etc.

        return await self._repository.create(multimedia_data)

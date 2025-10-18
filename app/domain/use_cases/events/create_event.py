"""
Caso de uso para la creación de un nuevo evento.
"""

from app.domain.entities.event import Event
from app.domain.entities.event_dto import EventCreateDTO
from app.domain.repositories.event_repository import EventRepository


class CreateEventUseCase:
    """
    Orquesta la lógica de negocio para crear un nuevo evento.
    """

    def __init__(self, event_repository: EventRepository) -> None:
        """
        Inicializa el caso de uso con sus dependencias.

        Args:
            event_repository: Repositorio para interactuar con la capa de datos de eventos.
        """
        self.event_repository = event_repository

    async def execute(self, event_data: EventCreateDTO) -> Event:
        """
        Ejecuta la lógica para crear un evento.

        Args:
            event_data: Datos del evento a crear (DTO de dominio).

        Returns:
            La entidad del evento recién creado.
        """
        # Aquí se podrían añadir lógicas de negocio adicionales, como:
        # - Validar si la fecha del evento es en el futuro.
        # - Comprobar la disponibilidad para esa fecha.
        # - Enviar una notificación por correo electrónico.

        created_event = await self.event_repository.create(event_data)

        return created_event

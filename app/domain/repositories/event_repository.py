"""
Define la interfaz (contrato) para el repositorio de eventos.
"""

from abc import ABC, abstractmethod
from datetime import date

from app.domain.entities.event import Event
from app.domain.entities.event_dto import EventCreateDTO
from app.domain.value_objects.event_status import EventStatus


class EventRepository(ABC):
    """Clase base abstracta para el repositorio de eventos."""

    @abstractmethod
    async def create(self, event_data: EventCreateDTO) -> Event:
        """Crea un nuevo evento en la base de datos."""
        pass

    @abstractmethod
    async def list_events(
        self,
        skip: int = 0,
        limit: int = 100,
        status: EventStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        order_by: str = "event_date",
        order_direction: str = "desc",
    ) -> list[Event]:
        """
        Lista eventos con filtros opcionales y paginación.

        Args:
            skip: Número de registros a saltar para paginación.
            limit: Número máximo de registros a devolver.
            status: Filtro opcional por estado del evento.
            fecha_desde: Filtro opcional para eventos desde esta fecha (inclusive).
            fecha_hasta: Filtro opcional para eventos hasta esta fecha (inclusive).
            order_by: Campo por el cual ordenar los resultados.
            order_direction: Dirección del ordenamiento ("asc" o "desc").

        Returns:
            Lista de entidades Event que cumplen con los filtros.
        """
        pass

    # Aquí se podrían añadir otros métodos como:
    # @abstractmethod
    # async def get_by_id(self, event_id: str) -> Optional[Event]:
    #     pass

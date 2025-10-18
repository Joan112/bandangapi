"""
Define la interfaz (contrato) para el repositorio de eventos.
"""

from abc import ABC, abstractmethod

from app.domain.entities.event import Event
from app.domain.entities.event_dto import EventCreateDTO


class EventRepository(ABC):
    """Clase base abstracta para el repositorio de eventos."""

    @abstractmethod
    async def create(self, event_data: EventCreateDTO) -> Event:
        """Crea un nuevo evento en la base de datos."""
        pass

    # Aquí se podrían añadir otros métodos como:
    # @abstractmethod
    # async def get_by_id(self, event_id: str) -> Optional[Event]:
    #     pass
    #
    # @abstractmethod
    # async def get_all(self) -> list[Event]:
    #     pass

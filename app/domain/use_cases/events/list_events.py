"""
Caso de uso para listar eventos con filtros y paginación.
"""

from datetime import date

from app.core.exceptions import ValidationError
from app.domain.entities.event import Event
from app.domain.repositories.event_repository import EventRepository
from app.domain.value_objects.event_status import EventStatus


class ListEventsUseCase:
    """
    Orquesta la lógica de negocio para listar eventos con filtros opcionales.
    """

    MAX_LIMIT = 100
    DEFAULT_LIMIT = 10
    DEFAULT_SKIP = 0

    def __init__(self, event_repository: EventRepository) -> None:
        """
        Inicializa el caso de uso con sus dependencias.

        Args:
            event_repository: Repositorio para interactuar con la capa de datos de eventos.
        """
        self.event_repository = event_repository

    async def execute(
        self,
        skip: int = DEFAULT_SKIP,
        limit: int = DEFAULT_LIMIT,
        status: EventStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        order_by: str = "event_date",
        order_direction: str = "desc",
    ) -> list[Event]:
        """
        Ejecuta la lógica para listar eventos con filtros opcionales.

        Args:
            skip: Número de registros a saltar para paginación. Default: 0.
            limit: Número máximo de registros a devolver. Default: 10. Max: 100.
            status: Filtro opcional por estado del evento.
            fecha_desde: Filtro opcional para eventos desde esta fecha (inclusive).
            fecha_hasta: Filtro opcional para eventos hasta esta fecha (inclusive).
            order_by: Campo por el cual ordenar los resultados. Default: "event_date".
            order_direction: Dirección del ordenamiento ("asc" o "desc"). Default: "desc".

        Returns:
            Lista de entidades Event que cumplen con los filtros.

        Raises:
            ValidationError: Si los parámetros son inválidos.
        """
        # Validaciones de negocio
        if skip < 0:
            raise ValidationError("El valor de 'skip' debe ser mayor o igual a 0")

        if limit < 1 or limit > self.MAX_LIMIT:
            raise ValidationError(
                f"El valor de 'limit' debe estar entre 1 y {self.MAX_LIMIT}"
            )

        if order_direction not in ("asc", "desc"):
            raise ValidationError(
                "El valor de 'order_direction' debe ser 'asc' o 'desc'"
            )

        # Validar rango de fechas
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ValidationError(
                "La fecha 'fecha_desde' no puede ser posterior a 'fecha_hasta'"
            )

        # Delegar al repositorio
        events = await self.event_repository.list_events(
            skip=skip,
            limit=limit,
            status=status,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            order_by=order_by,
            order_direction=order_direction,
        )

        return events

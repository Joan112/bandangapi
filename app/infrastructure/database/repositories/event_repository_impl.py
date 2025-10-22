"""
Implementación del repositorio de eventos con Supabase.
"""

import logging
from dataclasses import asdict
from datetime import date

from postgrest.exceptions import APIError

from app.core.exceptions import SupabaseError
from app.domain.entities.event import Event
from app.domain.entities.event_dto import EventCreateDTO
from app.domain.repositories.event_repository import EventRepository
from app.domain.value_objects.event_status import EventStatus
from app.infrastructure.external.supabase import supabase_client

logger = logging.getLogger(__name__)


class EventRepositoryImpl(EventRepository):
    """
    Implementación concreta del repositorio de eventos que interactúa con Supabase.
    """

    def __init__(self) -> None:
        """Inicializa el repositorio con el cliente de Supabase."""
        self._supabase_client = supabase_client
        self._table_name = "eventos"

    async def create(self, event_data: EventCreateDTO) -> Event:
        """
        Crea un nuevo evento en la base de datos Supabase.

        Args:
            event_data: Datos del evento a crear (DTO de dominio).

        Returns:
            La entidad del evento recién creado.

        Raises:
            SupabaseError: Si ocurre un error durante la comunicación con Supabase.
        """
        try:
            # Usar cliente regular (RLS permite insertar eventos públicamente)
            client = await self._supabase_client.client

            # Convertir el DTO (dataclass) a diccionario
            event_dict = asdict(event_data)

            # Convertir date a string ISO 8601 para Supabase
            if event_dict.get("event_date"):
                event_dict["event_date"] = event_dict["event_date"].isoformat()

            response = await client.table(self._table_name).insert(event_dict).execute()

            if not response.data or len(response.data) == 0:
                raise SupabaseError("La inserción del evento no devolvió datos.")

            # El registro insertado está en el primer elemento de la lista de datos
            created_event_data = response.data[0]

            # Convertir el diccionario de respuesta a la entidad de dominio Event
            return Event.model_validate(created_event_data)

        except APIError as e:
            # Capturar errores específicos de la API de PostgREST/Supabase
            raise SupabaseError(f"Error de API al crear el evento: {e.message}") from e
        except Exception as e:
            # Capturar cualquier otro error inesperado
            raise SupabaseError(
                f"Un error inesperado ocurrió al crear el evento: {e}"
            ) from e

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
        Lista eventos con filtros opcionales y paginación usando Supabase.

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

        Raises:
            SupabaseError: Si ocurre un error durante la comunicación con Supabase.
        """
        try:
            # Usar cliente de administrador para listar eventos (solo accesible para admins)
            client = await self._supabase_client.admin_client

            # Iniciar query
            query = client.table(self._table_name).select("*")

            # Aplicar filtro de estado si se proporciona
            if status is not None:
                query = query.eq("status", status.value)

            # Aplicar filtro de fecha desde (mayor o igual)
            if fecha_desde is not None:
                query = query.gte("event_date", fecha_desde.isoformat())

            # Aplicar filtro de fecha hasta (menor o igual)
            if fecha_hasta is not None:
                query = query.lte("event_date", fecha_hasta.isoformat())

            # Aplicar ordenamiento
            query = query.order(order_by, desc=(order_direction == "desc"))

            # Aplicar paginación con range
            # range es inclusivo en ambos extremos: range(0, 9) devuelve 10 registros
            query = query.range(skip, skip + limit - 1)

            # Ejecutar query
            response = await query.execute()

            # Convertir response a lista de entidades
            events = [Event.model_validate(event_data) for event_data in response.data]

            logger.info(
                f"Listados {len(events)} eventos con filtros: "
                f"status={status}, fecha_desde={fecha_desde}, fecha_hasta={fecha_hasta}, "
                f"skip={skip}, limit={limit}"
            )

            return events

        except APIError as e:
            # Capturar errores específicos de la API de PostgREST/Supabase
            logger.error(f"Error de API al listar eventos: {e.message}")
            raise SupabaseError(f"Error de API al listar eventos: {e.message}") from e
        except Exception as e:
            # Capturar cualquier otro error inesperado
            logger.error(f"Error inesperado al listar eventos: {e}")
            raise SupabaseError(
                f"Un error inesperado ocurrió al listar eventos: {e}"
            ) from e

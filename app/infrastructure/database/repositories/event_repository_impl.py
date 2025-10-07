"""
Implementación del repositorio de eventos con Supabase.
"""
from postgrest.exceptions import APIError

from app.core.exceptions import SupabaseError
from app.domain.entities.event import Event
from app.domain.repositories.event_repository import EventRepository
from app.infrastructure.external.supabase import supabase_client
from app.presentation.api.v1.schemas.event import EventCreate


class EventRepositoryImpl(EventRepository):
    """
    Implementación concreta del repositorio de eventos que interactúa con Supabase.
    """

    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self._supabase_client = supabase_client
        self._table_name = "eventos"

    async def create(self, event_data: EventCreate) -> Event:
        """
        Crea un nuevo evento en la base de datos Supabase.

        Args:
            event_data: Datos del evento a crear (esquema Pydantic).

        Returns:
            La entidad del evento recién creado.

        Raises:
            SupabaseError: Si ocurre un error durante la comunicación con Supabase.
        """
        try:
            # Usar cliente admin para bypassar RLS
            client = await self._supabase_client.admin_client

            # Convertir el esquema Pydantic a un diccionario sin alias (nombres de columnas reales)
            # mode='json' serializa date/datetime a strings ISO 8601
            event_dict = event_data.model_dump(by_alias=False, mode='json')

            response = await client.table(self._table_name).insert(event_dict).execute()

            if not response.data or len(response.data) == 0:
                raise SupabaseError("La inserción del evento no devolvió datos.")

            # El registro insertado está en el primer elemento de la lista de datos
            created_event_data = response.data[0]

            # Convertir el diccionario de respuesta a la entidad de dominio Event
            return Event.model_validate(created_event_data)

        except APIError as e:
            # Capturar errores específicos de la API de PostgREST/Supabase
            raise SupabaseError(f"Error de API al crear el evento: {e.message}")
        except Exception as e:
            # Capturar cualquier otro error inesperado
            raise SupabaseError(f"Un error inesperado ocurrió al crear el evento: {e}")

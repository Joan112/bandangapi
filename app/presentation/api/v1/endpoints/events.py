"""
Endpoint de la API para gestionar eventos.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.dependencies import get_create_event_use_case, require_role
from app.core.exceptions import SupabaseError
from app.domain.entities.supabase_user import SupabaseUser
from app.domain.use_cases.events.create_event import CreateEventUseCase
from app.presentation.api.v1.schemas.event import EventCreate, EventRead
from app.presentation.middleware.rate_limit import limiter

router = APIRouter()


@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento",
    description="Recibe los datos de un nuevo evento y lo registra en el sistema. Este endpoint es PÚBLICO para permitir formularios de contacto.",
    tags=["Eventos"],
)
@limiter.limit("5/hour")  # Protección anti-spam para endpoint público
async def create_event(
    request: Request,
    event_data: EventCreate,
    use_case: CreateEventUseCase = Depends(get_create_event_use_case),
) -> EventRead:
    """
    Endpoint para crear un nuevo evento.

    **NOTA DE SEGURIDAD**: Este endpoint es PÚBLICO intencionalmente
    para permitir que clientes potenciales soliciten cotizaciones.
    Los datos se validan estrictamente con Pydantic y se almacenan
    con estado 'pending' para revisión manual del equipo.

    **PROTECCIÓN CSRF**: Este endpoint público usa rate limiting estricto (5/hour)
    y validación de origen CORS para prevenir ataques CSRF. Los datos se crean
    con estado 'pending' requiriendo aprobación manual del equipo.

    - **event_data**: Datos del evento a crear validados por el esquema `EventCreate`.
    - **use_case**: Instancia del caso de uso inyectada por FastAPI.
    """
    try:
        # Convertir Pydantic schema a DTO de dominio
        event_dto = event_data.to_dto()

        # Ejecutar use case con DTO
        created_event = await use_case.execute(event_dto)

        # Convertir entidad de dominio a schema de respuesta
        return EventRead.model_validate(created_event)
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo crear el evento: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}",
        ) from e

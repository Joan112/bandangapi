"""
Endpoint de la API para gestionar eventos.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_create_event_use_case
from app.core.exceptions import SupabaseError
from app.domain.use_cases.events.create_event import CreateEventUseCase
from app.presentation.api.v1.schemas.event import EventCreate, EventRead

router = APIRouter()

@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento",
    description="Recibe los datos de un nuevo evento y lo registra en el sistema.",
    tags=["Eventos"]
)
async def create_event(
    event_data: EventCreate,
    use_case: CreateEventUseCase = Depends(get_create_event_use_case)
):
    """
    Endpoint para crear un nuevo evento.

    - **event_data**: Datos del evento a crear validados por el esquema `EventCreate`.
    - **use_case**: Instancia del caso de uso inyectada por FastAPI.
    """
    try:
        created_event = await use_case.execute(event_data)
        return created_event
    except SupabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo crear el evento: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado: {e}"
        )

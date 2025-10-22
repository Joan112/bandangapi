"""
Endpoint de la API para gestionar eventos.
"""

import logging
from datetime import date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.dependencies import (
    get_create_event_use_case,
    get_list_events_use_case,
    require_role,
)
from app.core.exceptions import SupabaseError, ValidationError
from app.domain.entities.supabase_user import SupabaseUser
from app.domain.use_cases.events.create_event import CreateEventUseCase
from app.domain.use_cases.events.list_events import ListEventsUseCase
from app.domain.value_objects.event_status import EventStatus
from app.presentation.api.v1.schemas.event import EventCreate, EventRead
from app.presentation.middleware.rate_limit import limiter

# Logger para auditoría de seguridad
logger = logging.getLogger(__name__)

router = APIRouter()


class OrderByField(str, Enum):
    """Campos válidos para ordenamiento - previene inyección SQL"""

    EVENT_DATE = "event_date"
    CREATED_AT = "created_at"
    NAME = "name"
    LOCATION = "location"
    STATUS = "status"


@router.get(
    "/",
    response_model=list[EventRead],
    status_code=status.HTTP_200_OK,
    summary="Listar eventos",
    description="Obtener lista de eventos con filtros opcionales (solo ADMIN)",
    tags=["Eventos"],
)
@limiter.limit("60/minute")  # Rate limiting razonable para admin panel
async def list_events(
    request: Request,
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Límite de registros"),
    status_filter: EventStatus | None = Query(
        None, alias="status", description="Filtrar por estado"
    ),
    fecha_desde: date | None = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: date | None = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    order_by: OrderByField = Query(
        OrderByField.EVENT_DATE, description="Campo de ordenamiento"
    ),
    order_direction: str = Query(
        "desc", pattern="^(asc|desc)$", description="Dirección de ordenamiento"
    ),
    current_user: SupabaseUser = Depends(require_role("ADMIN")),
    use_case: ListEventsUseCase = Depends(get_list_events_use_case),
) -> list[EventRead]:
    """
    Listar eventos con filtros opcionales.

    **Permisos:** Solo ADMIN o SUPERADMIN

    **Filtros disponibles:**
    - status: pending, confirmed, cancelled
    - fecha_desde: Eventos desde esta fecha (inclusive)
    - fecha_hasta: Eventos hasta esta fecha (inclusive)
    - order_by: Campo para ordenar (event_date, created_at, name, etc.)
    - order_direction: asc o desc

    **Paginación:**
    - skip: Número de registros a saltar (default: 0)
    - limit: Máximo de registros (default: 10, max: 100)

    **Ejemplo de uso:**
    ```
    GET /api/v1/events/?status=pending&limit=20&order_by=event_date&order_direction=asc
    GET /api/v1/events/?fecha_desde=2025-01-01&fecha_hasta=2025-12-31
    ```
    """
    # SECURITY: Log de auditoría de acceso a datos sensibles
    logger.info(
        f"Usuario {current_user.email} (ID: {current_user.id}, Rol: {current_user.role.value}) "
        f"accedió al listado de eventos con filtros: skip={skip}, limit={limit}, "
        f"status={status_filter}, fecha_desde={fecha_desde}, fecha_hasta={fecha_hasta}, "
        f"order_by={order_by.value}, order_direction={order_direction}"
    )

    try:
        events = await use_case.execute(
            skip=skip,
            limit=limit,
            status=status_filter,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            order_by=order_by.value,  # Pasar el valor del enum
            order_direction=order_direction,
        )

        # Convertir entidades de dominio a schemas de respuesta
        return [EventRead.model_validate(event) for event in events]

    except ValidationError as e:
        # SECURITY: Log detallado server-side, mensaje genérico al cliente
        logger.warning(
            f"Error de validación en list_events para usuario {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),  # ValidationError ya tiene mensajes seguros
        ) from e
    except SupabaseError as e:
        # SECURITY: Log detallado server-side, mensaje genérico al cliente
        logger.error(
            f"Error de Supabase en list_events para usuario {current_user.email}: {type(e).__name__} - {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo listar los eventos. Por favor, intente nuevamente.",
        ) from e
    except Exception as e:
        # SECURITY: Log detallado server-side, mensaje genérico al cliente
        logger.error(
            f"Error inesperado en list_events para usuario {current_user.email}: {type(e).__name__} - {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error inesperado. Por favor, intente nuevamente.",
        ) from e


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

        # SECURITY: Log de auditoría para creación de eventos públicos
        logger.info(
            f"Evento creado vía endpoint público: {created_event.name} (ID: {created_event.id}), "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )

        # Convertir entidad de dominio a schema de respuesta
        return EventRead.model_validate(created_event)
    except SupabaseError as e:
        # SECURITY: Log detallado server-side, mensaje genérico al cliente
        logger.error(
            f"Error de Supabase en create_event: {type(e).__name__} - {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el evento. Por favor, intente nuevamente.",
        ) from e
    except Exception as e:
        # SECURITY: Log detallado server-side, mensaje genérico al cliente
        logger.error(
            f"Error inesperado en create_event: {type(e).__name__} - {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error inesperado. Por favor, intente nuevamente.",
        ) from e

"""
Esquemas Pydantic para la validación de datos de Eventos.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr, Field

from app.domain.value_objects.event_status import EventStatus
from app.presentation.api.v1.schemas.base import TrimmedModel

if TYPE_CHECKING:
    from app.domain.entities.event_dto import EventCreateDTO


class EventBase(TrimmedModel):
    """Esquema base para un evento, con los campos comunes."""

    name: str = Field(..., description="Nombre del cliente", max_length=100)
    email: EmailStr = Field(..., description="Correo electrónico del cliente")
    phone: str = Field(..., description="Teléfono de contacto", max_length=20)
    event_type: str = Field(
        ...,
        alias="eventType",
        description="Tipo de evento (Boda, XV Años, etc.)",
        max_length=50,
    )
    event_date: date = Field(..., alias="eventDate", description="Fecha del evento")
    location: str = Field(..., description="Ubicación del evento", max_length=200)
    guest_count: str = Field(
        ..., alias="guestCount", description="Cantidad de invitados", max_length=20
    )
    message: str | None = Field(None, description="Mensaje o notas adicionales")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Juan Pérez",
                "email": "juan.perez@example.com",
                "phone": "+5215512345678",
                "eventType": "Boda",
                "eventDate": "2025-12-20",
                "location": "Salón de Fiestas 'El Jardín'",
                "guestCount": "150-200",
                "message": "Necesitamos cotización para barra de postres.",
            }
        }


class EventCreate(EventBase):
    """Esquema para la creación de un nuevo evento. Hereda de EventBase."""

    def to_dto(self) -> "EventCreateDTO":
        """
        Convertir schema de presentación a DTO de dominio.

        Este método permite la conversión desde la capa de presentación
        hacia el domain layer, manteniendo la separación de capas en
        Clean Architecture.

        Returns:
            EventCreateDTO con los datos del schema.
        """
        from app.domain.entities.event_dto import EventCreateDTO

        return EventCreateDTO(
            name=self.name,
            email=self.email,
            phone=self.phone,
            event_type=self.event_type,
            event_date=self.event_date,
            location=self.location,
            guest_count=self.guest_count,
            message=self.message,
        )


class EventRead(EventBase):
    """Esquema para la lectura de un evento, incluye campos generados por la BD."""

    id: uuid.UUID = Field(..., description="ID único del evento")
    status: EventStatus = Field(..., description="Estado actual del evento")
    created_at: datetime = Field(
        ..., alias="createdAt", description="Fecha de creación del registro"
    )
    updated_at: datetime = Field(
        ..., alias="updatedAt", description="Fecha de última actualización"
    )

    class Config:
        from_attributes = True
        populate_by_name = True

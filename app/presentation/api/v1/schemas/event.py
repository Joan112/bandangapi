"""
Esquemas Pydantic para la validación de datos de Eventos.
"""
from pydantic import EmailStr, Field
from datetime import date, datetime
from typing import Optional
from enum import Enum
import uuid

from app.presentation.api.v1.schemas.base import TrimmedModel

class EventStatus(str, Enum):
    """Enum para los posibles estados de un evento."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class EventBase(TrimmedModel):
    """Esquema base para un evento, con los campos comunes."""
    name: str = Field(..., description="Nombre del cliente", max_length=100)
    email: EmailStr = Field(..., description="Correo electrónico del cliente")
    phone: str = Field(..., description="Teléfono de contacto", max_length=20)
    event_type: str = Field(..., alias="eventType", description="Tipo de evento (Boda, XV Años, etc.)", max_length=50)
    event_date: date = Field(..., alias="eventDate", description="Fecha del evento")
    location: str = Field(..., description="Ubicación del evento", max_length=200)
    guest_count: str = Field(..., alias="guestCount", description="Cantidad de invitados", max_length=20)
    message: Optional[str] = Field(None, description="Mensaje o notas adicionales")

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
                "message": "Necesitamos cotización para barra de postres."
            }
        }

class EventCreate(EventBase):
    """Esquema para la creación de un nuevo evento. Hereda de EventBase."""
    pass

class EventRead(EventBase):
    """Esquema para la lectura de un evento, incluye campos generados por la BD."""
    id: uuid.UUID = Field(..., description="ID único del evento")
    status: EventStatus = Field(..., description="Estado actual del evento")
    created_at: datetime = Field(..., alias="createdAt", description="Fecha de creación del registro")
    updated_at: datetime = Field(..., alias="updatedAt", description="Fecha de última actualización")

    class Config:
        from_attributes = True
        populate_by_name = True
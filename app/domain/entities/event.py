"""
Define la entidad de dominio para un Evento.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr

from app.domain.value_objects.event_status import EventStatus


class Event(BaseModel):
    """Representa un evento en el dominio de la aplicación."""

    id: uuid.UUID
    name: str
    email: EmailStr
    phone: str
    event_type: str
    event_date: date
    location: str
    guest_count: str
    message: str | None = None
    status: EventStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

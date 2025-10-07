"""
Define la entidad de dominio para un Evento.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional
import uuid

from app.presentation.api.v1.schemas.event import EventStatus

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
    message: Optional[str] = None
    status: EventStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

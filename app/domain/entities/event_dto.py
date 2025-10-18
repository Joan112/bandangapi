"""
Data Transfer Objects para Events.

Los DTOs son objetos simples que transfieren datos entre capas,
sin lógica de negocio. Se usan para mantener la independencia
entre capas en Clean Architecture.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class EventCreateDTO:
    """
    DTO para crear un evento (Domain Layer).

    Este DTO es usado por:
    - Use Cases (domain layer)
    - Repositories (domain interfaces)
    - Repository Implementations (infrastructure layer)

    La capa de presentación debe convertir sus schemas Pydantic
    a este DTO antes de invocar los use cases.
    """

    name: str
    email: str
    phone: str
    event_type: str
    event_date: date
    location: str
    guest_count: str
    message: str | None = None

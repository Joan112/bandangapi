"""
Value objects del dominio.

Los value objects son objetos inmutables que representan conceptos
del dominio sin identidad propia.
"""

from app.domain.value_objects.event_status import EventStatus

__all__ = ["EventStatus"]

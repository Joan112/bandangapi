"""
Value objects para eventos.
"""

from enum import Enum


class EventStatus(str, Enum):
    """Estado de un evento en el sistema."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

"""
Define la entidad de dominio para Multimedia.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MultimediaType(str, Enum):
    """Tipo de contenido multimedia"""

    IMAGE = "image"
    VIDEO = "video"


class Multimedia(BaseModel):
    """Representa un contenido multimedia en el dominio de la aplicación."""

    id: UUID
    type: MultimediaType
    title: str
    description: str | None = None
    url: str
    thumbnail: str | None = None
    category: str
    tags: list[str] = Field(default_factory=list)
    featured: bool = False
    uploaded_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    size: int | None = None
    width: int | None = None
    height: int | None = None
    duration: int | None = None
    is_published: bool = False
    order: int = 0

    class Config:
        from_attributes = True

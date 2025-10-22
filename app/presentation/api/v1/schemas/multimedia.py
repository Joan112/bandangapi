"""
Esquemas Pydantic para la validación de datos de Multimedia.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.entities.multimedia import MultimediaType
from app.presentation.api.v1.schemas.base import TrimmedModel


class MultimediaDimensions(TrimmedModel):
    """Dimensiones de una imagen"""

    width: int = Field(..., description="Ancho en píxeles", gt=0)
    height: int = Field(..., description="Alto en píxeles", gt=0)


class MultimediaBase(TrimmedModel):
    """Esquema base para multimedia"""

    type: MultimediaType = Field(..., description="Tipo de contenido (image o video)")
    title: str = Field(..., description="Título descriptivo", max_length=200)
    description: str | None = Field(None, description="Descripción detallada")
    url: str = Field(..., description="URL del recurso multimedia")
    thumbnail: str | None = Field(None, description="URL de la miniatura")
    category: str = Field(..., description="Categoría del contenido", max_length=100)
    tags: list[str] = Field(
        default_factory=list, description="Etiquetas para búsquedas"
    )
    featured: bool = Field(default=False, description="Destacado en página principal")
    size: int | None = Field(None, description="Tamaño del archivo en bytes", ge=0)
    width: int | None = Field(None, description="Ancho de la imagen en píxeles", gt=0)
    height: int | None = Field(None, description="Alto de la imagen en píxeles", gt=0)
    duration: int | None = Field(
        None, description="Duración del video en segundos", ge=0
    )
    is_published: bool = Field(
        default=False, alias="isPublished", description="Estado de publicación"
    )
    order: int = Field(default=0, description="Orden de aparición en galería", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "type": "image",
                "title": "Concierto en vivo - Bandang 2024",
                "description": "Presentación en el Teatro Nacional",
                "url": "https://example.com/images/concierto-2024.jpg",
                "thumbnail": "https://example.com/images/concierto-2024-thumb.jpg",
                "category": "conciertos",
                "tags": ["concierto", "2024", "teatro nacional"],
                "featured": True,
                "size": 2048576,
                "width": 1920,
                "height": 1080,
                "isPublished": True,
                "order": 1,
            }
        }


class MultimediaCreate(MultimediaBase):
    """Esquema para la creación de contenido multimedia"""

    created_by: UUID | None = Field(
        None, alias="createdBy", description="ID del usuario creador"
    )

    class Config:
        populate_by_name = True


class MultimediaUpdate(TrimmedModel):
    """Esquema para actualizar contenido multimedia"""

    title: str | None = Field(None, description="Título descriptivo", max_length=200)
    description: str | None = Field(None, description="Descripción detallada")
    thumbnail: str | None = Field(None, description="URL de la miniatura")
    category: str | None = Field(
        None, description="Categoría del contenido", max_length=100
    )
    tags: list[str] | None = Field(None, description="Etiquetas para búsquedas")
    featured: bool | None = Field(None, description="Destacado en página principal")
    is_published: bool | None = Field(
        None, alias="isPublished", description="Estado de publicación"
    )
    order: int | None = Field(None, description="Orden de aparición en galería", ge=0)

    class Config:
        populate_by_name = True


class MultimediaRead(MultimediaBase):
    """Esquema para la lectura de contenido multimedia"""

    id: UUID = Field(..., description="ID único del contenido")
    uploaded_at: datetime = Field(
        ..., alias="uploadedAt", description="Fecha de subida"
    )
    updated_at: datetime = Field(
        ..., alias="updatedAt", description="Fecha de última actualización"
    )
    created_by: UUID | None = Field(
        None, alias="createdBy", description="ID del usuario creador"
    )

    class Config:
        from_attributes = True
        populate_by_name = True


class MultimediaListResponse(TrimmedModel):
    """Respuesta con lista de contenido multimedia"""

    items: list[MultimediaRead] = Field(
        ..., description="Lista de contenidos multimedia"
    )
    total: int = Field(..., description="Total de elementos", ge=0)
    skip: int = Field(..., description="Elementos omitidos", ge=0)
    limit: int = Field(..., description="Límite de elementos por página", ge=1)


class MultimediaUploadResponse(TrimmedModel):
    """Respuesta después de upload exitoso"""

    id: UUID = Field(..., description="ID único del contenido")
    title: str = Field(..., description="Título del contenido")
    media_type: str = Field(..., description="Tipo de media (image/video)")
    url: str = Field(..., description="URL pública del archivo")
    thumbnail_url: str | None = Field(
        None, description="URL del thumbnail (solo imágenes)"
    )
    storage_path: str = Field(..., description="Ruta en el bucket de Storage")
    file_size: int = Field(..., description="Tamaño del archivo en bytes")
    mime_type: str = Field(..., description="Tipo MIME del archivo")
    original_filename: str = Field(..., description="Nombre original del archivo")
    uploaded_at: datetime = Field(..., description="Fecha y hora de subida")

    class Config:
        from_attributes = True

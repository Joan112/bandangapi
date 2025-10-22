"""
Servicio para gestionar uploads a Supabase Storage
"""

import io
import mimetypes
from typing import Literal
from uuid import uuid4

from PIL import Image

from app.core.exceptions import ValidationError
from app.infrastructure.external.supabase import supabase_client

# Tipos MIME permitidos
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}

# Límites de tamaño (en bytes)
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200 MB

# Configuración de thumbnails
THUMBNAIL_SIZE = (400, 300)
THUMBNAIL_QUALITY = 85


class SupabaseStorageService:
    """
    Servicio para gestionar archivos en Supabase Storage.

    Handles:
    - Upload de imágenes y videos
    - Generación de thumbnails
    - Validación de archivos
    - Eliminación de archivos
    """

    def __init__(self) -> None:
        """Inicializar servicio de Storage"""
        self.bucket_name = "bandang-multimedia"
        self._supabase_client = supabase_client

    def _validate_file(
        self,
        file_bytes: bytes,
        filename: str,
        media_type: Literal["image", "video"],
    ) -> tuple[str, str]:
        """
        Validar archivo antes de subir.

        Args:
            file_bytes: Contenido del archivo en bytes
            filename: Nombre original del archivo
            media_type: Tipo de media ('image' o 'video')

        Returns:
            Tuple (mime_type, extension)

        Raises:
            ValidationError: Si el archivo no es válido
        """
        # Determinar tipo MIME
        mime_type, _ = mimetypes.guess_type(filename)

        if not mime_type:
            raise ValidationError(
                "No se pudo determinar el tipo de archivo. "
                "Asegúrate de que el archivo tenga una extensión válida."
            )

        # Validar tipo MIME según media_type
        if media_type == "image":
            allowed_types = ALLOWED_IMAGE_TYPES
            max_size = MAX_IMAGE_SIZE
        else:  # video
            allowed_types = ALLOWED_VIDEO_TYPES
            max_size = MAX_VIDEO_SIZE

        if mime_type not in allowed_types:
            raise ValidationError(
                f"Tipo de archivo no permitido: {mime_type}. "
                f"Tipos permitidos: {', '.join(allowed_types.keys())}"
            )

        # Validar tamaño
        file_size = len(file_bytes)
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValidationError(
                f"Archivo demasiado grande ({file_size / (1024 * 1024):.2f} MB). "
                f"Tamaño máximo: {max_size_mb:.0f} MB"
            )

        extension = allowed_types[mime_type]
        return mime_type, extension

    def _generate_thumbnail(self, image_bytes: bytes) -> bytes:
        """
        Generar thumbnail de una imagen.

        Args:
            image_bytes: Bytes de la imagen original

        Returns:
            Bytes del thumbnail generado

        Raises:
            ValidationError: Si no se puede procesar la imagen
        """
        try:
            # Abrir imagen
            img: Image.Image = Image.open(io.BytesIO(image_bytes))

            # Convertir a RGB si es necesario (para PNG con transparencia)
            if img.mode in ("RGBA", "LA", "P"):
                # Crear fondo blanco
                background: Image.Image = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background

            # Redimensionar manteniendo aspecto
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Guardar como JPEG optimizado
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            output.seek(0)

            return output.getvalue()

        except Exception as e:
            raise ValidationError(f"Error al generar thumbnail: {e}") from e

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        media_type: Literal["image", "video"],
    ) -> tuple[str, str | None, str, str, int]:
        """
        Subir archivo a Supabase Storage.

        Args:
            file_bytes: Contenido del archivo
            filename: Nombre original del archivo
            media_type: Tipo de media ('image' o 'video')

        Returns:
            Tuple (file_url, thumbnail_url, storage_path, mime_type, file_size)

        Raises:
            ValidationError: Si el archivo no es válido
            Exception: Si hay error al subir
        """
        # Validar archivo
        mime_type, extension = self._validate_file(file_bytes, filename, media_type)

        # Generar UUID único para el archivo
        file_id = uuid4()

        # Determinar carpeta según tipo
        folder = "images" if media_type == "image" else "videos"

        # Construir path del archivo
        storage_path = f"{folder}/{file_id}{extension}"

        try:
            # Obtener cliente de Supabase
            client = await self._supabase_client.client

            # Subir archivo a Storage
            await client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={
                    "content-type": mime_type,
                    "cache-control": "3600",  # Cache de 1 hora
                    "upsert": "false",  # No sobrescribir si existe
                },
            )

            # Obtener URL pública del archivo
            file_url = client.storage.from_(self.bucket_name).get_public_url(
                storage_path
            )

            # Generar thumbnail para imágenes
            thumbnail_url = None
            if media_type == "image":
                try:
                    thumbnail_bytes = self._generate_thumbnail(file_bytes)
                    thumbnail_path = f"thumbnails/{file_id}_thumb.jpg"

                    # Subir thumbnail
                    await client.storage.from_(self.bucket_name).upload(
                        path=thumbnail_path,
                        file=thumbnail_bytes,
                        file_options={
                            "content-type": "image/jpeg",
                            "cache-control": "3600",
                        },
                    )

                    # Obtener URL del thumbnail
                    thumbnail_url = client.storage.from_(
                        self.bucket_name
                    ).get_public_url(thumbnail_path)

                except Exception as e:
                    # No fallar si el thumbnail falla, solo logging
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"No se pudo generar thumbnail para {file_id}: {e}")

            file_size = len(file_bytes)

            return file_url, thumbnail_url, storage_path, mime_type, file_size

        except Exception as e:
            raise Exception(f"Error al subir archivo a Storage: {e}") from e

    async def delete_file(self, storage_path: str) -> bool:
        """
        Eliminar archivo del Storage.

        Args:
            storage_path: Ruta del archivo en el bucket

        Returns:
            True si se eliminó correctamente

        Raises:
            Exception: Si hay error al eliminar
        """
        try:
            client = await self._supabase_client.client

            # Eliminar archivo
            await client.storage.from_(self.bucket_name).remove([storage_path])

            return True

        except Exception as e:
            raise Exception(f"Error al eliminar archivo del Storage: {e}") from e

    async def delete_file_and_thumbnail(
        self, storage_path: str, thumbnail_url: str | None
    ) -> bool:
        """
        Eliminar archivo y su thumbnail del Storage.

        Args:
            storage_path: Ruta del archivo principal
            thumbnail_url: URL del thumbnail (opcional)

        Returns:
            True si se eliminó correctamente
        """
        # Eliminar archivo principal
        await self.delete_file(storage_path)

        # Eliminar thumbnail si existe
        if thumbnail_url:
            try:
                # Extraer path del thumbnail desde la URL
                # URL ejemplo: https://xyz.supabase.co/storage/v1/object/public/bandang-multimedia/thumbnails/uuid_thumb.jpg
                thumbnail_path = thumbnail_url.split(f"{self.bucket_name}/")[-1]
                await self.delete_file(thumbnail_path)
            except Exception as e:
                # No fallar si no se puede eliminar el thumbnail
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"No se pudo eliminar thumbnail {thumbnail_url}: {e}")

        return True


# Singleton instance
storage_service = SupabaseStorageService()

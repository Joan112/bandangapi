"""
Cliente de Supabase para la aplicación
"""

from functools import lru_cache
from typing import Any, TypeVar, cast

from supabase._async.client import AsyncClient
from supabase._async.client import create_client as create_async_client
from supabase.lib.client_options import AsyncClientOptions

from app.core.config import settings

T = TypeVar("T")


class SupabaseClient:
    """
    Cliente de Supabase con métodos de utilidad

    Implementa el patrón Singleton para evitar múltiples conexiones
    y proporciona métodos de alto nivel para operaciones comunes.
    """

    def __init__(self) -> None:
        """Inicializar cliente de Supabase"""
        self._client: AsyncClient | None = None
        self._admin_client: AsyncClient | None = None
        self._options = AsyncClientOptions(
            schema="public",
            headers={"X-Client-Info": f"bandangweb-api/{settings.VERSION}"},
            auto_refresh_token=True,
            persist_session=False,
        )

    async def _ensure_client(self) -> AsyncClient:
        """Asegurar que el cliente está inicializado"""
        if self._client is None:
            self._client = await create_async_client(
                settings.SUPABASE_URL, settings.SUPABASE_KEY, options=self._options
            )
        return self._client

    async def _ensure_admin_client(self) -> AsyncClient:
        """
        Asegurar que el cliente admin está inicializado

        **SECURITY WARNING**: Este cliente usa SUPABASE_SERVICE_ROLE_KEY y BYPASSA RLS.
        """
        if self._admin_client is None:
            self._admin_client = await create_async_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
                options=self._options,
            )
        return self._admin_client

    @property
    async def client(self) -> AsyncClient:
        """
        Obtener cliente nativo de Supabase (respeta RLS policies)

        Este cliente usa la anon/public key y respeta todas las Row Level Security policies.
        Úsalo para todas las operaciones normales que deben respetar permisos de usuario.
        """
        return await self._ensure_client()

    @property
    async def admin_client(self) -> AsyncClient:
        """
        Obtener cliente admin de Supabase (bypasa RLS)

        **SECURITY WARNING**: Este cliente usa service_role_key y BYPASSA todas las RLS policies.
        Úsalo SOLO cuando sea absolutamente necesario.

        Usos legítimos:
        - Acceder a auth.users de Supabase (no accesible vía RLS)
        - Crear recursos en nombre de otros usuarios (fallback crítico)
        - Operaciones administrativas que requieren bypass

        SIEMPRE documenta POR QUÉ necesitas usar admin_client en un comentario.
        """
        return await self._ensure_admin_client()

    async def get_by_id(
        self, table: str, id_value: str | int, select: str = "*"
    ) -> dict[str, Any] | None:
        """
        Obtener un registro por su ID

        Args:
            table: Nombre de la tabla
            id_value: Valor del ID a buscar
            select: Columnas a seleccionar (por defecto todas)

        Returns:
            Registro encontrado o None
        """
        client = await self._ensure_client()
        response = await client.table(table).select(select).eq("id", id_value).execute()

        if response.data and len(response.data) > 0:
            return cast(dict[str, Any], response.data[0])
        return None

    async def get_by_field(
        self, table: str, field: str, value: Any, select: str = "*"
    ) -> dict[str, Any] | None:
        """
        Obtener un registro por un campo específico

        Args:
            table: Nombre de la tabla
            field: Nombre del campo
            value: Valor a buscar
            select: Columnas a seleccionar (por defecto todas)

        Returns:
            Registro encontrado o None
        """
        client = await self._ensure_client()
        response = await client.table(table).select(select).eq(field, value).execute()

        if response.data and len(response.data) > 0:
            return cast(dict[str, Any], response.data[0])
        return None

    async def list_all(
        self,
        table: str,
        select: str = "*",
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Listar todos los registros de una tabla

        Args:
            table: Nombre de la tabla
            select: Columnas a seleccionar (por defecto todas)
            order_by: Campo para ordenar
            limit: Límite de registros
            offset: Desplazamiento

        Returns:
            Lista de registros
        """
        client = await self._ensure_client()
        query = client.table(table).select(select)

        if order_by:
            query = query.order(order_by)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.range(offset, offset + (limit or 1000))

        response = await query.execute()
        return response.data or []

    async def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Crear un nuevo registro

        Args:
            table: Nombre de la tabla
            data: Datos a insertar

        Returns:
            Registro creado
        """
        client = await self._ensure_client()
        response = await client.table(table).insert(data).execute()

        if response.data and len(response.data) > 0:
            return cast(dict[str, Any], response.data[0])

        raise ValueError(f"Error al crear registro en {table}: {response.error}")

    async def update(
        self, table: str, id_value: str | int, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Actualizar un registro existente

        Args:
            table: Nombre de la tabla
            id_value: ID del registro a actualizar
            data: Datos a actualizar

        Returns:
            Registro actualizado
        """
        client = await self._ensure_client()
        response = await client.table(table).update(data).eq("id", id_value).execute()

        if response.data and len(response.data) > 0:
            return cast(dict[str, Any], response.data[0])

        raise ValueError(f"Error al actualizar registro en {table}: {response.error}")

    async def delete(self, table: str, id_value: str | int) -> bool:
        """
        Eliminar un registro

        Args:
            table: Nombre de la tabla
            id_value: ID del registro a eliminar

        Returns:
            True si se eliminó correctamente
        """
        client = await self._ensure_client()
        response = await client.table(table).delete().eq("id", id_value).execute()

        if response.error:
            raise ValueError(f"Error al eliminar registro en {table}: {response.error}")

        return True

    async def execute_rpc(self, function_name: str, params: dict[str, Any]) -> Any:
        """
        Ejecutar una función RPC en Supabase

        Args:
            function_name: Nombre de la función
            params: Parámetros para la función

        Returns:
            Resultado de la función
        """
        client = await self._ensure_client()
        response = await client.rpc(function_name, params).execute()

        if response.error:
            raise ValueError(f"Error al ejecutar RPC {function_name}: {response.error}")

        return response.data


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """
    Obtener instancia singleton del cliente de Supabase

    Returns:
        Cliente de Supabase
    """
    return SupabaseClient()


# Instancia global del cliente
supabase_client = get_supabase_client()

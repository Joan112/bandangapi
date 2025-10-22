"""
Implementación del repositorio de usuarios con Supabase
"""

import logging
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.exceptions import DuplicateEntityError, EntityNotFoundError
from app.domain.entities.supabase_user import SupabaseUser, UserRole
from app.domain.repositories.supabase_user_repository import SupabaseUserRepository
from app.infrastructure.external.supabase import supabase_client

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class SupabaseUserRepositoryImpl(SupabaseUserRepository):
    """
    Implementación del repositorio de usuarios con Supabase
    """

    def __init__(self) -> None:
        """Inicializar repositorio"""
        self._supabase_client = supabase_client

    async def get_by_id(self, user_id: UUID) -> SupabaseUser | None:
        """
        Obtener un usuario por su ID.

        Usa admin_client solo para auth.users (requerido para acceder a datos de autenticación).
        Para profiles usa el cliente regular con RLS policies.

        Args:
            user_id: ID del usuario

        Returns:
            Usuario encontrado o None
        """
        try:
            client = await self._supabase_client.client
            admin_client = await self._supabase_client.admin_client

            # Obtener datos del perfil usando el cliente regular (respeta RLS)
            response = (
                await client.table("profiles")
                .select("*")
                .eq("id", str(user_id))
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            profile_data = response.data[0]

            # SECURITY: Obtener datos de auth.users usando admin_client (NECESARIO - no hay otra forma)
            # Justificación: La tabla auth.users de Supabase NO es accesible vía RLS policies.
            # El único método para obtener email, email_confirmed_at, etc. es mediante admin API.
            # El cliente regular se usa para 'profiles' (respeta RLS), admin solo para 'auth.users'.
            auth_response = await admin_client.auth.admin.get_user_by_id(str(user_id))
            auth_user = auth_response.user if auth_response else None

            if not auth_user:
                # Esto no debería ocurrir si el perfil existe, debido a la FK
                return None

            # Combinar datos
            user_data = {
                **profile_data,
                "email": auth_user.email,
                "email_confirmed_at": auth_user.email_confirmed_at,
                "last_sign_in_at": auth_user.last_sign_in_at,
                "phone": auth_user.phone,
                "created_at": auth_user.created_at,
                "updated_at": auth_user.updated_at,
            }

            return SupabaseUser.from_dict(user_data)
        except Exception as e:
            # Usar logging estructurado para auditoría y debugging
            logger.error(
                f"Error al obtener usuario por ID {user_id}: {type(e).__name__} - {str(e)}"
            )
            return None

    async def get_by_email(self, email: str) -> SupabaseUser | None:
        """
        Obtener un usuario por su email

        Args:
            email: Email del usuario

        Returns:
            Usuario encontrado o None
        """
        try:
            client = await self._supabase_client.client
            # Usar la función RPC personalizada
            response = await client.rpc(
                "get_user_by_email", {"p_email": email}
            ).execute()

            if not response.data or len(response.data) == 0:
                return None

            return SupabaseUser.from_dict(response.data[0])
        except Exception as e:
            logger.error(
                f"Error al obtener usuario por email {email}: {type(e).__name__} - {str(e)}"
            )
            return None

    async def list_users(
        self, skip: int = 0, limit: int = 100, role: UserRole | None = None
    ) -> list[SupabaseUser]:
        """
        Listar usuarios con paginación y filtros opcionales

        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            role: Filtrar por rol

        Returns:
            Lista de usuarios
        """
        try:
            client = await self._supabase_client.client
            query = client.table("profiles").select("*")

            # Aplicar filtro por rol si se especifica
            if role:
                query = query.eq("role", role.value)

            # Aplicar paginación
            query = query.range(skip, skip + limit - 1)

            # Ejecutar consulta
            response = await query.execute()

            if not response.data:
                return []

            return [SupabaseUser.from_dict(user_data) for user_data in response.data]
        except Exception as e:
            logger.error(f"Error al listar usuarios: {type(e).__name__} - {str(e)}")
            return []

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> SupabaseUser:
        """
        Crea un nuevo usuario y se asegura de que su perfil exista.

        Este método es robusto contra fallos del trigger de la base de datos.
        Primero, intenta obtener el perfil creado por el trigger. Si no lo encuentra,
        lo crea manualmente como medida de seguridad.
        """
        try:
            # SECURITY: admin_client se usa SOLO para operaciones que lo requieren absolutamente
            admin_client = await self._supabase_client.admin_client
            client = await self._supabase_client.client

            # 1. Verificar si ya existe un perfil con ese email para evitar errores.
            # NOTA: Usar cliente regular para verificación (respeta RLS)
            existing_profile = (
                await client.table("profiles").select("id").eq("email", email).execute()
            )
            if existing_profile.data:
                raise DuplicateEntityError("Usuario", "email", email)

            # 2. Registrar el usuario en `auth.users`.
            # NOTA: Usar cliente regular - Supabase Auth permite registro público
            signup_response = await client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}},
                }
            )

            if not signup_response.user:
                raise ValueError(
                    "La respuesta de Supabase Auth no contiene un usuario."
                )

            user_id = UUID(signup_response.user.id)

            # 3. Intentar obtener el perfil, asumiendo que el trigger funcionó.
            # NOTA: El usuario debe confirmar su email mediante el link enviado por Supabase.
            import asyncio

            user = await self.get_by_id(user_id)
            if not user:
                await asyncio.sleep(1.5)  # Esperar un poco más por si hay retardo
                user = await self.get_by_id(user_id)

            # 4. Si el perfil sigue sin existir, crearlo manualmente.
            if not user:
                logger.warning(
                    f"Perfil no encontrado para usuario {user_id}, creando manualmente..."
                )

                profile_data = {
                    "id": str(user_id),
                    "email": email,
                    "full_name": full_name,
                    "role": role.value if hasattr(role, 'value') else role,
                }

                try:
                    # SECURITY: Usar admin_client para insertar perfil manualmente (FALLBACK CRÍTICO)
                    # Justificación: El perfil se crea en nombre de otro usuario (user_id != current_user)
                    # por lo que RLS policies lo bloquearían. Esto solo ocurre si el trigger de BD falla.
                    insert_response = (
                        await admin_client.table("profiles")
                        .insert(profile_data)
                        .execute()
                    )
                    logger.info(
                        f"Perfil creado manualmente. Respuesta: {insert_response.data}"
                    )

                    # Si la inserción manual fue exitosa, construir el usuario directamente
                    if insert_response.data and len(insert_response.data) > 0:
                        profile = insert_response.data[0]

                        # SECURITY: Obtener datos de auth.users (requiere admin_client)
                        # Justificación: Mismo que get_by_id() - auth.users no accesible vía RLS
                        auth_response = await admin_client.auth.admin.get_user_by_id(
                            str(user_id)
                        )
                        auth_user = auth_response.user if auth_response else None

                        if auth_user:
                            # Combinar datos del perfil y auth
                            user_data = {
                                **profile,
                                "email": auth_user.email,
                                "email_confirmed_at": auth_user.email_confirmed_at,
                                "last_sign_in_at": auth_user.last_sign_in_at,
                                "phone": auth_user.phone,
                                "created_at": auth_user.created_at,
                                "updated_at": auth_user.updated_at,
                            }
                            user = SupabaseUser.from_dict(user_data)
                            logger.info(f"Usuario creado exitosamente: {user.email}")
                except Exception as insert_error:
                    logger.error(
                        f"Error al insertar perfil manualmente: {insert_error}"
                    )

            # 5. Si después de todos los intentos el perfil no existe, lanzar un error definitivo.
            if not user:
                logger.error(
                    f"FALLO CRÍTICO: No se pudo obtener ni crear el perfil del usuario (ID: {user_id}). "
                    f"Verificar RLS policies en tabla 'profiles' de Supabase."
                )
                raise ValueError(
                    f"No se pudo obtener ni crear el perfil del usuario (ID: {user_id})."
                )

            return user
        except APIError as e:
            if "user already registered" in str(e.message).lower():
                raise DuplicateEntityError("Usuario", "email", email) from e
            raise ValueError(f"Error de API de Supabase al crear usuario: {e}") from e
        except DuplicateEntityError:
            # Re-lanzar DuplicateEntityError sin modificar para que el endpoint retorne 409 Conflict
            raise
        except Exception as e:
            raise ValueError(f"Error inesperado al crear usuario: {e}") from e

    async def update_user(
        self,
        user_id: UUID,
        full_name: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> SupabaseUser:
        """
        Actualizar un usuario existente

        Args:
            user_id: ID del usuario
            full_name: Nuevo nombre completo (opcional)
            role: Nuevo rol (opcional)
            is_active: Nuevo estado (opcional)

        Returns:
            Usuario actualizado
        """
        try:
            # Verificar si el usuario existe
            user = await self.get_by_id(user_id)
            if not user:
                raise EntityNotFoundError(entity="Usuario", entity_id=str(user_id))

            # Preparar datos a actualizar
            update_data: dict[str, Any] = {}

            if full_name is not None:
                update_data["full_name"] = full_name

            if role is not None:
                update_data["role"] = role.value

            if is_active is not None:
                update_data["is_active"] = is_active

            if not update_data:
                return user  # No hay cambios que hacer

            client = await self._supabase_client.client
            # Actualizar perfil
            await client.table("profiles").update(update_data).eq(
                "id", str(user_id)
            ).execute()

            # Si se actualizó el nombre, también actualizar los metadatos del usuario
            if full_name is not None:
                await client.auth.admin.update_user_by_id(
                    str(user_id), {"user_metadata": {"full_name": full_name}}
                )

            # Obtener el usuario actualizado
            updated_user = await self.get_by_id(user_id)
            if not updated_user:
                raise EntityNotFoundError(entity="Usuario", entity_id=str(user_id))

            return updated_user
        except EntityNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Error al actualizar usuario: {e}") from e

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Eliminar un usuario

        Args:
            user_id: ID del usuario

        Returns:
            True si se eliminó correctamente
        """
        try:
            # Verificar si el usuario existe
            user = await self.get_by_id(user_id)
            if not user:
                raise EntityNotFoundError(entity="Usuario", entity_id=str(user_id))

            client = await self._supabase_client.client
            # Eliminar usuario en Supabase Auth
            # Esto también eliminará el perfil debido a la restricción ON DELETE CASCADE
            await client.auth.admin.delete_user(str(user_id))

            return True
        except EntityNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Error al eliminar usuario: {e}") from e

    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Cambiar la contraseña de un usuario

        Args:
            user_id: ID del usuario
            new_password: Nueva contraseña

        Returns:
            True si se cambió correctamente
        """
        try:
            # Verificar si el usuario existe
            user = await self.get_by_id(user_id)
            if not user:
                raise EntityNotFoundError(entity="Usuario", entity_id=str(user_id))

            client = await self._supabase_client.client
            # Cambiar contraseña
            await client.auth.admin.update_user_by_id(
                str(user_id), {"password": new_password}
            )

            return True
        except EntityNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Error al cambiar contraseña: {e}") from e

    async def authenticate(
        self, email: str, password: str
    ) -> tuple[SupabaseUser, str, str] | None:
        """
        Autentica a un usuario y devuelve el usuario y los tokens de Supabase.
        """
        try:
            client = await self._supabase_client.client

            # Autenticar con Supabase Auth
            auth_response = await client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if not auth_response.user or not auth_response.session:
                # Credenciales incorrectas o usuario no confirmado
                return None

            # Obtener el perfil completo del usuario
            user_profile = await self.get_by_id(UUID(auth_response.user.id))
            if not user_profile:
                # Esto no debería pasar si el login fue exitoso, pero es una salvaguarda
                return None

            access_token = auth_response.session.access_token
            refresh_token = auth_response.session.refresh_token

            return user_profile, access_token, refresh_token
        except Exception as e:
            # El cliente de Supabase puede lanzar una excepción con detalles
            # si el email no está confirmado, por ejemplo.
            logger.error(
                f"Error de autenticación en Supabase: {type(e).__name__} - {str(e)}"
            )
            return None

    # Métodos wrapper genéricos para compatibilidad con endpoints
    async def list_all(
        self, skip: int = 0, limit: int = 100, role: str | None = None
    ) -> list[SupabaseUser]:
        """
        Wrapper genérico para list_users.

        Args:
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            role: Filtro opcional por rol

        Returns:
            Lista de usuarios
        """
        # Convertir string a UserRole si es necesario
        role_enum: UserRole | None = None
        if role is not None:
            role_enum = UserRole(role)

        return await self.list_users(skip=skip, limit=limit, role=role_enum)

    async def update(self, user_id: UUID, update_data: dict[str, Any]) -> SupabaseUser:
        """
        Wrapper genérico para update_user.

        Args:
            user_id: ID del usuario a actualizar
            update_data: Diccionario con los campos a actualizar

        Returns:
            Usuario actualizado

        Raises:
            EntityNotFoundError: Si el usuario no existe
        """
        return await self.update_user(
            user_id=user_id,
            full_name=update_data.get("full_name"),
            role=UserRole(update_data["role"]) if "role" in update_data else None,
            is_active=update_data.get("is_active"),
        )

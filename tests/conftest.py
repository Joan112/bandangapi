"""
Fixtures para pytest
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.infrastructure.external.supabase.client import SupabaseClient
from app.main import app

# Configurar variables de entorno para tests
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "True"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-purposes-only-min-32-chars"


@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para toda la sesión de tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_supabase_client() -> SupabaseClient:
    """
    Cliente de Supabase mockeado para tests.

    En lugar de conectarse a Supabase real, devuelve mocks
    que pueden ser configurados en cada test.
    """
    client = SupabaseClient()
    # Mockear el cliente interno
    client._client = AsyncMock()
    client._admin_client = AsyncMock()

    # Configurar mocks por defecto
    mock_response = MagicMock()
    mock_response.data = []
    mock_response.error = None

    # Mock para table queries
    mock_table = AsyncMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.range.return_value = mock_table
    mock_table.execute = AsyncMock(return_value=mock_response)

    client._client.table.return_value = mock_table
    client._admin_client.table.return_value = mock_table

    return client


@pytest.fixture(scope="function")
async def client(monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP de test para hacer requests a la API.

    Mockea Supabase para evitar llamadas reales durante tests.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4

    # Deshabilitar rate limiter durante tests
    monkeypatch.setattr("app.presentation.middleware.rate_limit.limiter.enabled", False)

    # Mock del cliente Supabase
    mock_supabase = MagicMock()

    # Storage para usuarios creados (key: email, value: user_data)
    created_users_by_email = {}
    created_users_by_id = {}
    # Storage para sesiones activas (key: access_token, value: session_data)
    active_sessions = {}
    # Storage para refresh tokens (key: refresh_token, value: session_data)
    refresh_tokens = {}

    # Mock de auth.sign_up
    async def mock_sign_up(credentials):
        from postgrest.exceptions import APIError

        email = credentials.get("email")
        password = credentials.get("password")

        # Verificar si el email ya existe (simular error de Supabase)
        if email in created_users_by_email:
            # Simular error de Supabase por email duplicado
            raise APIError({"message": "User already registered", "code": "23505"})

        user_id = str(uuid4())

        # Create mock user object
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = email
        mock_user.user_metadata = {
            "full_name": credentials.get("options", {})
            .get("data", {})
            .get("full_name", "")
        }
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.updated_at = "2024-01-01T00:00:00Z"
        mock_user.email_confirmed_at = (
            "2024-01-01T00:00:00Z"  # Email confirmado para tests
        )
        mock_user.last_sign_in_at = "2024-01-01T00:00:00Z"
        mock_user.phone = None
        mock_user.app_metadata = {}
        mock_user.aud = "authenticated"

        # Guardar usuario en storage
        user_data = {
            "user": mock_user,
            "email": email,
            "password": password,  # Guardar para validación en login
            "full_name": credentials.get("options", {})
            .get("data", {})
            .get("full_name", ""),
            "role": credentials.get("options", {})
            .get("data", {})
            .get("role", "user"),  # Rol personalizado (solo para tests)
        }
        created_users_by_email[email] = user_data
        created_users_by_id[user_id] = user_data

        # Create mock session
        mock_session = MagicMock()
        mock_session.access_token = "mock_access_token"
        mock_session.refresh_token = "mock_refresh_token"
        mock_session.token_type = "bearer"
        mock_session.user = mock_user

        # Create mock response
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        return mock_response

    # Mock de auth.sign_in_with_password
    async def mock_sign_in(credentials):
        from gotrue.errors import AuthApiError

        from app.core.security import create_access_token, create_refresh_token

        email = credentials.get("email")
        password = credentials.get("password")

        # Buscar usuario registrado
        user_data = created_users_by_email.get(email)

        # Si el usuario no existe o la contraseña no coincide, error 401
        if not user_data or user_data.get("password") != password:
            raise AuthApiError("Invalid login credentials", 400)

        # Usuario y password válidos, devolver sesión
        mock_user = user_data["user"]

        # Generar tokens reales usando las funciones de security.py
        access_token = create_access_token(subject=str(mock_user.id))
        refresh_token = create_refresh_token(subject=str(mock_user.id))

        # Guardar tokens en storage
        session_data = {
            "user_id": mock_user.id,
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
        active_sessions[access_token] = session_data
        refresh_tokens[refresh_token] = session_data

        # Create mock session
        mock_session = MagicMock()
        mock_session.access_token = access_token
        mock_session.refresh_token = refresh_token
        mock_session.token_type = "bearer"
        mock_session.user = mock_user

        # Create mock response
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        return mock_response

    # Mock de auth.refresh_session
    async def mock_refresh_session(refresh_token_str):
        from gotrue.errors import AuthApiError

        from app.core.security import create_access_token, create_refresh_token

        # Buscar sesión por refresh_token
        session_data = refresh_tokens.get(refresh_token_str)

        if not session_data:
            raise AuthApiError("Invalid refresh token", 400)

        user_id = session_data["user_id"]
        email = session_data["email"]

        # Buscar usuario
        user_data = created_users_by_id.get(user_id)
        if not user_data:
            raise AuthApiError("User not found", 404)

        # Generar nuevos tokens
        new_access_token = create_access_token(subject=str(user_id))
        new_refresh_token = create_refresh_token(subject=str(user_id))

        # Revocar tokens antiguos
        old_access_token = session_data["access_token"]
        if old_access_token in active_sessions:
            del active_sessions[old_access_token]
        if refresh_token_str in refresh_tokens:
            del refresh_tokens[refresh_token_str]

        # Guardar nuevos tokens
        new_session_data = {
            "user_id": user_id,
            "email": email,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }
        active_sessions[new_access_token] = new_session_data
        refresh_tokens[new_refresh_token] = new_session_data

        # Create mock response
        mock_user = user_data["user"]

        mock_session = MagicMock()
        mock_session.access_token = new_access_token
        mock_session.refresh_token = new_refresh_token
        mock_session.token_type = "bearer"
        mock_session.user = mock_user

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        return mock_response

    # Mock de auth.sign_out
    async def mock_sign_out():
        # En un mock simplificado, sign_out no recibe parámetros
        # En la implementación real, Supabase usa el token del contexto
        # Para tests, simplemente retornamos None (éxito)
        # La revocación real de tokens se maneja por el endpoint
        return None

    # Mock de auth.get_user
    async def mock_get_user(token):
        from app.core.security import decode_token

        # Buscar sesión por access_token
        session_data = active_sessions.get(token)

        if not session_data:
            # Intentar decodificar el token para obtener user_id
            try:
                payload = decode_token(token, expected_type="access")
                user_id = payload.get("sub")

                # Buscar usuario por ID
                user_data = created_users_by_id.get(user_id)
                if not user_data:
                    return None

                # Crear respuesta con el usuario
                mock_user = user_data["user"]
                mock_response = MagicMock()
                mock_response.user = mock_user
                return mock_response
            except Exception:
                return None

        # Usuario encontrado en sesiones activas
        user_id = session_data["user_id"]
        user_data = created_users_by_id.get(user_id)

        if not user_data:
            return None

        mock_user = user_data["user"]
        mock_response = MagicMock()
        mock_response.user = mock_user
        return mock_response

    # Mock de admin methods
    mock_admin = MagicMock()

    async def mock_update_user_by_id(user_id, data):
        return MagicMock()  # Éxito

    async def mock_get_user_by_id(user_id):
        """Mock para obtener usuario de auth.users"""
        user_data = created_users_by_id.get(user_id)
        if user_data:
            mock_response = MagicMock()
            mock_response.user = user_data["user"]
            return mock_response
        return None

    mock_admin.update_user_by_id = mock_update_user_by_id
    mock_admin.get_user_by_id = mock_get_user_by_id
    mock_supabase.auth.admin = mock_admin

    mock_supabase.auth.sign_up = mock_sign_up
    mock_supabase.auth.sign_in_with_password = mock_sign_in
    mock_supabase.auth.refresh_session = mock_refresh_session
    mock_supabase.auth.sign_out = mock_sign_out
    mock_supabase.auth.get_user = mock_get_user

    # Storage para perfiles
    profiles_storage = {}

    # Mock de table operations
    class MockTableBuilder:
        def __init__(self, table_name):
            self.table_name = table_name
            self._operation = None
            self._data = None
            self._filters = {}

        def select(self, columns="*"):
            self._operation = "select"
            return self

        def insert(self, data):
            self._operation = "insert"
            self._data = data
            return self

        def update(self, data):
            self._operation = "update"
            self._data = data
            return self

        def delete(self):
            self._operation = "delete"
            return self

        def eq(self, column, value):
            self._filters[column] = value
            return self

        def order(self, column):
            return self

        def limit(self, count):
            return self

        def range(self, start, end):
            return self

        async def execute(self):
            mock_response = MagicMock()

            if self.table_name == "profiles":
                if self._operation == "insert":
                    # Insertar perfil en storage con valores por defecto
                    profile_id = self._data.get("id")
                    profile_email = self._data.get("email")

                    # Buscar rol del usuario en storage si existe
                    user_role = "user"
                    if profile_id in created_users_by_id:
                        user_role = created_users_by_id[profile_id].get("role", "user")
                    elif profile_email in created_users_by_email:
                        user_role = created_users_by_email[profile_email].get(
                            "role", "user"
                        )

                    # Agregar campos por defecto si no están presentes
                    complete_profile = {
                        **self._data,
                        "role": self._data.get(
                            "role", user_role
                        ),  # Usar rol del usuario
                        "is_active": self._data.get("is_active", True),
                        "created_at": self._data.get(
                            "created_at", "2024-01-01T00:00:00Z"
                        ),
                        "updated_at": self._data.get(
                            "updated_at", "2024-01-01T00:00:00Z"
                        ),
                    }
                    profiles_storage[profile_id] = complete_profile

                    # IMPORTANTE: También guardar en storage de emails para detectar duplicados
                    # Esto simula la constraint única de email en la tabla profiles
                    if profile_email and profile_email in created_users_by_email:
                        # Si el email ya existe, actualizar el perfil del usuario existente
                        # (esto pasa cuando se crea manualmente el perfil después del sign_up)
                        pass

                    mock_response.data = [complete_profile]
                    mock_response.count = None
                elif self._operation == "select":
                    # Buscar perfil por ID
                    if "id" in self._filters:
                        profile = profiles_storage.get(self._filters["id"])
                        mock_response.data = [profile] if profile else []
                    elif "email" in self._filters:
                        # Buscar por email - verificar tanto en profiles_storage como en created_users
                        matching = [
                            p
                            for p in profiles_storage.values()
                            if p.get("email") == self._filters["email"]
                        ]

                        # Si no hay match en profiles_storage, verificar en created_users_by_email
                        # (para detectar usuarios creados por sign_up)
                        if (
                            not matching
                            and self._filters["email"] in created_users_by_email
                        ):
                            # Crear perfil "virtual" del usuario ya registrado para simular
                            # que el perfil existe (aunque todavía no se insertó manualmente)
                            user_data = created_users_by_email[self._filters["email"]]
                            virtual_profile = {
                                "id": user_data["user"].id,
                                "email": self._filters["email"],
                            }
                            matching = [virtual_profile]

                        mock_response.data = matching
                    else:
                        mock_response.data = list(profiles_storage.values())
                    mock_response.count = len(mock_response.data)
                elif self._operation == "update":
                    # Actualizar perfil
                    if "id" in self._filters:
                        profile_id = self._filters["id"]
                        if profile_id in profiles_storage:
                            # Actualizar campos del perfil
                            profiles_storage[profile_id].update(self._data)
                            mock_response.data = [profiles_storage[profile_id]]
                            mock_response.count = 1
                        else:
                            mock_response.data = []
                            mock_response.count = 0
                    else:
                        mock_response.data = []
                        mock_response.count = 0
                else:
                    mock_response.data = []
                    mock_response.count = None
            else:
                mock_response.data = []
                mock_response.count = None

            return mock_response

    def mock_table(table_name):
        return MockTableBuilder(table_name)

    mock_supabase.table = mock_table

    # Patchear el cliente Supabase
    monkeypatch.setattr(
        "app.infrastructure.external.supabase.client.supabase_client._client",
        mock_supabase,
    )
    monkeypatch.setattr(
        "app.infrastructure.external.supabase.client.supabase_client._admin_client",
        mock_supabase,
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_user_data() -> dict[str, str]:
    """Datos de usuario de ejemplo para tests"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_event_data() -> dict[str, str]:
    """Datos de evento de ejemplo para tests"""
    return {
        "name": "Juan Pérez",
        "email": "juan.perez@example.com",
        "phone": "+5215512345678",
        "eventType": "Boda",
        "eventDate": "2025-12-20",
        "location": "Salón de Fiestas 'El Jardín'",
        "guestCount": "150-200",
        "message": "Necesitamos cotización para barra de postres.",
    }


@pytest.fixture
def sample_multimedia_data() -> dict[str, str]:
    """Datos de multimedia de ejemplo para tests"""
    return {
        "title": "Video promocional",
        "mediaType": "video",
        "url": "https://example.com/video.mp4",
        "thumbnailUrl": "https://example.com/thumbnail.jpg",
        "description": "Video de muestra",
    }


# ============================================================================
# Fixtures para Tests de Eventos
# ============================================================================


@pytest.fixture
def mock_admin_dependency(client: AsyncClient):
    """
    Mock de la dependencia get_current_user para simular usuario ADMIN.

    Usa dependency_overrides de FastAPI para inyectar un usuario ADMIN.
    """
    from app.core.dependencies import get_current_user
    from app.domain.entities.supabase_user import SupabaseUser, UserRole
    from app.main import app
    from uuid import uuid4

    mock_admin_user = SupabaseUser(
        id=uuid4(),
        email="admin@test.com",
        full_name="Admin User",
        role=UserRole.ADMIN,  # Usar el enum UserRole
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    async def _mock_get_current_user():
        return mock_admin_user

    # Override la dependencia en la app de FastAPI
    app.dependency_overrides[get_current_user] = _mock_get_current_user

    yield mock_admin_user

    # Limpiar después del test
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user_token(client: AsyncClient) -> str:
    """
    Fixture que retorna token de usuario ADMIN.

    NOTA: Este token debe usarse junto con mock_admin_dependency
    para bypasear la verificación de rol en los endpoints.
    """
    admin_data = {
        "email": "admin@test.com",
        "password": "AdminPassword123!",
        "full_name": "Admin User",
    }

    # Registrar usuario
    await client.post("/api/v1/auth/register", json=admin_data)

    # Login para obtener token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_data["email"], "password": admin_data["password"]},
    )

    tokens = login_response.json()
    return tokens["access_token"]


@pytest.fixture
def mock_superadmin_dependency(client: AsyncClient):
    """
    Mock de la dependencia get_current_user para simular usuario SUPERADMIN.

    Usa dependency_overrides de FastAPI para inyectar un usuario SUPERADMIN.
    """
    from app.core.dependencies import get_current_user
    from app.domain.entities.supabase_user import SupabaseUser, UserRole
    from app.main import app
    from uuid import uuid4

    mock_superadmin_user = SupabaseUser(
        id=uuid4(),
        email="superadmin@test.com",
        full_name="Super Admin User",
        role=UserRole.SUPERADMIN,  # Usar el enum UserRole
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    async def _mock_get_current_user():
        return mock_superadmin_user

    # Override la dependencia en la app de FastAPI
    app.dependency_overrides[get_current_user] = _mock_get_current_user

    yield mock_superadmin_user

    # Limpiar después del test
    app.dependency_overrides.clear()


@pytest.fixture
async def superadmin_user_token(client: AsyncClient) -> str:
    """Fixture que retorna token de usuario SUPERADMIN."""
    superadmin_data = {
        "email": "superadmin@test.com",
        "password": "SuperAdminPassword123!",
        "full_name": "Super Admin User",
    }

    # Registrar usuario
    await client.post("/api/v1/auth/register", json=superadmin_data)

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": superadmin_data["email"],
            "password": superadmin_data["password"],
        },
    )

    tokens = login_response.json()
    return tokens["access_token"]


@pytest.fixture
async def regular_user_token(client: AsyncClient) -> str:
    """Fixture que retorna token de usuario regular (USER)."""
    user_data = {
        "email": "user@test.com",
        "password": "UserPassword123!",
        "full_name": "Regular User",
    }

    # Registrar usuario
    await client.post("/api/v1/auth/register", json=user_data)

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )

    tokens = login_response.json()
    return tokens["access_token"]

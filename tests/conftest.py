"""
Fixtures para pytest
"""

import asyncio
import os
from collections.abc import AsyncGenerator
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
        mock_user.email_confirmed_at = None
        mock_user.last_sign_in_at = None
        mock_user.phone = None
        mock_user.app_metadata = {}
        mock_user.aud = "authenticated"

        # Guardar usuario en storage
        user_data = {
            "user": mock_user,
            "email": email,
            "password": password,  # Guardar para validación en login
            "full_name": credentials.get("options", {}).get("data", {}).get("full_name", ""),
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

        email = credentials.get("email")
        password = credentials.get("password")

        # Buscar usuario registrado
        user_data = created_users_by_email.get(email)

        # Si el usuario no existe o la contraseña no coincide, error 401
        if not user_data or user_data.get("password") != password:
            raise AuthApiError("Invalid login credentials", 400)

        # Usuario y password válidos, devolver sesión
        mock_user = user_data["user"]

        # Create mock session
        mock_session = MagicMock()
        mock_session.access_token = f"mock_access_token_{mock_user.id}"
        mock_session.refresh_token = f"mock_refresh_token_{mock_user.id}"
        mock_session.token_type = "bearer"
        mock_session.user = mock_user

        # Create mock response
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

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

                    # Agregar campos por defecto si no están presentes
                    complete_profile = {
                        **self._data,
                        "is_active": self._data.get("is_active", True),
                        "created_at": self._data.get("created_at", "2024-01-01T00:00:00Z"),
                        "updated_at": self._data.get("updated_at", "2024-01-01T00:00:00Z"),
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
                        matching = [p for p in profiles_storage.values() if p.get("email") == self._filters["email"]]

                        # Si no hay match en profiles_storage, verificar en created_users_by_email
                        # (para detectar usuarios creados por sign_up)
                        if not matching and self._filters["email"] in created_users_by_email:
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

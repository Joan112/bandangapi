"""
Fixtures para pytest
"""

import asyncio
import os
from typing import AsyncGenerator
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
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    # Mock del cliente Supabase
    mock_supabase = MagicMock()

    # Mock de auth.sign_up
    async def mock_sign_up(credentials):
        user_id = str(uuid4())

        # Create mock user object
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = credentials.get('email')
        mock_user.user_metadata = {
            'full_name': credentials.get('options', {}).get('data', {}).get('full_name', '')
        }
        mock_user.created_at = '2024-01-01T00:00:00Z'
        mock_user.app_metadata = {}
        mock_user.aud = 'authenticated'

        # Create mock session
        mock_session = MagicMock()
        mock_session.access_token = 'mock_access_token'
        mock_session.refresh_token = 'mock_refresh_token'
        mock_session.token_type = 'bearer'
        mock_session.user = mock_user

        # Create mock response
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        return mock_response

    # Mock de auth.sign_in_with_password
    async def mock_sign_in(credentials):
        user_id = str(uuid4())

        # Create mock user object
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = credentials.get('email')
        mock_user.user_metadata = {'full_name': 'Test User'}
        mock_user.created_at = '2024-01-01T00:00:00Z'
        mock_user.app_metadata = {}
        mock_user.aud = 'authenticated'

        # Create mock session
        mock_session = MagicMock()
        mock_session.access_token = 'mock_access_token'
        mock_session.refresh_token = 'mock_refresh_token'
        mock_session.token_type = 'bearer'
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
    mock_admin.update_user_by_id = mock_update_user_by_id
    mock_supabase.auth.admin = mock_admin

    mock_supabase.auth.sign_up = mock_sign_up
    mock_supabase.auth.sign_in_with_password = mock_sign_in

    # Mock de table operations
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.range.return_value = mock_table

    async def mock_execute():
        # Return a mock response object
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.count = None
        return mock_response

    mock_table.execute = mock_execute
    mock_supabase.table.return_value = mock_table

    # Patchear el cliente Supabase
    monkeypatch.setattr('app.infrastructure.external.supabase.client.supabase_client._client', mock_supabase)
    monkeypatch.setattr('app.infrastructure.external.supabase.client.supabase_client._admin_client', mock_supabase)

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

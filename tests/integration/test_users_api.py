"""
Tests de integración para endpoints de usuarios
"""

import pytest
from httpx import AsyncClient

from app.domain.entities.supabase_user import UserRole


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, sample_user_data):
    """Test de obtener usuario actual"""
    # Registrar y login
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    auth_data = login_response.json()

    # Obtener usuario actual
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient):
    """Test de listar usuarios como admin"""
    # Crear usuario admin
    admin_data = {
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
    }
    await client.post("/api/v1/auth/register", json=admin_data)

    # Login como admin
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_data["email"], "password": admin_data["password"]},
    )
    auth_data = login_response.json()

    # Listar usuarios
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    response = await client.get("/api/v1/users", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)


@pytest.mark.asyncio
async def test_list_users_as_regular_user(client: AsyncClient, sample_user_data):
    """Test de listar usuarios como usuario regular (debe fallar)"""
    # Registrar usuario regular
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    auth_data = login_response.json()

    # Intentar listar usuarios (debe fallar)
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    response = await client.get("/api/v1/users", headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_as_admin(client: AsyncClient):
    """Test de actualizar usuario como admin"""
    # Crear usuario regular
    user_data = {
        "email": "user@example.com",
        "password": "UserPass123!",
        "full_name": "Regular User",
    }
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    user_id = user_response.json()["user"]["id"]

    # Crear admin
    admin_data = {
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
    }
    await client.post("/api/v1/auth/register", json=admin_data)

    # Login como admin
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_data["email"], "password": admin_data["password"]},
    )
    auth_data = login_response.json()

    # Actualizar usuario
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    update_data = {"full_name": "Updated Name"}
    response = await client.patch(
        f"/api/v1/users/{user_id}", json=update_data, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"

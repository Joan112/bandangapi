"""
Tests de integración para endpoints de autenticación
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, sample_user_data):
    """Test de registro de usuario"""
    response = await client.post("/api/v1/auth/register", json=sample_user_data)

    assert response.status_code == 201
    data = response.json()
    # AuthResponse tiene estructura: {user: {...}, access_token, refresh_token, token_type}
    assert "user" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == sample_user_data["email"]
    assert data["user"]["full_name"] == sample_user_data["full_name"]
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, sample_user_data):
    """Test de registro con email duplicado"""
    # Registrar usuario por primera vez
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Intentar registrar con mismo email
    response = await client.post("/api/v1/auth/register", json=sample_user_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, sample_user_data):
    """Test de login exitoso"""
    # Registrar usuario
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Login
    login_data = {
        "email": sample_user_data["email"],
        "password": sample_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, sample_user_data):
    """Test de login con credenciales inválidas"""
    # Registrar usuario
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Login con password incorrecto
    login_data = {
        "email": sample_user_data["email"],
        "password": "WrongPassword123",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, sample_user_data):
    """Test de refresh token"""
    # Registrar y login
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    tokens = login_response.json()

    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, sample_user_data):
    """Test de logout"""
    # Registrar y login
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    tokens = login_response.json()

    # Logout
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = await client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data

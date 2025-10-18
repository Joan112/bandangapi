"""
Tests unitarios para seguridad
"""

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)


def test_password_hashing():
    """Test de hashing de passwords"""
    password = "TestPassword123"
    hashed = get_password_hash(password)

    # El hash no debe ser igual al password
    assert hashed != password

    # Debe verificar correctamente
    assert verify_password(password, hashed) is True

    # Password incorrecto no debe verificar
    assert verify_password("WrongPassword", hashed) is False


def test_password_strength_validation():
    """Test de validación de fortaleza de password"""
    # Password válido
    is_valid, message = validate_password_strength("ValidPass123")
    assert is_valid is True
    assert message == ""

    # Password muy corto
    is_valid, message = validate_password_strength("Short1")
    assert is_valid is False
    assert "caracteres" in message.lower()

    # Sin mayúsculas
    is_valid, message = validate_password_strength("lowercase123")
    assert is_valid is False
    assert "mayúscula" in message.lower()

    # Sin minúsculas
    is_valid, message = validate_password_strength("UPPERCASE123")
    assert is_valid is False
    assert "minúscula" in message.lower()

    # Sin números
    is_valid, message = validate_password_strength("NoNumbers")
    assert is_valid is False
    assert "número" in message.lower()


def test_jwt_token_creation_and_decoding():
    """Test de creación y decodificación de JWT"""
    user_id = 123

    # Crear access token
    token = create_access_token(str(user_id))
    assert token is not None
    assert isinstance(token, str)

    # Decodificar token
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_invalid_token():
    """Test de token inválido"""
    from fastapi import HTTPException

    invalid_token = "invalid.token.here"

    with pytest.raises(HTTPException) as exc_info:
        decode_token(invalid_token)

    assert exc_info.value.status_code == 401

"""
Utilidades de seguridad: JWT, password hashing, tokens
"""

from datetime import datetime, timedelta
from typing import Any, Literal, cast

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar password plano contra hash bcrypt

    Args:
        plain_password: Password en texto plano
        hashed_password: Hash bcrypt del password

    Returns:
        True si coinciden, False si no
    """
    # Truncar a 72 bytes antes de verificar (límite de bcrypt)
    password_bytes = plain_password.encode("utf-8")[:72]
    hash_bytes = (
        hashed_password.encode("utf-8")
        if isinstance(hashed_password, str)
        else hashed_password
    )
    return bcrypt.checkpw(password_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """
    Hashear password con bcrypt

    Args:
        password: Password en texto plano

    Returns:
        Hash bcrypt del password como string

    Note:
        bcrypt tiene un límite de 72 bytes. Si el password es más largo,
        se trunca automáticamente para evitar errores.
    """
    # Truncar a 72 bytes si es necesario (límite de bcrypt)
    password_bytes = password.encode("utf-8")[:72]
    # Generar salt y hashear (cost factor 12)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_token(
    subject: str | Any,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Crear JWT token (access o refresh)

    Args:
        subject: Subject del token (user_id normalmente)
        token_type: Tipo de token ("access" o "refresh")
        expires_delta: Tiempo de expiración custom

    Returns:
        Token JWT codificado
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        if token_type == "access":
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        else:  # refresh
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return cast(str, encoded_jwt)


def create_access_token(subject: str | Any) -> str:
    """Crear access token JWT"""
    return create_token(subject, "access")


def create_refresh_token(subject: str | Any) -> str:
    """Crear refresh token JWT"""
    return create_token(subject, "refresh")


def decode_token(
    token: str, expected_type: Literal["access", "refresh"] | None = None
) -> dict[str, Any]:
    """
    Decodificar y validar JWT token

    Args:
        token: Token JWT a decodificar
        expected_type: Tipo de token esperado (opcional)

    Returns:
        Payload del token

    Raises:
        HTTPException: Si el token es inválido o expirado
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Validar tipo de token si se especifica
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token tipo {expected_type} esperado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return cast(dict[str, Any], payload)

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validar fortaleza del password

    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)

    Args:
        password: Password a validar

    Returns:
        Tuple (es_válido, mensaje_error)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return (
            False,
            f"Password debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres",
        )

    if not any(c.isupper() for c in password):
        return False, "Password debe contener al menos una mayúscula"

    if not any(c.islower() for c in password):
        return False, "Password debe contener al menos una minúscula"

    if not any(c.isdigit() for c in password):
        return False, "Password debe contener al menos un número"

    # Validar carácter especial
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return (
            False,
            "Password debe contener al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)",
        )

    return True, ""

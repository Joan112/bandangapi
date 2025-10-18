"""
Utilidades de seguridad: JWT, password hashing, tokens
"""

from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Context para hashing de passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar password plano contra hash

    Args:
        plain_password: Password en texto plano
        hashed_password: Hash bcrypt del password

    Returns:
        True si coinciden, False si no
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashear password con bcrypt

    Args:
        password: Password en texto plano

    Returns:
        Hash bcrypt del password
    """
    return pwd_context.hash(password)


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

    return encoded_jwt


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

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validar fortaleza del password

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

    return True, ""

"""
Esquemas Pydantic para autenticación
"""
from typing import Optional

from pydantic import EmailStr, Field

from app.presentation.api.v1.schemas.base import TrimmedModel


class LoginRequest(TrimmedModel):
    """Esquema para login de usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña del usuario")


class TokenResponse(TrimmedModel):
    """Esquema de respuesta con tokens"""
    access_token: str = Field(..., description="Access token JWT")
    refresh_token: str = Field(..., description="Refresh token JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")


class RefreshTokenRequest(TrimmedModel):
    """Esquema para refrescar token"""
    refresh_token: str = Field(..., description="Refresh token JWT")


class MessageResponse(TrimmedModel):
    """Esquema para respuestas con mensaje"""
    message: str = Field(..., description="Mensaje de respuesta")

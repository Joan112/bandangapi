"""
Esquemas Pydantic para autenticación con Supabase
"""

from uuid import UUID

from pydantic import EmailStr, Field

from app.domain.entities.supabase_user import UserRole
from app.presentation.api.v1.schemas.base import TrimmedModel


class RegisterRequest(TrimmedModel):
    """Esquema para registro de usuario"""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    full_name: str | None = Field(None, description="Nombre completo del usuario")


class UserResponse(TrimmedModel):
    """Esquema de respuesta de usuario"""

    id: UUID = Field(..., description="ID del usuario")
    email: str = Field(..., description="Email del usuario")
    full_name: str | None = Field(None, description="Nombre completo del usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    is_active: bool = Field(..., description="Estado del usuario")

    class Config:
        """Configuración del modelo"""

        from_attributes = True
        use_enum_values = True


class AuthResponse(TrimmedModel):
    """Esquema de respuesta de autenticación"""

    user: UserResponse = Field(..., description="Datos del usuario")
    access_token: str = Field(..., description="Access token JWT")
    refresh_token: str = Field(..., description="Refresh token JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")

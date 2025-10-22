"""
Esquemas Pydantic para autenticación con Supabase
"""

from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.core.security import validate_password_strength
from app.domain.entities.supabase_user import UserRole
from app.presentation.api.v1.schemas.base import TrimmedModel


class RegisterRequest(TrimmedModel):
    """Esquema para registro de usuario"""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    full_name: str | None = Field(None, description="Nombre completo del usuario")
    role: UserRole | None = Field(
        None, description="Rol del usuario (solo para testing)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validar fortaleza del password"""
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


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


class UserUpdate(TrimmedModel):
    """Esquema para actualizar usuario (todos los campos opcionales)"""

    email: EmailStr | None = Field(None, description="Email del usuario")
    full_name: str | None = Field(None, description="Nombre completo del usuario")
    password: str | None = Field(
        None, min_length=8, description="Nueva contraseña del usuario"
    )
    role: UserRole | None = Field(None, description="Rol del usuario")
    is_active: bool | None = Field(None, description="Estado del usuario")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Validar fortaleza del password si se proporciona"""
        if v is None:
            return v
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class AuthResponse(TrimmedModel):
    """Esquema de respuesta de autenticación"""

    user: UserResponse = Field(..., description="Datos del usuario")
    access_token: str = Field(..., description="Access token JWT de Supabase")
    refresh_token: str = Field(..., description="Refresh token JWT de Supabase")
    token_type: str = Field(default="bearer", description="Tipo de token")
    message: str | None = Field(
        None, description="Mensaje adicional (ej: confirmación de email requerida)"
    )

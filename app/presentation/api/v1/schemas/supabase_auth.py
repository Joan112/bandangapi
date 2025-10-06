"""
Esquemas Pydantic para autenticación con Supabase
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.domain.entities.supabase_user import UserRole


class RegisterRequest(BaseModel):
    """Esquema para registro de usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    full_name: Optional[str] = Field(None, description="Nombre completo del usuario")


class UserResponse(BaseModel):
    """Esquema de respuesta de usuario"""
    id: UUID = Field(..., description="ID del usuario")
    email: str = Field(..., description="Email del usuario")
    full_name: Optional[str] = Field(None, description="Nombre completo del usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    is_active: bool = Field(..., description="Estado del usuario")
    
    class Config:
        """Configuración del modelo"""
        from_attributes = True
        use_enum_values = True


class AuthResponse(BaseModel):
    """Esquema de respuesta de autenticación"""
    user: UserResponse = Field(..., description="Datos del usuario")
    access_token: str = Field(..., description="Access token JWT")
    refresh_token: str = Field(..., description="Refresh token JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
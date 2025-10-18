"""
Entidad de dominio: Usuario para Supabase
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    """Roles de usuario"""

    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


@dataclass
class SupabaseUser:
    """
    Entidad SupabaseUser del dominio
    Representa un usuario en el sistema usando Supabase Auth
    """

    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Campos opcionales que pueden venir de Supabase Auth
    email_confirmed_at: datetime | None = None
    last_sign_in_at: datetime | None = None
    phone: str | None = None

    def has_role(self, required_role: UserRole) -> bool:
        """
        Verificar si el usuario tiene un rol específico o superior

        Args:
            required_role: Rol requerido

        Returns:
            True si tiene el rol o superior
        """
        role_hierarchy = {
            UserRole.USER: 0,
            UserRole.ADMIN: 1,
            UserRole.SUPERADMIN: 2,
        }
        return role_hierarchy[self.role] >= role_hierarchy[required_role]

    def can_modify_user(self, target_user: "SupabaseUser") -> bool:
        """
        Verificar si puede modificar otro usuario

        Args:
            target_user: Usuario objetivo

        Returns:
            True si puede modificar
        """
        # Superadmin puede modificar a cualquiera
        if self.role == UserRole.SUPERADMIN:
            return True

        # Admin puede modificar a usuarios normales
        if self.role == UserRole.ADMIN and target_user.role == UserRole.USER:
            return True

        # Usuarios pueden modificarse a sí mismos
        if self.id == target_user.id:
            return True

        return False

    @classmethod
    def from_dict(cls, data: dict) -> "SupabaseUser":
        """
        Crear una instancia de SupabaseUser desde un diccionario

        Args:
            data: Diccionario con datos del usuario

        Returns:
            Instancia de SupabaseUser
        """
        # Convertir role a enum si viene como string
        if "role" in data and isinstance(data["role"], str):
            data["role"] = UserRole(data["role"])

        # Convertir fechas a datetime si es necesario
        for field in [
            "created_at",
            "updated_at",
            "email_confirmed_at",
            "last_sign_in_at",
        ]:
            if field in data and data[field] and not isinstance(data[field], datetime):
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(
                        data[field].replace("Z", "+00:00")
                    )

        # Convertir id a UUID si es necesario
        if "id" in data and not isinstance(data["id"], UUID):
            data["id"] = UUID(data["id"])

        return cls(**data)

    def to_dict(self) -> dict:
        """
        Convertir la entidad a un diccionario

        Returns:
            Diccionario con los datos del usuario
        """
        result = {
            "id": str(self.id),
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        # Agregar campos opcionales si tienen valor
        if self.full_name:
            result["full_name"] = self.full_name

        if self.email_confirmed_at:
            result["email_confirmed_at"] = self.email_confirmed_at.isoformat()

        if self.last_sign_in_at:
            result["last_sign_in_at"] = self.last_sign_in_at.isoformat()

        if self.phone:
            result["phone"] = self.phone

        return result

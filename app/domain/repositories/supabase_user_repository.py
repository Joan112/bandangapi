"""
Interfaz para el repositorio de usuarios con Supabase
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities.supabase_user import SupabaseUser, UserRole


class SupabaseUserRepository(ABC):
    """
    Interfaz para el repositorio de usuarios con Supabase
    Define los métodos que debe implementar cualquier repositorio de usuarios
    """
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[SupabaseUser]:
        """
        Obtener un usuario por su ID
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Usuario encontrado o None
        """
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[SupabaseUser]:
        """
        Obtener un usuario por su email
        
        Args:
            email: Email del usuario
            
        Returns:
            Usuario encontrado o None
        """
        pass
    
    @abstractmethod
    async def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        role: Optional[UserRole] = None
    ) -> List[SupabaseUser]:
        """
        Listar usuarios con paginación y filtros opcionales
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            role: Filtrar por rol
            
        Returns:
            Lista de usuarios
        """
        pass
    
    @abstractmethod
    async def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER
    ) -> SupabaseUser:
        """
        Crear un nuevo usuario
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            full_name: Nombre completo (opcional)
            role: Rol del usuario
            
        Returns:
            Usuario creado
        """
        pass
    
    @abstractmethod
    async def update_user(
        self, 
        user_id: UUID, 
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> SupabaseUser:
        """
        Actualizar un usuario existente
        
        Args:
            user_id: ID del usuario
            full_name: Nuevo nombre completo (opcional)
            role: Nuevo rol (opcional)
            is_active: Nuevo estado (opcional)
            
        Returns:
            Usuario actualizado
        """
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: UUID) -> bool:
        """
        Eliminar un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si se eliminó correctamente
        """
        pass
    
    @abstractmethod
    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Cambiar la contraseña de un usuario
        
        Args:
            user_id: ID del usuario
            new_password: Nueva contraseña
            
        Returns:
            True si se cambió correctamente
        """
        pass
    
    @abstractmethod
    async def authenticate(self, email: str, password: str) -> Optional[SupabaseUser]:
        """
        Autenticar un usuario con email y contraseña
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            Usuario autenticado o None
        """
        pass
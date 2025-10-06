"""
Caso de uso para registrar un usuario con Supabase
"""
from typing import Optional, Protocol

from app.core.exceptions import DuplicateEntityError, ValidationError
from app.domain.entities.supabase_user import SupabaseUser, UserRole


class SupabaseUserRepository(Protocol):
    """Interfaz del repositorio de usuarios con Supabase"""
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER
    ) -> SupabaseUser:
        """Crear un nuevo usuario"""
        ...


class RegisterUserSupabaseUseCase:
    """
    Caso de uso para registrar un usuario con Supabase
    """
    
    def __init__(self, user_repository: SupabaseUserRepository):
        """
        Inicializar caso de uso
        
        Args:
            user_repository: Repositorio de usuarios
        """
        self._repository = user_repository
    
    async def execute(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> SupabaseUser:
        """
        Ejecutar caso de uso
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            full_name: Nombre completo (opcional)
            role: Rol del usuario
            
        Returns:
            Usuario creado
            
        Raises:
            ValidationError: Si los datos no son válidos
            DuplicateEntityError: Si ya existe un usuario con el mismo email
        """
        # Validar email
        if not email or "@" not in email:
            raise ValidationError("Email inválido")
            
        # Validar contraseña
        if not password or len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")
            
        try:
            # Crear usuario
            user = await self._repository.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=role
            )
            
            return user
        except DuplicateEntityError:
            raise
        except Exception as e:
            raise ValidationError(f"Error al registrar usuario: {e}")
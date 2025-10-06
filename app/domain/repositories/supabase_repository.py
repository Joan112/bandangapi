"""
Interfaces para repositorios basados en Supabase
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')  # Tipo genérico para entidades


class SupabaseRepository(Generic[T], ABC):
    """
    Interfaz base para repositorios que usan Supabase
    
    Esta clase define los métodos que deben implementar todos los
    repositorios que utilizan Supabase como fuente de datos.
    """
    
    @abstractmethod
    async def get_by_id(self, id_value: str | int) -> Optional[T]:
        """
        Obtener una entidad por su ID
        
        Args:
            id_value: ID de la entidad
            
        Returns:
            Entidad encontrada o None
        """
        pass
    
    @abstractmethod
    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """
        Obtener una entidad por un campo específico
        
        Args:
            field: Nombre del campo
            value: Valor a buscar
            
        Returns:
            Entidad encontrada o None
        """
        pass
    
    @abstractmethod
    async def list_all(
        self, 
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[T]:
        """
        Listar todas las entidades
        
        Args:
            order_by: Campo para ordenar
            limit: Límite de registros
            offset: Desplazamiento
            
        Returns:
            Lista de entidades
        """
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Crear una nueva entidad
        
        Args:
            data: Datos para crear la entidad
            
        Returns:
            Entidad creada
        """
        pass
    
    @abstractmethod
    async def update(self, id_value: str | int, data: Dict[str, Any]) -> T:
        """
        Actualizar una entidad existente
        
        Args:
            id_value: ID de la entidad
            data: Datos a actualizar
            
        Returns:
            Entidad actualizada
        """
        pass
    
    @abstractmethod
    async def delete(self, id_value: str | int) -> bool:
        """
        Eliminar una entidad
        
        Args:
            id_value: ID de la entidad
            
        Returns:
            True si se eliminó correctamente
        """
        pass
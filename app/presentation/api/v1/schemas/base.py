"""
Módulo base para esquemas Pydantic con funcionalidades personalizadas.
"""
from pydantic import BaseModel, field_validator
from typing import Any

class TrimmedModel(BaseModel):
    """
    Un BaseModel personalizado que recorta automáticamente los espacios en blanco
    de todos los campos de tipo string.
    """
    @field_validator('*', check_fields=False)
    def trim_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v
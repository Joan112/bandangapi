"""
Excepciones personalizadas
"""


class BandangWebException(Exception):
    """Base exception para la aplicación"""

    pass


class EntityNotFoundError(BandangWebException):
    """Entidad no encontrada"""

    def __init__(self, entity: str, entity_id: str | int) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} con ID {entity_id} no encontrado")


class DuplicateEntityError(BandangWebException):
    """Entidad duplicada"""

    def __init__(self, entity: str, field: str, value: str) -> None:
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity} con {field}='{value}' ya existe")


class InvalidCredentialsError(BandangWebException):
    """Credenciales inválidas"""

    def __init__(self, message: str = "Email o password incorrectos") -> None:
        super().__init__(message)


class InsufficientPermissionsError(BandangWebException):
    """Permisos insuficientes"""

    def __init__(self, required_role: str) -> None:
        self.required_role = required_role
        super().__init__(f"Se requiere rol '{required_role}' para esta acción")


class InvalidTokenError(BandangWebException):
    """Token inválido"""

    def __init__(self, message: str = "Token inválido o expirado") -> None:
        super().__init__(message)


class ValidationError(BandangWebException):
    """Error de validación"""

    def __init__(self, message: str) -> None:
        super().__init__(message)

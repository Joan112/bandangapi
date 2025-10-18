---
name: bandang-api-generator
description: Generar endpoints FastAPI con Pydantic schemas, validaciones, RBAC y dependency injection para BandangWeb API.
model: sonnet
color: green
---

# Bandang API Generator

**Description:** Agente especializado en crear o modificar endpoints FastAPI rápidamente para BandangWeb API.

**Tools:** Read, Write, Edit, Bash, Glob, Grep

**Model:** Sonnet

---

## Especialización

Generar endpoints REST API completos siguiendo las convenciones del proyecto:
- FastAPI routers con async/await
- Pydantic V2 schemas para validación
- Dependency injection
- Documentación OpenAPI automática
- Manejo de errores consistente

## Cuándo Usar Este Agente

- Agregar nuevos endpoints a features existentes
- Modificar endpoints existentes
- Crear operaciones CRUD rápidas
- Agregar validaciones y middlewares a endpoints
- Configurar permisos y RBAC en rutas

## Estructura de Endpoints

### Ubicaciones
- **Routers**: `app/presentation/api/v1/endpoints/`
- **Schemas**: `app/presentation/api/v1/schemas/`
- **Router principal**: `app/presentation/api/router.py`

### Patrón de Archivo de Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from app.presentation.api.v1.schemas.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse
)
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import EntityNotFoundError, ValidationError

router = APIRouter()

# Dependency para obtener repositorio/servicio
def get_entity_service():
    # Inicializar servicio o repositorio
    pass

@router.get(
    "/",
    response_model=List[EntityResponse],
    summary="Listar entidades",
    description="Obtiene lista paginada de entidades con filtros opcionales"
)
async def list_entities(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de registros"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre"),
    current_user = Depends(get_current_user),
    service = Depends(get_entity_service)
):
    """
    Listar entidades con paginación.

    - **skip**: Número de registros a omitir (paginación)
    - **limit**: Número máximo de registros a retornar
    - **search**: Filtro opcional por nombre
    """
    return await service.list_all(skip=skip, limit=limit, search=search)

@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Obtener entidad por ID"
)
async def get_entity(
    entity_id: UUID,
    current_user = Depends(get_current_user),
    service = Depends(get_entity_service)
):
    """Obtener una entidad específica por su ID"""
    entity = await service.get_by_id(entity_id)
    if not entity:
        raise EntityNotFoundError(entity="Entity", id=str(entity_id))
    return entity

@router.post(
    "/",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva entidad"
)
async def create_entity(
    entity_data: EntityCreate,
    current_user = Depends(require_role("USER")),
    service = Depends(get_entity_service)
):
    """
    Crear una nueva entidad.

    Requiere autenticación de usuario.
    """
    return await service.create(entity_data.model_dump(), user_id=current_user.id)

@router.put(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Actualizar entidad"
)
async def update_entity(
    entity_id: UUID,
    entity_data: EntityUpdate,
    current_user = Depends(require_role("ADMIN")),
    service = Depends(get_entity_service)
):
    """
    Actualizar entidad existente.

    Requiere rol ADMIN.
    """
    return await service.update(
        entity_id,
        entity_data.model_dump(exclude_unset=True)
    )

@router.patch(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Actualización parcial"
)
async def partial_update_entity(
    entity_id: UUID,
    entity_data: EntityUpdate,
    current_user = Depends(get_current_user),
    service = Depends(get_entity_service)
):
    """Actualización parcial de una entidad"""
    return await service.update(
        entity_id,
        entity_data.model_dump(exclude_unset=True)
    )

@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar entidad"
)
async def delete_entity(
    entity_id: UUID,
    current_user = Depends(require_role("ADMIN")),
    service = Depends(get_entity_service)
):
    """
    Eliminar entidad.

    Requiere rol ADMIN. Operación irreversible.
    """
    await service.delete(entity_id)
```

## Schemas Pydantic

### Patrón de Schemas

```python
from pydantic import BaseModel, Field, ConfigDict, EmailStr, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum

# Enums si se necesitan
class EntityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

# Schema base con campos comunes
class EntityBase(BaseModel):
    """Schema base con campos comunes"""
    name: str = Field(..., min_length=1, max_length=200, description="Nombre de la entidad")
    description: Optional[str] = Field(None, max_length=1000)
    status: EntityStatus = Field(default=EntityStatus.ACTIVE)

# Schema para creación (sin id, sin timestamps)
class EntityCreate(EntityBase):
    """Schema para crear una nueva entidad"""
    email: EmailStr = Field(..., description="Email de contacto")
    tags: List[str] = Field(default_factory=list, max_items=10)

# Schema para actualización (todo opcional)
class EntityUpdate(BaseModel):
    """Schema para actualizar entidad (todos los campos opcionales)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[EntityStatus] = None
    email: Optional[EmailStr] = None
    tags: Optional[List[str]] = Field(None, max_items=10)

# Schema de respuesta (con id, timestamps, relaciones)
class EntityResponse(EntityBase):
    """Schema de respuesta con todos los campos"""
    id: UUID
    email: EmailStr
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Ejemplo",
                "description": "Descripción de ejemplo",
                "status": "active",
                "email": "ejemplo@example.com",
                "tags": ["tag1", "tag2"],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }
    )

# Schema para listas con metadatos
class EntityListResponse(BaseModel):
    """Schema para respuestas de listado con paginación"""
    total: int = Field(..., description="Total de registros")
    items: List[EntityResponse] = Field(..., description="Lista de entidades")
    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
```

## Validaciones Comunes con Pydantic

```python
from pydantic import BaseModel, Field, field_validator, model_validator
import re

class EntityCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    website: Optional[HttpUrl] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Solo alfanuméricos y guiones"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username debe contener solo letras, números, guiones y underscore')
        return v.lower()

    @model_validator(mode='after')
    def validate_model(self):
        """Validaciones que involucran múltiples campos"""
        if self.age < 18 and self.website:
            raise ValueError('Menores de 18 no pueden tener website público')
        return self
```

## Dependency Injection Patterns

### Repositorio/Servicio como Dependency

```python
from typing import Annotated
from fastapi import Depends

def get_entity_repository():
    from app.infrastructure.database.repositories.entity_repository_impl import EntityRepositoryImpl
    return EntityRepositoryImpl()

# Usar Annotated para dependencies reutilizables
EntityRepository = Annotated[EntityRepositoryImpl, Depends(get_entity_repository)]

@router.get("/")
async def list_entities(repository: EntityRepository):
    return await repository.list_all()
```

### Usuario Actual con Roles

```python
from app.core.dependencies import get_current_user, require_role
from app.domain.entities.supabase_user import SupabaseUser

# Usuario autenticado (cualquier rol)
@router.get("/profile")
async def get_profile(current_user: SupabaseUser = Depends(get_current_user)):
    return current_user

# Solo ADMIN
@router.delete("/{id}")
async def delete_item(
    id: UUID,
    current_user: SupabaseUser = Depends(require_role("ADMIN"))
):
    pass

# Solo ADMIN o SUPERADMIN
async def require_admin_or_super():
    user = await get_current_user()
    if user.role not in ["ADMIN", "SUPERADMIN"]:
        from app.core.exceptions import InsufficientPermissionsError
        raise InsufficientPermissionsError(required_role="ADMIN")
    return user

@router.put("/{id}")
async def update_item(current_user = Depends(require_admin_or_super)):
    pass
```

## Manejo de Errores

### Usar Excepciones Custom

```python
from app.core.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    ValidationError,
    InsufficientPermissionsError
)

@router.get("/{entity_id}")
async def get_entity(entity_id: UUID, service = Depends(get_service)):
    entity = await service.get_by_id(entity_id)
    if not entity:
        raise EntityNotFoundError(entity="Entity", id=str(entity_id))
    return entity

@router.post("/")
async def create_entity(data: EntityCreate, service = Depends(get_service)):
    existing = await service.get_by_email(data.email)
    if existing:
        raise DuplicateEntityError(
            entity="Entity",
            field="email",
            value=data.email
        )
    return await service.create(data.model_dump())
```

### Excepciones HTTP Directas (cuando sea necesario)

```python
from fastapi import HTTPException, status

@router.get("/external/{external_id}")
async def get_from_external(external_id: str):
    try:
        data = await external_api.fetch(external_id)
    except ExternalAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error from external API: {str(e)}"
        )
    return data
```

## Query Parameters y Paginación

```python
from fastapi import Query
from typing import Optional

@router.get("/")
async def list_entities(
    # Paginación
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de registros"),

    # Filtros
    search: Optional[str] = Query(None, max_length=100, description="Búsqueda por nombre"),
    status: Optional[str] = Query(None, regex="^(active|inactive|pending)$"),

    # Ordenamiento
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|name)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),

    service = Depends(get_service)
):
    return await service.list_all(
        skip=skip,
        limit=limit,
        search=search,
        status=status,
        sort_by=sort_by,
        order=order
    )
```

## File Upload (si es necesario)

```python
from fastapi import File, UploadFile
from typing import List

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="Archivo a subir"),
    current_user = Depends(get_current_user)
):
    """Upload de archivo individual"""
    # Validar tipo de archivo
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise ValidationError("Solo se permiten imágenes JPEG, PNG o WebP")

    # Validar tamaño (5MB max)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise ValidationError("El archivo no debe superar 5MB")

    # Procesar upload (ej: subir a Supabase Storage)
    # ...

    return {"filename": file.filename, "size": len(contents)}

@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="Múltiples archivos"),
    current_user = Depends(get_current_user)
):
    """Upload de múltiples archivos"""
    if len(files) > 10:
        raise ValidationError("Máximo 10 archivos por request")

    results = []
    for file in files:
        # Procesar cada archivo
        contents = await file.read()
        results.append({
            "filename": file.filename,
            "size": len(contents),
            "content_type": file.content_type
        })

    return {"uploaded": len(results), "files": results}
```

## Registrar Router en Main

Agregar en `app/presentation/api/router.py`:

```python
from app.presentation.api.v1.endpoints import new_endpoint

api_router.include_router(
    new_endpoint.router,
    prefix="/new-endpoint",
    tags=["New Endpoint"]
)
```

## Documentación OpenAPI

### Tags y Metadata

En el archivo de endpoint:
```python
router = APIRouter(
    tags=["Entities"],
    responses={
        404: {"description": "Entity not found"},
        400: {"description": "Bad request"}
    }
)
```

### Ejemplos en Schemas

```python
class EntityCreate(BaseModel):
    name: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Ejemplo 1",
                    "description": "Primera descripción"
                },
                {
                    "name": "Ejemplo 2",
                    "description": "Segunda descripción"
                }
            ]
        }
    )
```

## Rate Limiting (si es necesario)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/send-email")
@limiter.limit("5/minute")  # 5 requests por minuto
async def send_email(request: Request, data: EmailData):
    # Enviar email
    pass
```

## Checklist para Nuevos Endpoints

- [ ] Router creado con `APIRouter()`
- [ ] Schemas Pydantic definidos (Create, Update, Response)
- [ ] Validaciones con Field() y validators
- [ ] Dependency injection para servicios/repos
- [ ] RBAC configurado con `require_role()` donde sea necesario
- [ ] Manejo de errores con excepciones custom
- [ ] Docstrings en cada endpoint
- [ ] Query parameters con validación
- [ ] Response models definidos
- [ ] HTTP status codes correctos
- [ ] Router registrado en `app/presentation/api/router.py`
- [ ] Ejemplos en schemas para documentación

## Output Esperado

Cuando el usuario pida crear endpoints, este agente debe:
1. Crear el archivo de router en `app/presentation/api/v1/endpoints/`
2. Crear schemas en `app/presentation/api/v1/schemas/`
3. Configurar dependency injection
4. Agregar validaciones Pydantic
5. Implementar RBAC según los requisitos
6. Registrar el router en el router principal
7. Generar documentación inline clara

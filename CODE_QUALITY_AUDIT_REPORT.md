# Reporte de Auditoría de Calidad de Código - BandangAPI

**Fecha:** 2025-10-21
**Proyecto:** BandangWeb API v1.0.0
**Auditor:** Bandang Code Quality Agent
**Python:** 3.11+
**Framework:** FastAPI 0.110+

---

## Resumen Ejecutivo

### Score General: **68/100** ⚠️

| Categoría | Score | Estado |
|-----------|-------|--------|
| **Formateo (Black)** | 92/100 | ✅ Bueno |
| **Linting (Ruff)** | 95/100 | ✅ Excelente |
| **Type Safety (mypy)** | 45/100 | ❌ Crítico |
| **Docstrings** | 75/100 | ⚠️ Aceptable |
| **SOLID Principles** | 70/100 | ⚠️ Aceptable |
| **Code Smells** | 60/100 | ⚠️ Requiere Atención |

### Hallazgos Clave

- ✅ **Fortalezas:**
  - Arquitectura Clean bien estructurada
  - Buena separación de responsabilidades (domain/infrastructure/presentation)
  - Uso consistente de Pydantic para validación
  - Documentación en docstrings presente en la mayoría de funciones

- ❌ **Debilidades Críticas:**
  - **Type safety incompleta**: 28 errores de mypy en modo strict
  - **Uso de print() en producción**: Detectado en repositorios
  - **Funciones sin type hints**: Varios endpoints y dependencies sin anotaciones completas
  - **Código formateado inconsistente**: 5 archivos requieren reformateo con Black

---

## 1. Análisis de Formateo (Black)

### Estado: ✅ **92/100 - Bueno**

**Resultado:**
```
5 files would be reformatted, 56 files would be left unchanged
```

**Archivos que requieren reformateo:**

1. `app/core/security.py`
2. `app/presentation/api/v1/endpoints/supabase_auth.py`
3. `app/presentation/api/v1/schemas/multimedia.py`
4. `app/infrastructure/external/supabase/storage_service.py`
5. `app/infrastructure/database/repositories/supabase_user_repository_impl.py`

**Configuración Black (pyproject.toml):**
```toml
[tool.black]
line-length = 88
target-version = ['py311']
```

### ⚠️ Problema: Discrepancia en Documentación

**CRÍTICO:** La documentación en `CLAUDE.md` menciona `line-length = 100`, pero `pyproject.toml` tiene configurado `line-length = 88`.

**Recomendación:**
```bash
# Aplicar formateo automático
poetry run black app/ tests/
```

---

## 2. Análisis de Linting (Ruff)

### Estado: ✅ **95/100 - Excelente**

**Resultado:**
```
Found 7 errors.
[*] 5 fixable with the --fix option
```

**Errores Detectados:**

### F401: Imports no utilizados (5 errores) ✅ Auto-fixable

```python
# app/infrastructure/external/supabase/storage_service.py
F401: `pathlib.Path` imported but unused (línea 7)
F401: `uuid.UUID` imported but unused (línea 9)
F401: `app.core.config.settings` imported but unused (línea 13)

# app/presentation/api/v1/endpoints/events.py
F401: `app.core.dependencies.require_role` imported but unused (línea 7)
F401: `app.domain.entities.supabase_user.SupabaseUser` imported but unused (línea 9)
```

**Impacto:** Bajo - Solo imports no utilizados
**Fix automático:**
```bash
poetry run ruff check --fix app/
```

### F841: Variables asignadas pero no utilizadas (2 errores)

```python
# app/infrastructure/external/supabase/storage_service.py:188
upload_response = ...  # Nunca se usa

# app/presentation/api/v1/endpoints/supabase_auth.py:231
token = authorization.replace("Bearer ", "")  # Nunca se usa
```

**Recomendación:**
```python
# Opción 1: Usar la variable
logger.debug(f"Upload response: {upload_response}")

# Opción 2: Usar _ para variables intencionales descartables
_ = authorization.replace("Bearer ", "")

# Opción 3: Eliminar la asignación si no se necesita
```

---

## 3. Análisis de Type Safety (mypy)

### Estado: ❌ **45/100 - CRÍTICO**

**Resultado:**
```
28 errores de type checking en modo strict
```

### 3.1 Errores Críticos de Type Hints (Alta Prioridad)

#### Missing Type Parameters for Generic Types (4 errores)

```python
# app/domain/entities/supabase_user.py:81, 114
def from_dict(cls, data: dict) -> "SupabaseUser":  # ❌ dict sin types
    ...

# ✅ FIX:
def from_dict(cls, data: dict[str, Any]) -> "SupabaseUser":
    ...
```

```python
# app/domain/repositories/multimedia_repository.py:18, 70
async def create(self, multimedia_data: dict) -> Multimedia:  # ❌

# ✅ FIX:
async def create(self, multimedia_data: dict[str, Any]) -> Multimedia:
```

#### Functions Missing Type Annotations (7 errores)

```python
# app/core/dependencies.py:72, 109, 120, 144, 165
async def get_current_user(user_id: Annotated[str, Depends(get_current_user_id)]):  # ❌
    ...

# ✅ FIX:
async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> SupabaseUser:
    ...
```

```python
# app/core/dependencies.py:109
def require_role(required_role: str):  # ❌ Sin return type
    async def role_dependency(current_user=Depends(get_current_user)):  # ❌
        ...
    return role_dependency

# ✅ FIX:
from typing import Callable
from fastapi import Depends

def require_role(required_role: str) -> Callable[..., Awaitable[SupabaseUser]]:
    async def role_dependency(
        current_user: SupabaseUser = Depends(get_current_user)
    ) -> SupabaseUser:
        ...
    return role_dependency
```

```python
# app/presentation/middleware/security_headers.py:17
def __call__(self, request):  # ❌
    ...

# ✅ FIX:
from starlette.requests import Request
from starlette.responses import Response

def __call__(self, request: Request) -> Response:
    ...
```

### 3.2 Errores de no-any-return (6 errores)

```python
# app/core/security.py:93
def create_access_token(subject: str | Any) -> str:
    return create_token(subject, "access")  # ❌ Returns Any

# ✅ FIX: Asegurar que create_token retorna str explícitamente
encoded_jwt: str = jwt.encode(...)
return encoded_jwt
```

```python
# app/infrastructure/external/supabase/client.py:82, 104, 158, 180
async def get_by_id(...) -> dict[str, Any] | None:
    response = await client.table(table).select("*")...
    return response.data[0]  # ❌ Any

# ✅ FIX: Cast explícito
from typing import cast
return cast(dict[str, Any], response.data[0])
```

### 3.3 Errores de Incompatibilidad de Tipos (5 errores)

```python
# app/infrastructure/external/supabase/client.py:40, 50
from supabase import create_client, ClientOptions

client = create_client(url, key, options=ClientOptions(...))  # ❌
# Expected: AsyncClientOptions | None

# ✅ FIX: Usar el tipo correcto para async client
from supabase import AsyncClientOptions

options = AsyncClientOptions(...)
```

```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py:444
async def list_all(self, role: str | None = None) -> list[SupabaseUser]:
    return await self.list_users(skip=skip, limit=limit, role=role)  # ❌
    # Expected: UserRole | None, got: str | None

# ✅ FIX:
async def list_all(self, role: str | None = None) -> list[SupabaseUser]:
    user_role: UserRole | None = UserRole(role) if role else None
    return await self.list_users(skip=skip, limit=limit, role=user_role)
```

### 3.4 Errores de Pillow (2 errores)

```python
# app/infrastructure/external/supabase/storage_service.py:133, 135
img: ImageFile = Image.open(io.BytesIO(file_bytes))  # ❌
# Expression has type "Image", variable has type "ImageFile"

# ✅ FIX:
from PIL.Image import Image as PILImage

img: PILImage = Image.open(io.BytesIO(file_bytes))
```

---

## 4. Code Smells y Anti-Patterns

### 4.1 Uso de print() en Producción ❌ CRÍTICO

**Archivo:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py`

**Líneas detectadas:**
```python
# Línea 105
print(f"Error al obtener usuario por email: {e}")

# Línea 141
print(f"Error al listar usuarios: {e}")
```

**Problema:** `print()` en producción es inaceptable:
- No respeta niveles de logging (DEBUG, INFO, WARNING, ERROR)
- No se integra con sistemas de monitoreo
- Dificulta troubleshooting
- No puede deshabilitarse en producción

**Recomendación:**
```python
import logging

logger = logging.getLogger(__name__)

# ✅ FIX:
try:
    ...
except Exception as e:
    logger.error(f"Error al obtener usuario por email: {e}", exc_info=True)
    return None
```

**NOTA POSITIVA:** Líneas 77-80, 191-205, 254-260 ya usan `logging` correctamente. Solo faltan 2 ocurrencias.

### 4.2 Bloques try-except Excesivamente Amplios

**Archivo:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py`

```python
# Línea 158-271 (113 líneas en un solo try-except) ❌
async def create_user(...) -> SupabaseUser:
    try:
        # 113 líneas de lógica compleja
        ...
    except APIError as e:
        ...
    except Exception as e:
        raise ValueError(f"Error inesperado al crear usuario: {e}") from e
```

**Problema:**
- Dificulta identificar la fuente exacta del error
- Catch genérico de `Exception` oculta bugs
- Complejidad ciclomática alta

**Recomendación:**
```python
async def create_user(...) -> SupabaseUser:
    # Separar en funciones más pequeñas
    user_id = await self._register_user_in_auth(email, password, full_name)
    user = await self._get_or_create_profile(user_id, email, full_name, role)
    return user

async def _register_user_in_auth(...) -> UUID:
    try:
        signup_response = await client.auth.sign_up(...)
        if not signup_response.user:
            raise ValueError("No user in response")
        return UUID(signup_response.user.id)
    except APIError as e:
        if "user already registered" in str(e.message).lower():
            raise DuplicateEntityError("Usuario", "email", email) from e
        raise
```

### 4.3 Lógica de Negocio en Repositorios

**Archivo:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py`

```python
# Líneas 189-264: Lógica compleja de retry y creación de perfil manual ❌
if not user:
    await asyncio.sleep(1.5)  # Esperar un poco más por si hay retardo
    user = await self.get_by_id(user_id)

if not user:
    logger.warning(
        f"Perfil no encontrado para usuario {user_id}, creando manualmente..."
    )
    # 50+ líneas de lógica de compensación
```

**Problema:**
- Repositorio haciendo lógica de negocio (violación de Single Responsibility)
- `asyncio.sleep()` hardcoded es un code smell
- Esta lógica debería estar en un Use Case

**Recomendación:**
```python
# Domain Use Case: app/domain/use_cases/auth/create_user_with_retry.py
class CreateUserWithRetryUseCase:
    async def execute(...) -> SupabaseUser:
        user_id = await self.repo.register_in_auth(...)
        user = await self._wait_for_profile_creation(user_id)
        if not user:
            user = await self._manually_create_profile(user_id, ...)
        return user

    async def _wait_for_profile_creation(self, user_id: UUID) -> SupabaseUser | None:
        for attempt in range(3):
            user = await self.repo.get_by_id(user_id)
            if user:
                return user
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        return None
```

### 4.4 Magic Numbers y Strings

```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py:192
await asyncio.sleep(1.5)  # ❌ Magic number

# ✅ FIX:
PROFILE_CREATION_RETRY_DELAY_SECONDS = 1.5
await asyncio.sleep(PROFILE_CREATION_RETRY_DELAY_SECONDS)
```

```python
# app/core/security.py:178
special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"  # ❌ Magic string

# ✅ FIX:
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
```

### 4.5 Inicialización de Repositorios en Endpoints

**Archivo:** `app/presentation/api/v1/endpoints/multimedia.py`

```python
# Líneas 86-88 ❌
async def list_multimedia(...):
    from app.infrastructure.database.repositories.multimedia_repository_impl import (
        MultimediaRepositoryImpl,
    )
    repository = MultimediaRepositoryImpl()
```

**Problema:**
- Importación dentro de función (anti-pattern)
- Violación de Dependency Injection
- Dificulta testing

**Recomendación:**
```python
# ✅ FIX: Usar dependency injection consistente
def get_multimedia_repository() -> MultimediaRepositoryImpl:
    return MultimediaRepositoryImpl()

async def list_multimedia(
    ...,
    repository: MultimediaRepositoryImpl = Depends(get_multimedia_repository)
):
    items = await repository.list_all(...)
```

**Ocurrencias:** Se repite en líneas 86, 130, 174, 223 del mismo archivo.

---

## 5. Análisis de Docstrings

### Estado: ⚠️ **75/100 - Aceptable**

**Fortalezas:**
- ✅ La mayoría de funciones públicas tienen docstrings en formato Google-style
- ✅ Parámetros y returns documentados
- ✅ Excepciones documentadas con `Raises:`

**Debilidades:**

#### 5.1 Docstrings Incompletos

```python
# app/core/security.py:96-98
def create_access_token(subject: str | Any) -> str:
    """Crear access token JWT"""  # ❌ Muy breve
    return create_token(subject, "access")
```

**Recomendación:**
```python
def create_access_token(subject: str | Any) -> str:
    """
    Crear access token JWT con expiración configurable.

    Args:
        subject: Subject del token (típicamente user_id)

    Returns:
        Token JWT codificado como string

    Example:
        >>> token = create_access_token("user-uuid-123")
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    return create_token(subject, "access")
```

#### 5.2 Falta Documentación de Comportamiento Asíncrono

```python
# app/core/dependencies.py:72-106
async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """
    Obtener usuario actual completo desde Supabase  # ❌ Falta mencionar async I/O

    Args:
        user_id: ID del usuario (UUID as string)
    ...
```

**Recomendación:**
```python
async def get_current_user(...) -> SupabaseUser:
    """
    Obtener usuario actual completo desde Supabase.

    Esta función realiza una consulta asíncrona a la base de datos
    de Supabase para obtener el perfil completo del usuario.

    Args:
        user_id: ID del usuario (UUID as string)

    Returns:
        Usuario completo (SupabaseUser)

    Raises:
        HTTPException 404: Si el usuario no existe
        HTTPException 400: Si el usuario está inactivo

    Note:
        Requiere autenticación válida. El user_id se extrae
        del token JWT mediante get_current_user_id.
    """
```

---

## 6. Análisis SOLID Principles

### 6.1 Single Responsibility Principle: ⚠️ **70/100**

**Violaciones detectadas:**

#### `SupabaseUserRepositoryImpl` - Demasiadas Responsabilidades

**Líneas de código:** 468 líneas ❌

**Responsabilidades mezcladas:**
1. CRUD de usuarios
2. Autenticación
3. Gestión de perfiles
4. Retry logic para triggers de BD
5. Cambio de contraseñas
6. Sincronización auth.users ↔ profiles

**Recomendación:**
```python
# Separar en múltiples clases especializadas:

# 1. app/infrastructure/database/repositories/supabase_user_repository_impl.py
class SupabaseUserRepositoryImpl:
    """Solo CRUD básico de usuarios"""
    async def get_by_id(self, user_id: UUID) -> SupabaseUser | None: ...
    async def list_users(self, ...) -> list[SupabaseUser]: ...
    async def update_user(self, ...) -> SupabaseUser: ...
    async def delete_user(self, user_id: UUID) -> bool: ...

# 2. app/infrastructure/auth/supabase_auth_service.py
class SupabaseAuthService:
    """Autenticación y tokens"""
    async def authenticate(self, email: str, password: str) -> AuthResult: ...
    async def change_password(self, user_id: UUID, new_password: str) -> bool: ...

# 3. app/infrastructure/database/repositories/supabase_profile_repository.py
class SupabaseProfileRepository:
    """Gestión de perfiles con retry logic"""
    async def get_or_create_profile(self, user_id: UUID, ...) -> Profile: ...
    async def sync_profile_with_auth(self, user_id: UUID) -> None: ...
```

### 6.2 Dependency Inversion Principle: ✅ **85/100**

**Fortalezas:**
- ✅ Uso correcto de Protocols en domain layer
- ✅ Repositorios implementan interfaces abstractas
- ✅ Use Cases dependen de abstracciones, no implementaciones

**Ejemplos correctos:**
```python
# ✅ app/domain/use_cases/auth/register_user_supabase.py
class SupabaseUserRepository(Protocol):  # Abstracción
    async def create_user(...) -> SupabaseUser: ...

class RegisterUserSupabaseUseCase:
    def __init__(self, user_repository: SupabaseUserRepository):  # Depende de abstracción
        self._repository = user_repository
```

**Debilidades:**

```python
# ❌ app/presentation/api/v1/endpoints/supabase_auth.py:28-35
def get_supabase_user_repository() -> SupabaseUserRepositoryImpl:  # Implementación concreta
    return SupabaseUserRepositoryImpl()

# ✅ FIX:
def get_supabase_user_repository() -> SupabaseUserRepository:  # Usar abstracción
    return SupabaseUserRepositoryImpl()
```

---

## 7. Métricas de Complejidad

### 7.1 Archivos con Complejidad Alta

| Archivo | LOC | Funciones | Complejidad |
|---------|-----|-----------|-------------|
| `supabase_user_repository_impl.py` | 468 | 13 | Alta ❌ |
| `multimedia_repository_impl.py` | 236 | 5 | Media ⚠️ |
| `client.py` (Supabase) | ~200 | 8+ | Media ⚠️ |
| `security.py` | 186 | 7 | Baja ✅ |
| `dependencies.py` | 215 | 7 | Media ⚠️ |

### 7.2 Funciones Largas (>50 líneas)

```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py
async def create_user(...):  # 113 líneas ❌
async def get_by_id(...):     # 57 líneas ⚠️
async def authenticate(...):  # 30 líneas ✅
```

**Recomendación:** Refactorizar `create_user()` en funciones más pequeñas.

---

## 8. Tests y Coverage

**NOTA:** No se solicitó análisis de tests en esta auditoría, pero se recomienda:

```bash
# Ejecutar tests con coverage
poetry run pytest --cov=app --cov-report=html

# Métricas objetivo:
# - Coverage general: >80%
# - Coverage en domain/use_cases: >90%
# - Coverage en infrastructure: >70%
```

---

## TOP 10 Problemas Críticos (Priorizados)

### 🔴 PRIORIDAD ALTA (Resolver Inmediatamente)

#### 1. **Type Safety Incompleta (28 errores de mypy)**
   - **Impacto:** Alto - Bugs en runtime no detectados en desarrollo
   - **Esfuerzo:** Medio (2-3 días)
   - **Fix:** Agregar type hints completos en dependencies.py, middleware, security.py

#### 2. **Uso de print() en Producción**
   - **Impacto:** Alto - Logs no capturados en monitoreo
   - **Esfuerzo:** Bajo (30 min)
   - **Fix:** Reemplazar 2 ocurrencias de `print()` por `logger.error()`

#### 3. **Funciones sin Return Type Annotations**
   - **Impacto:** Alto - mypy strict mode falla
   - **Esfuerzo:** Bajo (1 día)
   - **Archivos:** dependencies.py (5 funciones), middleware (2 funciones)

### ⚠️ PRIORIDAD MEDIA (Resolver en Sprint Actual)

#### 4. **SupabaseUserRepositoryImpl Viola SRP (468 líneas)**
   - **Impacto:** Medio - Dificulta mantenimiento
   - **Esfuerzo:** Alto (3-5 días)
   - **Fix:** Separar en 3 clases (Repository, AuthService, ProfileRepository)

#### 5. **Importaciones Dentro de Funciones**
   - **Impacto:** Medio - Dificulta testing
   - **Esfuerzo:** Bajo (1 hora)
   - **Archivo:** multimedia.py (4 ocurrencias)
   - **Fix:** Usar dependency injection consistente

#### 6. **Bloques try-except Excesivamente Amplios**
   - **Impacto:** Medio - Oculta bugs
   - **Esfuerzo:** Medio (2 días)
   - **Fix:** Refactorizar create_user() en funciones más pequeñas

#### 7. **Magic Numbers y Strings Hardcoded**
   - **Impacto:** Bajo-Medio - Dificulta configuración
   - **Esfuerzo:** Bajo (2 horas)
   - **Fix:** Extraer a constantes con nombres descriptivos

### 🟡 PRIORIDAD BAJA (Backlog)

#### 8. **5 Archivos sin Formateo Black**
   - **Impacto:** Bajo - Inconsistencia visual
   - **Esfuerzo:** Muy Bajo (5 min)
   - **Fix:** `poetry run black app/`

#### 9. **7 Imports No Utilizados (Ruff F401)**
   - **Impacto:** Bajo - Código innecesario
   - **Esfuerzo:** Muy Bajo (1 min)
   - **Fix:** `poetry run ruff check --fix app/`

#### 10. **Docstrings Breves en Funciones Helper**
   - **Impacto:** Bajo - Dificulta onboarding
   - **Esfuerzo:** Medio (1 día)
   - **Fix:** Expandir docstrings con ejemplos y contexto

---

## Recomendaciones Específicas de Refactoring

### Refactoring #1: Separar SupabaseUserRepositoryImpl

**Antes (468 líneas en 1 archivo):**
```python
class SupabaseUserRepositoryImpl:
    async def get_by_id(...)
    async def create_user(...)  # 113 líneas
    async def authenticate(...)
    async def change_password(...)
    # ... 13 métodos en total
```

**Después (3 archivos especializados):**

```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py (150 LOC)
class SupabaseUserRepositoryImpl(SupabaseUserRepository):
    """CRUD básico de usuarios"""
    async def get_by_id(self, user_id: UUID) -> SupabaseUser | None: ...
    async def get_by_email(self, email: str) -> SupabaseUser | None: ...
    async def list_users(self, ...) -> list[SupabaseUser]: ...
    async def update_user(self, ...) -> SupabaseUser: ...
    async def delete_user(self, user_id: UUID) -> bool: ...

# app/infrastructure/auth/supabase_auth_service.py (100 LOC)
class SupabaseAuthService:
    """Autenticación y gestión de contraseñas"""
    async def authenticate(self, email: str, password: str) -> AuthResult: ...
    async def change_password(self, user_id: UUID, new_password: str) -> bool: ...
    async def refresh_token(self, refresh_token: str) -> TokenPair: ...

# app/infrastructure/database/repositories/supabase_profile_repository.py (150 LOC)
class SupabaseProfileRepository:
    """Gestión de perfiles con lógica de retry"""
    async def create_profile_for_user(self, user_id: UUID, ...) -> Profile: ...
    async def get_or_wait_for_profile(self, user_id: UUID) -> Profile | None: ...
    async def sync_profile_with_auth_user(self, user_id: UUID) -> None: ...
```

### Refactoring #2: Type Hints Completos en Dependencies

**Antes:**
```python
# app/core/dependencies.py
async def get_current_user(user_id: Annotated[str, Depends(get_current_user_id)]):
    ...

def require_role(required_role: str):
    async def role_dependency(current_user=Depends(get_current_user)):
        ...
    return role_dependency
```

**Después:**
```python
from typing import Callable, Awaitable
from app.domain.entities.supabase_user import SupabaseUser

async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> SupabaseUser:
    """
    Obtener usuario actual completo desde Supabase.

    Returns:
        Usuario autenticado con perfil completo

    Raises:
        HTTPException 404: Usuario no encontrado
        HTTPException 400: Usuario inactivo
    """
    repo = SupabaseUserRepositoryImpl()
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    return user


def require_role(required_role: str) -> Callable[[SupabaseUser], Awaitable[SupabaseUser]]:
    """
    Factory para crear dependency que requiere un rol específico.

    Args:
        required_role: Rol requerido ("USER", "ADMIN", "SUPERADMIN")

    Returns:
        Dependency function que valida el rol

    Example:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: SupabaseUser = Depends(require_role("ADMIN"))
        ):
            ...
    """
    async def role_dependency(
        current_user: SupabaseUser = Depends(get_current_user)
    ) -> SupabaseUser:
        """Verificar que el usuario tiene el rol requerido"""
        role_hierarchy: dict[str, int] = {
            "USER": 1,
            "ADMIN": 2,
            "SUPERADMIN": 3,
        }

        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 999)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere rol {required_role} o superior",
            )

        return current_user

    return role_dependency
```

### Refactoring #3: Logging en Lugar de print()

**Antes:**
```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py
except Exception as e:
    print(f"Error al obtener usuario por email: {e}")
    return None
```

**Después:**
```python
import logging

logger = logging.getLogger(__name__)

try:
    ...
except Exception as e:
    logger.error(
        "Error al obtener usuario por email",
        extra={
            "email": email,
            "error_type": type(e).__name__,
            "error_message": str(e)
        },
        exc_info=True  # Incluye traceback completo
    )
    return None
```

---

## Plan de Acción Recomendado

### Sprint 1 (1 semana) - Fixes Críticos

```bash
# Día 1: Formateo y Linting
poetry run black app/ tests/
poetry run ruff check --fix app/
git commit -m "style: aplicar formateo Black y fixes de Ruff"

# Día 2-3: Type Hints en Dependencies
# - Agregar return types a todas las funciones en dependencies.py
# - Agregar type hints a middleware
git commit -m "feat: agregar type hints completos en dependencies y middleware"

# Día 4: Reemplazar print() por logging
# - 2 ocurrencias en supabase_user_repository_impl.py
git commit -m "fix: reemplazar print() por logging estructurado"

# Día 5: Resolver errores de mypy high-priority
# - dict -> dict[str, Any]
# - Funciones sin return type
poetry run mypy app/  # Verificar progreso
git commit -m "fix: resolver errores críticos de type checking"
```

### Sprint 2 (2 semanas) - Refactoring SRP

```bash
# Semana 1: Separar SupabaseUserRepositoryImpl
# - Crear SupabaseAuthService
# - Crear SupabaseProfileRepository
# - Migrar lógica de autenticación
# - Actualizar use cases y endpoints

# Semana 2: Tests y ajustes
# - Tests unitarios para nuevos servicios
# - Tests de integración
# - Documentación actualizada
```

### Sprint 3 (1 semana) - Mejoras de Calidad

```bash
# Expandir docstrings
# Extraer magic numbers a constantes
# Refactorizar funciones largas
# Aplicar dependency injection consistente
```

---

## Configuración Recomendada para CI/CD

### Pre-commit Hooks (.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.15
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.18.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-all]
        args: [--strict]
```

**Instalar:**
```bash
poetry run pre-commit install
```

### GitHub Actions Workflow

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: curl -sSL https://install.python-poetry.org | python3 -

      - name: Install dependencies
        run: poetry install --with dev

      - name: Black formatting check
        run: poetry run black --check app/ tests/

      - name: Ruff linting
        run: poetry run ruff check app/ tests/

      - name: mypy type checking
        run: poetry run mypy app/

      - name: Run tests with coverage
        run: poetry run pytest --cov=app --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

---

## Conclusiones

### Resumen de Esfuerzo Estimado

| Categoría | Esfuerzo | Impacto | ROI |
|-----------|----------|---------|-----|
| Type Hints Completos | 3 días | Alto | ⭐⭐⭐⭐⭐ |
| Reemplazar print() | 30 min | Alto | ⭐⭐⭐⭐⭐ |
| Formateo Black | 5 min | Bajo | ⭐⭐⭐⭐⭐ |
| Fix Ruff | 5 min | Bajo | ⭐⭐⭐⭐⭐ |
| Refactoring SRP | 2 semanas | Medio | ⭐⭐⭐⭐ |
| Docstrings | 1 semana | Medio | ⭐⭐⭐ |

### Estado Final Proyectado (Post-Fixes)

| Categoría | Actual | Proyectado |
|-----------|--------|------------|
| **Formateo (Black)** | 92/100 | 100/100 ✅ |
| **Linting (Ruff)** | 95/100 | 100/100 ✅ |
| **Type Safety (mypy)** | 45/100 | 90/100 ✅ |
| **Docstrings** | 75/100 | 85/100 ✅ |
| **SOLID Principles** | 70/100 | 85/100 ✅ |
| **Code Smells** | 60/100 | 80/100 ✅ |
| **Score General** | **68/100** | **90/100** ✅ |

### Próximos Pasos Inmediatos

1. ✅ Ejecutar `poetry run black app/ tests/` (5 min)
2. ✅ Ejecutar `poetry run ruff check --fix app/` (1 min)
3. ✅ Reemplazar 2 `print()` por `logger.error()` (30 min)
4. ✅ Agregar return types a dependencies.py (2 horas)
5. ⚠️ Planificar refactoring de SupabaseUserRepositoryImpl (Sprint 2)

---

**Documento generado automáticamente por Bandang Code Quality Agent**
**Versión:** 1.0.0
**Fecha:** 2025-10-21

# 📊 Reporte de Integración con Supabase - BandangWeb API

**Fecha:** 2025-10-18
**Versión de la API:** 1.0.0
**Autor:** Claude Code

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Auditoría de la Integración Actual](#1-auditoría-de-la-integración-actual)
3. [Análisis de Seguridad](#2-análisis-de-seguridad)
4. [Análisis de Autenticación](#3-análisis-de-autenticación)
5. [Análisis de Operaciones de Base de Datos](#4-análisis-de-operaciones-de-base-de-datos)
6. [Storage y Multimedia](#5-storage-y-multimedia)
7. [Recomendaciones](#6-recomendaciones)
8. [Estado de Migraciones y Schemas](#7-estado-de-migraciones-y-schemas)
9. [Métricas del Proyecto](#8-métricas-del-proyecto)
10. [Plan de Acción](#9-plan-de-acción)

---

## Resumen Ejecutivo

### ✅ Fortalezas Identificadas

- **Arquitectura limpia** con separación clara de capas (Domain, Infrastructure, Presentation)
- **Cliente Supabase bien implementado** con patrón Singleton y métodos helper útiles
- **Autenticación robusta** usando Supabase Auth con JWT tokens
- **RLS Policies documentadas** en SQL schemas
- **Tests mockeados** para evitar dependencias de servicios externos
- **Manejo de errores personalizado** con excepciones específicas

### ⚠️ Áreas de Mejora Críticas

1. **Uso excesivo de `admin_client`** (19 usos) bypaseando RLS innecesariamente
2. **Storage de Supabase NO implementado** - URLs hardcodeadas sin upload/download real
3. **Realtime NO utilizado** - Feature de Supabase desaprovechada
4. **RLS policies inconsistentes** entre documentación y uso real
5. **Falta de validación de roles** en algunos endpoints públicos
6. **Sin implementación de Edge Functions**
7. **Triggers de base de datos sin verificación en código**

---

## 1. Auditoría de la Integración Actual

### 1.1 Cliente Supabase (`app/infrastructure/external/supabase/client.py`)

**Ubicación:** `app/infrastructure/external/supabase/client.py:17-236`

#### Implementación

```python
class SupabaseClient:
    """Cliente de Supabase con métodos de utilidad"""

    def __init__(self) -> None:
        self._client: AsyncClient | None = None
        self._admin_client: AsyncClient | None = None
        self._options = ClientOptions(
            schema="public",
            headers={"X-Client-Info": f"bandangweb-api/{settings.VERSION}"},
            auto_refresh_token=True,
            persist_session=False,  # ⚠️ Importante: Sin persistencia de sesión
        )
```

**✅ Buenas prácticas implementadas:**

- Patrón Singleton con `@lru_cache` (línea 223-231)
- Lazy initialization de clientes (líneas 36-52)
- Métodos helper genéricos: `get_by_id()`, `get_by_field()`, `list_all()`, `create()`, `update()`, `delete()`, `execute_rpc()`
- Tipo de retorno explícito con type hints
- Async/await correctamente implementado
- Header personalizado `X-Client-Info` para tracking

**⚠️ Puntos de atención:**

- `persist_session=False` (línea 33): Las sesiones no se persisten, requiere refresh manual
- No hay manejo de reconexión automática en caso de error
- No hay timeout configurado para requests
- No hay retry logic para operaciones fallidas

### 1.2 Repositorios que usan Supabase

#### **Total: 3 repositorios implementados**

| Repositorio | Tabla | Cliente usado | Líneas de código |
|-------------|-------|---------------|------------------|
| `SupabaseUserRepositoryImpl` | `profiles`, `auth.users` | Regular + Admin | ~398 líneas |
| `EventRepositoryImpl` | `eventos` | Admin (⚠️) | ~69 líneas |
| `MultimediaRepositoryImpl` | `multimedia` | Regular + Admin | ~234 líneas |

#### 1.2.1 SupabaseUserRepositoryImpl

**Ubicación:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py`

**Métodos implementados:**

```python
- get_by_id(user_id: UUID) -> SupabaseUser | None
- get_by_email(email: str) -> SupabaseUser | None
- list_users(skip: int, limit: int, role: UserRole | None) -> list[SupabaseUser]
- create_user(email, password, full_name, role) -> SupabaseUser
- update_user(user_id, full_name, role, is_active) -> SupabaseUser
- delete_user(user_id: UUID) -> bool
- change_password(user_id: UUID, new_password: str) -> bool
- authenticate(email: str, password: str) -> tuple[SupabaseUser, str, str] | None
```

**✅ Aspectos positivos:**

- **Manejo de lag de Supabase** (líneas 188-203): Reintentos al auto-confirmar email
- **Trigger fallback** (líneas 213-228): Si el trigger `on_auth_user_created` falla, crea el perfil manualmente
- **RPC personalizada** para `get_by_email` (líneas 94-97): Usa función `get_user_by_email` en PostgreSQL
- **Combina datos** de `auth.users` y `profiles` (líneas 54-72)

**⚠️ Problemas de seguridad:**

- **Líneas 39-46**: Usa `admin_client` para `get_by_id()` - **INNECESARIO**, podría usar cliente regular con RLS
- **Línea 158**: Usa `admin_client` para verificar email duplicado - correcto (bypasa RLS para validación)
- **Líneas 195-196**: Auto-confirma email con `admin_client` - **CRÍTICO**: Todos los usuarios se auto-confirman sin validación

**🔧 Código problemático:**

```python
# Líneas 187-203: AUTO-CONFIRMACIÓN SIN VALIDACIÓN
for attempt in range(max_retries):
    try:
        await admin_client.auth.admin.update_user_by_id(
            str(user_id), {"email_confirm": True}  # ⚠️ Auto-confirma TODOS los usuarios
        )
        break
    except Exception as e:
        if "user not found" in str(e).lower() and attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
        else:
            raise e
```

**Impacto:** Usuarios sin verificar email pueden acceder al sistema inmediatamente.

#### 1.2.2 EventRepositoryImpl

**Ubicación:** `app/infrastructure/database/repositories/event_repository_impl.py`

**⚠️ PROBLEMA CRÍTICO - Línea 41:**

```python
async def create(self, event_data: EventCreateDTO) -> Event:
    # Usar cliente admin para bypassar RLS  ← ⚠️ INNECESARIO
    client = await self._supabase_client.admin_client
```

**Impacto:**

- Bypasea RLS policy `"Anyone can insert events"` definida en `scripts/create_events_schema.sql:54-58`
- No hay necesidad de usar `admin_client` porque la policy ya permite INSERT público
- El comentario indica que fue intencional, pero es redundante

**🔧 Solución sugerida:**

```python
# Usar cliente regular - la RLS policy ya permite INSERT
client = await self._supabase_client.client
```

#### 1.2.3 MultimediaRepositoryImpl

**Ubicación:** `app/infrastructure/database/repositories/multimedia_repository_impl.py`

**Uso de clientes:**

- **Línea 41**: `admin_client` para CREATE - ⚠️ Necesario solo si el usuario no está autenticado
- **Línea 75**: `client` regular para GET_BY_ID - ✅ Correcto
- **Línea 116**: `client` regular para LIST_ALL - ✅ Correcto
- **Línea 169**: `admin_client` para UPDATE - ⚠️ Debería verificar permisos primero
- **Línea 216**: `admin_client` para DELETE - ⚠️ Debería verificar permisos primero

**📊 Análisis de filtros (líneas 121-128):**

```python
if category:
    query = query.eq("category", category)
if type:
    query = query.eq("type", type)
if is_published is not None:
    query = query.eq("is_published", is_published)
if featured is not None:
    query = query.eq("featured", featured)
```

**✅ Bien implementado:** Filtros opcionales con verificación de `None`

### 1.3 Endpoints que interactúan con Supabase

#### **Total: 4 archivos de endpoints**

| Endpoint | Ruta | Autenticación | RLS Bypaseada |
|----------|------|---------------|---------------|
| `supabase_auth.py` | `/api/v1/auth/supabase/*` | No (registro/login) | Sí (admin) |
| `events.py` | `/api/v1/events` | No (⚠️ PÚBLICO) | Sí (admin) |
| `multimedia.py` | `/api/v1/multimedia` | No (lectura pública) | Sí (admin en escritura) |
| `users.py` | `/api/v1/users` | Sí (requiere auth) | N/A |

#### 1.3.1 supabase_auth.py

**Endpoints:**

- `POST /supabase/register` (líneas 66-152)
- `POST /supabase/login` (líneas 154-193)
- `POST /supabase/refresh` (líneas 196-235)
- `POST /supabase/logout` (líneas 238-246)

**✅ Flujo de registro robusto (líneas 80-137):**

```python
# 1. Registrar usuario
user = await use_case.execute(...)

try:
    # 2. Intentar login inmediato
    user, access_token, refresh_token = await login_use_case.execute(...)
except InvalidCredentialsError:
    # 3. Fallback: Generar tokens manualmente si falla login
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
```

**⚠️ Problema de diseño:**

- El fallback manual (líneas 122-126) indica que Supabase Auth tiene lag
- Genera tokens propios de FastAPI en lugar de tokens de Supabase
- Inconsistencia: A veces tokens de Supabase, a veces tokens propios

**🔧 Endpoint de logout stateless (líneas 238-246):**

```python
@router.post("/logout")
async def logout() -> dict[str, str]:
    """En una implementación con JWT stateless, el logout es manejado por el cliente"""
    return {"message": "Sesión cerrada exitosamente"}
```

**Impacto:** No invalida tokens en servidor - depende del cliente eliminarlos.

#### 1.3.2 events.py

**⚠️ ENDPOINT PÚBLICO SIN AUTENTICACIÓN (línea 21-22):**

```python
@router.post(
    "/",
    # ⚠️ NO hay Depends(get_current_user) - PÚBLICO
    summary="Crear un nuevo evento",
    description="Este endpoint es PÚBLICO para permitir formularios de contacto.",
)
async def create_event(event_data: EventCreate, ...):
```

**Justificación en comentarios (líneas 31-34):**

> NOTA DE SEGURIDAD: Este endpoint es PÚBLICO intencionalmente
> para permitir que clientes potenciales soliciten cotizaciones.
> Los datos se validan estrictamente con Pydantic y se almacenan
> con estado 'pending' para revisión manual del equipo.

**✅ Validación presente:** Pydantic valida todos los campos antes de insertar.

**⚠️ Riesgos:**

- Vulnerable a spam/flood - no hay rate limiting específico
- No hay CAPTCHA para evitar bots
- No hay límite de requests por IP

#### 1.3.3 multimedia.py

**Endpoints implementados:**

- `POST /` - Crear multimedia (líneas 23-58)
- `GET /` - Listar con filtros (líneas 61-110)
- `GET /{multimedia_id}` - Obtener por ID (líneas 113-150)
- `PATCH /{multimedia_id}` - Actualizar (líneas 153-198)
- `DELETE /{multimedia_id}` - Eliminar (líneas 201-231)

**⚠️ TODOS los endpoints son PÚBLICOS** - No requieren autenticación

**Impacto:**

- Cualquiera puede listar multimedia (aceptable si `is_published=true`)
- Cualquiera puede CREAR multimedia (⚠️ PROBLEMA DE SEGURIDAD)
- Cualquiera puede ACTUALIZAR multimedia (🚨 CRÍTICO)
- Cualquiera puede ELIMINAR multimedia (🚨 CRÍTICO)

**🔧 Líneas problemáticas:**

```python
# Línea 30: Sin Depends(get_current_user) o require_role
async def create_multimedia(
    multimedia_data: MultimediaCreate,
    # ⚠️ FALTA: current_user = Depends(require_role("ADMIN"))
):
```

### 1.4 Use Cases de Autenticación

#### **Total: 2 use cases**

| Use Case | Archivo | Responsabilidad |
|----------|---------|-----------------|
| `RegisterUserSupabaseUseCase` | `register_user_supabase.py` | Validar y crear usuario |
| `LoginUserSupabaseUseCase` | `login_user_supabase.py` | Autenticar y retornar tokens |

#### 1.4.1 RegisterUserSupabaseUseCase

**Validaciones (líneas 62-68):**

```python
if not email or "@" not in email:
    raise ValidationError("Email inválido")

if not password or len(password) < 8:
    raise ValidationError("La contraseña debe tener al menos 8 caracteres")
```

**⚠️ Validación débil:**

- Solo verifica presencia de `@` - no valida formato completo
- Solo valida longitud mínima 8 - no verifica complejidad (mayúsculas, números, símbolos)
- `app/core/security.py:136-161` tiene `validate_password_strength()` pero **NO se usa**

#### 1.4.2 LoginUserSupabaseUseCase

**Flujo (líneas 52-64):**

```python
auth_result = await self._repository.authenticate(email, password)

if not auth_result:
    raise InvalidCredentialsError("Credenciales inválidas o usuario no encontrado/confirmado.")

user, access_token, refresh_token = auth_result

if not user.is_active:
    raise InvalidCredentialsError("Usuario inactivo.")

return user, access_token, refresh_token
```

**✅ Aspectos positivos:**

- Verifica estado activo del usuario
- Retorna tokens de Supabase directamente
- Mensaje de error genérico (no revela si email existe)

---

## 2. Análisis de Seguridad

### 2.1 Uso de RLS Policies

#### **Documentación vs. Realidad**

| Tabla | RLS Habilitado | Policies Documentadas | Policies Aplicadas | Bypaseadas por código |
|-------|----------------|----------------------|--------------------|-----------------------|
| `profiles` | ✅ | 5 policies | ❓ (no verificado) | Sí (admin_client) |
| `eventos` | ✅ | 3 policies | ❓ (no verificado) | Sí (admin_client) |
| `multimedia` | ✅ | 5 policies | ❓ (no verificado) | Sí (admin_client) |

**⚠️ PROBLEMA:** Las policies están documentadas en SQL pero el código usa `admin_client` para bypassearlas.

#### Policies Documentadas (desde `docs/database/schema.md`)

##### **Tabla `profiles`:**

```sql
-- Policy: Usuarios pueden ver su propio perfil (línea 256-260)
CREATE POLICY "Users can view own profile"
ON public.users
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- Policy: Admins pueden ver todos los usuarios (línea 262-273)
CREATE POLICY "Admins can view all users"
ON public.users
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.users
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);
```

**⚠️ Inconsistencia:** La documentación usa tabla `public.users`, pero el código usa `public.profiles`.

##### **Tabla `eventos`:**

```sql
-- Policy: Cualquiera puede insertar eventos (línea 296-300)
CREATE POLICY "Anyone can insert events"
ON public.eventos
FOR INSERT
TO anon, authenticated
WITH CHECK (true);
```

**✅ Correcto:** Permite INSERT público - coincide con el endpoint público.

**⚠️ Pero:** El código usa `admin_client` innecesariamente.

##### **Tabla `multimedia`:**

```sql
-- Policy: Cualquiera puede ver contenido publicado (línea 336-340)
CREATE POLICY "Anyone can view published multimedia"
ON public.multimedia
FOR SELECT
TO anon, authenticated
USING (is_published = true);

-- Policy: Admins pueden insertar multimedia (línea 356-366)
CREATE POLICY "Admins can insert multimedia"
ON public.multimedia
FOR INSERT
TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.users
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);
```

**🚨 PROBLEMA CRÍTICO:** El endpoint de multimedia NO verifica roles, pero confía en RLS policies que **están siendo bypaseadas** por `admin_client`.

### 2.2 Admin Client vs Regular Client

#### **Uso de `admin_client` en el código:**

```bash
Total de usos de admin_client: 19 líneas
```

**Desglose por archivo:**

| Archivo | Usos | Necesarios | Innecesarios |
|---------|------|-----------|--------------|
| `supabase_user_repository_impl.py` | 12 | 8 | 4 |
| `event_repository_impl.py` | 1 | 0 | 1 |
| `multimedia_repository_impl.py` | 3 | 0 | 3 |

#### **Casos donde `admin_client` ES necesario:**

1. ✅ **Auto-confirmar email** (línea 195): Operación admin en `auth.users`
2. ✅ **Verificar email duplicado** (línea 163): Buscar en perfiles sin RLS
3. ✅ **Crear perfil manualmente** (línea 222): Fallback si trigger falla
4. ✅ **Cambiar password de otro usuario** (línea 352): Operación admin
5. ✅ **Eliminar usuario en Auth** (línea 325): Requiere permisos admin
6. ✅ **Obtener datos de auth.users** (línea 55): Tabla protegida de Supabase
7. ✅ **Actualizar metadatos de usuario** (línea 291): User metadata protegido
8. ✅ **Insertar perfil con service role** (línea 222): Sin sesión de usuario

#### **Casos donde `admin_client` NO es necesario:**

1. ❌ **get_by_id en profiles** (línea 39): Policy permite SELECT con `auth.uid() = id`
2. ❌ **Crear evento** (event_repository:41): Policy permite INSERT público
3. ❌ **Crear multimedia** (multimedia_repository:41): Debería verificar rol con RLS
4. ❌ **Actualizar multimedia** (multimedia_repository:169): Debería verificar rol con RLS
5. ❌ **Eliminar multimedia** (multimedia_repository:216): Debería verificar rol con RLS

### 2.3 Manejo de Service Role Key

**Ubicación de configuración:** `app/core/config.py:70-72`

```python
SUPABASE_SERVICE_ROLE_KEY: str = Field(
    ..., description="Clave de servicio de Supabase (bypasa RLS)"
)
```

**✅ Buenas prácticas:**

- Cargada desde `.env` (no hardcoded)
- Campo requerido con validación Pydantic
- Documentación clara de su propósito

**⚠️ Riesgos:**

- **No hay rotación de keys** implementada
- **No hay auditoría** de uso de service role key
- **No hay límite de operaciones** con admin client
- Si la key se filtra, acceso completo a la base de datos

### 2.4 Exposición de Datos Sensibles

#### **Datos sensibles en responses:**

**✅ NO expone:**

- Passwords hasheados
- Service role key
- Refresh tokens en logs

**⚠️ Expone en responses:**

```python
# app/presentation/api/v1/schemas/supabase_auth.py
class UserResponse(BaseModel):
    id: UUID
    email: str          # ⚠️ Email visible en responses
    full_name: str | None
    role: str           # ⚠️ Rol visible - puede revelar estructura de permisos
    is_active: bool
```

**Impacto:** Moderado - roles y emails visibles, pero es esperado para un perfil de usuario.

#### **Datos sensibles en logs:**

**Ubicación:** `app/presentation/middleware/logging.py`

**⚠️ No revisado en este análisis** - requiere inspección del código de logging.

---

## 3. Análisis de Autenticación

### 3.1 Flujo Completo de Login/Registro

#### **Diagrama de flujo:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    REGISTRO DE USUARIO                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────┐
    │ 1. POST /auth/supabase/register                 │
    │    - email, password, full_name                 │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 2. RegisterUserSupabaseUseCase.execute()        │
    │    - Validar email (solo '@')                   │
    │    - Validar password (solo len >= 8)           │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 3. SupabaseUserRepositoryImpl.create_user()     │
    │    a. Verificar email duplicado (admin_client)  │
    │    b. sign_up en Supabase Auth                  │
    │    c. Auto-confirmar email (admin_client) ⚠️    │
    │    d. Esperar trigger crear perfil              │
    │    e. Si falla, crear perfil manual             │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 4. Trigger: on_auth_user_created                │
    │    - INSERT INTO profiles (id, email, ...)      │
    │    - Role: 'user' por defecto                   │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 5. Auto-login inmediato (intento)               │
    │    - Si falla: generar tokens FastAPI           │
    │    - Si éxito: retornar tokens Supabase         │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ RETORNAR: user, access_token, refresh_token     │
    └─────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOGIN DE USUARIO                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────┐
    │ 1. POST /auth/supabase/login                    │
    │    - email, password                            │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 2. LoginUserSupabaseUseCase.execute()           │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 3. SupabaseUserRepositoryImpl.authenticate()    │
    │    a. sign_in_with_password (Supabase Auth)     │
    │    b. Obtener user y session                    │
    │    c. get_by_id para perfil completo            │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ 4. Verificar is_active                          │
    └───────────────────────┬─────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │ RETORNAR: user, access_token, refresh_token     │
    │ (Tokens de Supabase Auth)                       │
    └─────────────────────────────────────────────────┘
```

### 3.2 Integración con JWT Tokens

#### **Tokens de Supabase vs. Tokens propios de FastAPI**

**Problema de diseño identificado:**

El sistema mezcla dos sistemas de tokens:

1. **Tokens de Supabase Auth** (login normal)
2. **Tokens propios de FastAPI** (fallback en registro)

**Ubicación del problema:** `app/presentation/api/v1/endpoints/supabase_auth.py:122-126`

```python
# Generar tokens manualmente (FastAPI)
from app.core.security import create_access_token, create_refresh_token

access_token = create_access_token({"sub": str(user.id)})
refresh_token = create_refresh_token({"sub": str(user.id)})
```

**vs.**

```python
# Tokens de Supabase Auth (login normal)
auth_response = await client.auth.sign_in_with_password(...)
access_token = auth_response.session.access_token
refresh_token = auth_response.session.refresh_token
```

**Impacto:**

- **Inconsistencia:** Algunos tokens verificados por Supabase, otros por FastAPI
- **Confusión:** `decode_token()` en `app/core/security.py` solo valida tokens FastAPI, no de Supabase
- **Problema de seguridad:** Tokens FastAPI pueden no sincronizar con estado de Supabase

#### **Verificación de Tokens**

**Ubicación:** `app/core/dependencies.py:25-48`

```python
async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Obtener ID del usuario desde JWT"""
    payload = decode_token(token, expected_type="access")  # FastAPI JWT
    user_id: str | None = payload.get("sub")

    if user_id is None:
        raise HTTPException(...)

    return user_id
```

**⚠️ PROBLEMA:** `decode_token()` usa `settings.SECRET_KEY`, NO verifica tokens de Supabase.

**Ubicación de decode_token:** `app/core/security.py:97-133`

```python
def decode_token(token: str, expected_type: Literal["access", "refresh"] | None = None):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,  # ⚠️ SECRET_KEY de FastAPI, NO de Supabase
            algorithms=[settings.ALGORITHM]
        )
        # ...
    except JWTError as e:
        raise HTTPException(...)
```

**Consecuencia:** Los tokens de Supabase Auth **NO funcionarán** con los endpoints protegidos de FastAPI.

### 3.3 Refresh Tokens y Sesiones

#### **Endpoint de Refresh**

**Ubicación:** `app/presentation/api/v1/endpoints/supabase_auth.py:196-235`

```python
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """Refrescar token de acceso"""
    # Decodificar refresh token (FastAPI JWT)
    payload = decode_token(request.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")

    # Generar nuevos tokens (FastAPI)
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    return TokenResponse(access_token=new_access_token, ...)
```

**⚠️ PROBLEMA:** NO usa `client.auth.refresh_session()` de Supabase.

**Impacto:**

- Tokens refrescados sin validar con Supabase
- Usuario puede haber sido eliminado/desactivado en Supabase pero token sigue válido
- No sincroniza estado con Supabase Auth

**✅ Implementación correcta debería ser:**

```python
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refrescar token usando Supabase Auth"""
    client = await supabase_client.client

    # Refrescar con Supabase
    refresh_response = await client.auth.refresh_session(request.refresh_token)

    if refresh_response.error:
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    return TokenResponse(
        access_token=refresh_response.session.access_token,
        refresh_token=refresh_response.session.refresh_token,
        token_type="bearer",
    )
```

### 3.4 Roles y Permisos

#### **Roles definidos**

**Ubicación:** `app/domain/entities/supabase_user.py:11-16`

```python
class UserRole(str, Enum):
    """Roles de usuario"""
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
```

#### **Verificación de roles en dependencies**

**Ubicación:** `app/core/dependencies.py:88-120`

```python
def require_role(required_role: str):
    """Factory para crear dependency que requiere un rol específico"""

    async def role_dependency(current_user=Depends(get_current_user)):
        # Orden jerárquico de roles
        role_hierarchy = {
            "USER": 1,
            "ADMIN": 2,
            "SUPERADMIN": 3,
        }

        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 999)

        if user_role_level < required_role_level:
            raise HTTPException(status_code=403, ...)

        return current_user

    return role_dependency
```

**✅ Aspectos positivos:**

- Sistema jerárquico (SUPERADMIN > ADMIN > USER)
- Factory pattern para reutilización
- Verifica nivel de rol, no solo igualdad

**⚠️ Problema:**

- `require_role()` **NO se usa en endpoints de multimedia** que deberían requerir ADMIN
- `require_role()` solo se importa pero no se aplica en `events.py` y `multimedia.py`

**Prueba:**

```bash
$ grep -n "require_role" app/presentation/api/v1/endpoints/events.py
7:from app.core.dependencies import get_create_event_use_case, require_role

$ grep -n "require_role" app/presentation/api/v1/endpoints/multimedia.py
9:from app.core.dependencies import get_create_multimedia_use_case, require_role
```

**Importado pero NO usado en los decoradores de endpoints.**

#### **Métodos de verificación en entidad**

**Ubicación:** `app/domain/entities/supabase_user.py:39-78`

```python
def has_role(self, required_role: UserRole) -> bool:
    """Verificar si el usuario tiene un rol específico o superior"""
    role_hierarchy = {
        UserRole.USER: 0,
        UserRole.ADMIN: 1,
        UserRole.SUPERADMIN: 2,
    }
    return role_hierarchy[self.role] >= role_hierarchy[required_role]

def can_modify_user(self, target_user: "SupabaseUser") -> bool:
    """Verificar si puede modificar otro usuario"""
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
```

**✅ Excelente:** Lógica de negocio en la entidad de dominio (Clean Architecture).

**⚠️ Pero:** Estos métodos **NO se usan** en los repositorios o use cases.

---

## 4. Análisis de Operaciones de Base de Datos

### 4.1 Operaciones CRUD Implementadas

#### **Resumen por entidad:**

| Entidad | CREATE | READ | UPDATE | DELETE | LIST | SEARCH |
|---------|--------|------|--------|--------|------|--------|
| SupabaseUser | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (por email) |
| Event | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Multimedia | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

**⚠️ Event solo tiene CREATE** - No se pueden listar, actualizar o eliminar eventos vía API.

### 4.2 Uso de Métodos Helper del SupabaseClient

**Métodos disponibles en `SupabaseClient`:**

```python
- get_by_id(table, id_value, select="*")
- get_by_field(table, field, value, select="*")
- list_all(table, select="*", order_by, limit, offset)
- create(table, data)
- update(table, id_value, data)
- delete(table, id_value)
- execute_rpc(function_name, params)
```

**Uso en repositorios:**

| Método | SupabaseUserRepo | EventRepo | MultimediaRepo |
|--------|-----------------|-----------|----------------|
| `get_by_id` | ❌ (manual) | ❌ | ❌ (manual) |
| `get_by_field` | ❌ (RPC) | ❌ | ❌ |
| `list_all` | ❌ (manual) | ❌ | ❌ (manual) |
| `create` | ❌ (manual) | ❌ (manual) | ❌ (manual) |
| `update` | ❌ (manual) | ❌ | ❌ (manual) |
| `delete` | ❌ (manual) | ❌ | ❌ (manual) |
| `execute_rpc` | ✅ (get_user_by_email) | ❌ | ❌ |

**Conclusión:** Los métodos helper de `SupabaseClient` **casi no se usan**. Todo está implementado manualmente.

**Impacto:**

- Código duplicado en repositorios
- No se aprovecha la abstracción del cliente
- Más difícil de mantener

### 4.3 Consultas Complejas y RPC Calls

#### **RPC Implementadas:**

**1. `get_user_by_email`**

**Ubicación:** `scripts/supabase_auth_schema.sql:108-130`

```sql
CREATE OR REPLACE FUNCTION public.get_user_by_email(p_email TEXT)
RETURNS TABLE (
    id UUID,
    email TEXT,
    full_name TEXT,
    role TEXT,
    is_active BOOLEAN
) LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.email,
        p.full_name,
        p.role,
        p.is_active
    FROM
        public.profiles p
    WHERE
        p.email = p_email
        AND p.is_active = TRUE;
END;
$$;
```

**Uso en código:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py:94-97`

```python
response = await client.rpc(
    "get_user_by_email", {"p_email": email}
).execute()
```

**✅ Correcto:** Usa RPC para lógica de negocio en la BD.

**⚠️ Pero:** La RPC tiene `SECURITY DEFINER` - se ejecuta con permisos del creador (admin), no del usuario.

**2. Script de fix con RPC `exec_sql`**

**Ubicación:** `scripts/fix_profiles_insert_policy.py:35`

```python
result = await client.rpc('exec_sql', {'sql': sql_fix}).execute()
```

**⚠️ PROBLEMA:** Intenta ejecutar RPC `exec_sql` que **NO existe** en Supabase por defecto.

**Comentario en el script (líneas 42-43):**

> NOTA: Este script requiere una función RPC 'exec_sql' en Supabase.

**Impacto:** El script no funciona sin crear manualmente la función RPC.

### 4.4 Potenciales N+1 Queries

#### **Caso 1: get_by_id en SupabaseUserRepository**

**Ubicación:** `app/infrastructure/database/repositories/supabase_user_repository_impl.py:42-72`

```python
# Query 1: Obtener perfil
response = await admin_client.table("profiles").select("*").eq("id", str(user_id)).execute()

# Query 2: Obtener datos de auth.users
auth_response = await admin_client.auth.admin.get_user_by_id(str(user_id))
```

**Impacto:** 2 queries por usuario - si se lista usuarios, podría ser N+1.

**✅ Mitigación:** El método `list_users()` NO combina con `auth.users`, solo retorna datos de `profiles`.

#### **Caso 2: Multimedia con created_by**

**Ubicación:** `app/domain/entities/multimedia.py:33`

```python
created_by: UUID | None = None
```

**⚠️ Problema potencial:**

- Si se lista multimedia y se quiere obtener info del creador, requeriría query adicional por item
- No hay endpoint para obtener multimedia con info de creador (join)

**Solución sugerida:** Usar `.select("*, creator:created_by(*)")` en Supabase.

---

## 5. Storage y Multimedia

### 5.1 Análisis de Integración con Supabase Storage

**Resultado de búsqueda:**

```bash
$ grep -r "storage" app/ --include="*.py"
(Sin resultados en app/)

$ grep -r "bucket" app/ --include="*.py"
app/core/config.py:61:    AWS_BUCKET_NAME: str | None = None
```

**Conclusión: Supabase Storage NO está implementado.**

### 5.2 Revisión de Endpoints de Multimedia

**Ubicación:** `app/presentation/api/v1/endpoints/multimedia.py`

**Esquema de creación:** `app/presentation/api/v1/schemas/multimedia.py`

```python
class MultimediaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., alias="mediaType")  # "image" | "video"
    url: str = Field(...)  # ⚠️ URL como string - NO hay upload
    thumbnail_url: str | None = Field(None, alias="thumbnailUrl")
    description: str | None = None
    category: str
    # ...
```

**⚠️ PROBLEMA:** El campo `url` es un string libre - **NO hay upload de archivos**.

**Impacto:**

- Usuarios deben subir archivos externamente (AWS S3, Cloudinary, etc.)
- No se aprovecha Supabase Storage
- No hay validación de tipo de archivo
- No hay generación de thumbnails automática
- No hay límites de tamaño

### 5.3 Políticas de Acceso a Archivos

**No aplicable** - Supabase Storage no está en uso.

**⚠️ Si se implementara Storage:**

Necesitaría policies como:

```sql
-- Bucket para multimedia pública
CREATE POLICY "Public can view published files"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'multimedia' AND (storage.foldername(name))[1] = 'public');

-- Solo admins pueden subir
CREATE POLICY "Admins can upload multimedia"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'multimedia' AND
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role IN ('admin', 'superadmin')
  )
);
```

---

## 6. Recomendaciones

### 6.1 Mejores Prácticas No Implementadas

#### **CRÍTICAS (Prioridad 1):**

1. **🚨 Proteger endpoints de multimedia con autenticación**

   **Problema:** Endpoints de CREATE, UPDATE, DELETE son públicos.

   **Solución:**

   ```python
   # app/presentation/api/v1/endpoints/multimedia.py

   @router.post("/", dependencies=[Depends(require_role("ADMIN"))])
   async def create_multimedia(...):
       pass

   @router.patch("/{multimedia_id}", dependencies=[Depends(require_role("ADMIN"))])
   async def update_multimedia(...):
       pass

   @router.delete("/{multimedia_id}", dependencies=[Depends(require_role("ADMIN"))])
   async def delete_multimedia(...):
       pass
   ```

2. **🚨 Eliminar uso innecesario de `admin_client`**

   **Archivos a modificar:**

   - `event_repository_impl.py:41` - Cambiar a `client`
   - `multimedia_repository_impl.py:41,169,216` - Cambiar a `client` + verificar rol con RLS

   **Ejemplo:**

   ```python
   # event_repository_impl.py
   async def create(self, event_data: EventCreateDTO) -> Event:
       # Cambiar de:
       client = await self._supabase_client.admin_client

       # A:
       client = await self._supabase_client.client  # Respeta RLS
   ```

3. **🚨 Usar tokens de Supabase Auth consistentemente**

   **Problema:** Mezcla de tokens FastAPI y Supabase.

   **Solución:** Eliminar `create_access_token()` y `create_refresh_token()` de FastAPI, usar solo Supabase Auth.

   **Archivos a modificar:**

   - `app/presentation/api/v1/endpoints/supabase_auth.py:122-126` - Eliminar fallback manual
   - `app/presentation/api/v1/endpoints/supabase_auth.py:196-235` - Usar `refresh_session()` de Supabase
   - `app/core/dependencies.py:38` - Validar tokens con Supabase, no con FastAPI

4. **🚨 Validación de password con complejidad**

   **Problema:** Solo valida longitud >= 8.

   **Solución:**

   ```python
   # app/domain/use_cases/auth/register_user_supabase.py
   from app.core.security import validate_password_strength

   async def execute(self, email: str, password: str, ...):
       # Validar email
       if not email or "@" not in email:
           raise ValidationError("Email inválido")

       # Validar password con complejidad
       is_valid, error_msg = validate_password_strength(password)
       if not is_valid:
           raise ValidationError(error_msg)

       # ...
   ```

5. **🚨 Rate limiting específico para endpoints públicos**

   **Problema:** Endpoint de eventos es vulnerable a spam.

   **Solución:**

   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)

   @router.post("/", dependencies=[limiter.limit("5/minute")])
   async def create_event(event_data: EventCreate):
       # Solo 5 eventos por minuto por IP
       pass
   ```

#### **IMPORTANTES (Prioridad 2):**

6. **Implementar Supabase Storage para multimedia**

   **Beneficios:**

   - Upload directo desde la API
   - Generación automática de URLs firmadas temporales
   - Thumbnails automáticos con Supabase Image Transformation
   - Políticas de acceso granular

   **Implementación sugerida:**

   ```python
   # app/infrastructure/external/supabase/storage.py

   class SupabaseStorageService:
       async def upload_file(
           self,
           bucket: str,
           file_path: str,
           file_content: bytes,
           content_type: str
       ) -> str:
           """Upload file y retornar URL pública"""
           client = await supabase_client.client

           response = await client.storage.from_(bucket).upload(
               file_path,
               file_content,
               {"content-type": content_type}
           )

           if response.error:
               raise SupabaseError(f"Upload failed: {response.error.message}")

           public_url = client.storage.from_(bucket).get_public_url(file_path)
           return public_url

       async def get_signed_url(
           self,
           bucket: str,
           file_path: str,
           expires_in: int = 3600
       ) -> str:
           """Generar URL firmada temporal"""
           client = await supabase_client.client

           response = await client.storage.from_(bucket).create_signed_url(
               file_path,
               expires_in
           )

           if response.error:
               raise SupabaseError(f"Signed URL failed: {response.error.message}")

           return response.data["signedURL"]
   ```

   **Endpoint de upload:**

   ```python
   from fastapi import UploadFile, File

   @router.post("/upload", dependencies=[Depends(require_role("ADMIN"))])
   async def upload_multimedia(
       file: UploadFile = File(...),
       title: str = Form(...),
       category: str = Form(...),
   ):
       # Validar tipo de archivo
       allowed_types = ["image/jpeg", "image/png", "image/webp", "video/mp4"]
       if file.content_type not in allowed_types:
           raise HTTPException(400, "Tipo de archivo no permitido")

       # Validar tamaño (5MB max)
       contents = await file.read()
       if len(contents) > 5 * 1024 * 1024:
           raise HTTPException(400, "Archivo muy grande (max 5MB)")

       # Upload a Supabase Storage
       storage_service = SupabaseStorageService()
       file_path = f"multimedia/{uuid4()}/{file.filename}"

       url = await storage_service.upload_file(
           bucket="public-multimedia",
           file_path=file_path,
           file_content=contents,
           content_type=file.content_type
       )

       # Crear registro en BD
       multimedia_data = {
           "title": title,
           "type": "image" if "image" in file.content_type else "video",
           "url": url,
           "category": category,
           "size": len(contents),
       }

       # ...
   ```

7. **Implementar endpoints de gestión de eventos**

   **Faltantes:**

   ```python
   # GET /events - Listar eventos (solo admins)
   @router.get("/", dependencies=[Depends(require_role("ADMIN"))])
   async def list_events(
       status: str | None = None,
       skip: int = 0,
       limit: int = 100,
   ):
       pass

   # GET /events/{event_id} - Obtener evento por ID
   @router.get("/{event_id}", dependencies=[Depends(require_role("ADMIN"))])
   async def get_event(event_id: UUID):
       pass

   # PATCH /events/{event_id} - Actualizar estado del evento
   @router.patch("/{event_id}", dependencies=[Depends(require_role("ADMIN"))])
   async def update_event(event_id: UUID, data: EventUpdate):
       pass

   # DELETE /events/{event_id} - Eliminar evento
   @router.delete("/{event_id}", dependencies=[Depends(require_role("ADMIN"))])
   async def delete_event(event_id: UUID):
       pass
   ```

8. **Aprovechar métodos helper de SupabaseClient**

   **Problema:** Los repositorios implementan queries manualmente.

   **Solución:** Refactorizar repositorios para usar métodos del cliente.

   **Ejemplo:**

   ```python
   # multimedia_repository_impl.py - ANTES
   async def get_by_id(self, multimedia_id: UUID) -> Multimedia | None:
       client = await self._supabase_client.client
       response = await client.table(self._table_name).select("*").eq("id", str(multimedia_id)).execute()
       if not response.data or len(response.data) == 0:
           return None
       return Multimedia.model_validate(response.data[0])

   # DESPUÉS
   async def get_by_id(self, multimedia_id: UUID) -> Multimedia | None:
       result = await self._supabase_client.get_by_id(self._table_name, str(multimedia_id))
       if not result:
           return None
       return Multimedia.model_validate(result)
   ```

9. **Implementar auditoría de uso de `admin_client`**

   **Solución:**

   ```python
   # app/infrastructure/external/supabase/client.py

   async def _ensure_admin_client(self) -> AsyncClient:
       """Asegurar que el cliente admin está inicializado"""
       if self._admin_client is None:
           # Log cuando se usa admin client
           import logging
           logger = logging.getLogger(__name__)
           logger.warning(
               "Using admin_client - bypassing RLS",
               extra={"caller": inspect.stack()[2].function}
           )

           self._admin_client = await create_async_client(...)

       return self._admin_client
   ```

10. **Verificar RLS policies en base de datos real**

    **Problema:** Las policies están documentadas pero no verificadas.

    **Acción:** Ejecutar scripts SQL y verificar con:

    ```sql
    -- Ver policies de una tabla
    SELECT * FROM pg_policies WHERE tablename = 'profiles';

    -- Verificar RLS habilitado
    SELECT relname, relrowsecurity
    FROM pg_class
    WHERE relname IN ('profiles', 'eventos', 'multimedia');
    ```

#### **RECOMENDADAS (Prioridad 3):**

11. **Implementar Supabase Realtime**

    **Beneficio:** Notificaciones en tiempo real de cambios en eventos/multimedia.

    **Implementación:**

    ```python
    # app/infrastructure/external/supabase/realtime.py

    async def subscribe_to_events():
        """Suscribirse a cambios en tabla eventos"""
        client = await supabase_client.client

        def on_event_change(payload):
            event_type = payload["eventType"]  # INSERT, UPDATE, DELETE
            new_record = payload.get("new")

            # Emitir a WebSocket o notificar a admins
            print(f"Nuevo evento: {new_record}")

        subscription = client.table("eventos").on("INSERT", on_event_change).subscribe()
        return subscription
    ```

12. **Implementar Edge Functions para lógica compleja**

    **Casos de uso:**

    - Enviar email cuando se crea un evento nuevo
    - Generar thumbnails de imágenes automáticamente
    - Validaciones complejas antes de INSERT

    **Ejemplo:**

    ```typescript
    // supabase/functions/notify-new-event/index.ts

    Deno.serve(async (req) => {
      const { record } = await req.json()

      // Enviar email al admin
      await sendEmail({
        to: "admin@bandangweb.com",
        subject: `Nuevo evento: ${record.name}`,
        body: `Cliente: ${record.email}\nFecha: ${record.event_date}`
      })

      return new Response("OK")
    })
    ```

13. **Cachear resultados frecuentes con Redis**

    **Configuración presente en:** `app/core/config.py` (⚠️ pero no implementado)

    **Implementación sugerida:**

    ```python
    from functools import lru_cache
    from datetime import timedelta

    @lru_cache(maxsize=100)
    async def get_published_multimedia():
        """Cachear multimedia publicado por 5 minutos"""
        # TTL manejado por decorador o Redis
        repository = MultimediaRepositoryImpl()
        return await repository.list_all(is_published=True)
    ```

14. **Rotación de Service Role Key**

    **Implementación:**

    - Crear endpoint admin para rotar key
    - Usar Supabase Management API
    - Notificar a admins cuando se rota

15. **Implementar soft deletes**

    **Beneficio:** Recuperar registros eliminados accidentalmente.

    **Solución:**

    ```python
    # Agregar campo deleted_at a tablas
    deleted_at: datetime | None = None

    # RLS Policy
    CREATE POLICY "Hide deleted records"
    ON public.eventos
    FOR SELECT
    USING (deleted_at IS NULL);
    ```

### 6.2 Oportunidades de Optimización

1. **Índices compuestos para filtros frecuentes**

   ```sql
   -- Multimedia: filtro por publicado + tipo
   CREATE INDEX idx_multimedia_published_type
   ON public.multimedia(is_published, type)
   WHERE is_published = true;

   -- Eventos: filtro por status + fecha
   CREATE INDEX idx_eventos_status_date
   ON public.eventos(status, event_date)
   WHERE status = 'pending';
   ```

2. **Paginación con cursor en lugar de offset**

   **Problema:** `OFFSET` es lento para páginas avanzadas.

   **Solución:**

   ```python
   # Usar cursor basado en ID
   query = client.table("multimedia").select("*").gt("id", last_id).limit(100)
   ```

3. **Reducir queries en get_by_id de usuarios**

   **Solución:** Crear vista SQL que combine `auth.users` y `profiles`.

   ```sql
   CREATE VIEW user_profiles AS
   SELECT
       p.id,
       p.email,
       p.full_name,
       p.role,
       p.is_active,
       p.created_at,
       p.updated_at,
       au.email_confirmed_at,
       au.last_sign_in_at
   FROM public.profiles p
   LEFT JOIN auth.users au ON p.id = au.id;
   ```

### 6.3 Problemas de Seguridad a Resolver

#### **CRÍTICOS:**

1. **Auto-confirmación de email sin verificación** (Línea 195-196 de `supabase_user_repository_impl.py`)

   **Riesgo:** Cualquiera puede registrarse con email falso.

   **Solución:**

   ```python
   # Eliminar auto-confirmación
   # await admin_client.auth.admin.update_user_by_id(
   #     str(user_id), {"email_confirm": True}
   # )

   # Enviar email de confirmación
   # Supabase lo hace automáticamente si no se auto-confirma
   ```

2. **Endpoints de multimedia sin protección** (TODO el archivo `multimedia.py`)

   **Riesgo:** Cualquiera puede crear/modificar/eliminar multimedia.

   **Solución:** Ver recomendación #1.

3. **Mezcla de tokens FastAPI y Supabase** (Ver sección 3.2)

   **Riesgo:** Inconsistencia de estado de autenticación.

   **Solución:** Ver recomendación #3.

#### **IMPORTANTES:**

4. **Sin rate limiting en endpoint de eventos** (Línea 16-27 de `events.py`)

   **Riesgo:** Spam, flood de requests.

   **Solución:** Ver recomendación #5.

5. **Sin validación de roles en RLS policies aplicadas**

   **Riesgo:** Si el código usa `admin_client`, las policies no se verifican.

   **Solución:** Verificar que policies existen en BD y eliminar uso innecesario de `admin_client`.

6. **URLs de multimedia no validadas** (Campo `url` en schema)

   **Riesgo:** URLs maliciosas, phishing.

   **Solución:**

   ```python
   from pydantic import HttpUrl

   class MultimediaCreate(BaseModel):
       url: HttpUrl  # Valida formato de URL
   ```

### 6.4 Features de Supabase No Aprovechadas

1. **❌ Supabase Storage** - No implementado
2. **❌ Supabase Realtime** - No implementado (bandera en config: `SUPABASE_REALTIME_ENABLED=True` pero no usado)
3. **❌ Edge Functions** - No implementado
4. **❌ PostgREST filtering** - No se usan operadores como `ilike`, `fts`, `or`, etc.
5. **❌ Database Webhooks** - No configurados
6. **❌ Auth Providers** (Google, GitHub, etc.) - Solo email/password
7. **❌ Row Level Security con user_metadata** - No se usa metadata de usuario en policies
8. **❌ Supabase Vector** (pgvector) - No se usa para búsqueda semántica
9. **❌ Supabase Extensions** (PostGIS, pg_cron, etc.) - No se mencionan

---

## 7. Estado de Migraciones y Schemas

### 7.1 Archivos de Migración Alembic

**Resultado:**

```bash
$ ls alembic/versions/
(Sin archivos)
```

**⚠️ NO HAY MIGRACIONES DE ALEMBIC.**

**Impacto:**

- Los cambios de schema se hacen manualmente en Supabase SQL Editor
- No hay historial versionado de cambios
- No hay rollback automático
- Dificulta despliegue en múltiples ambientes

**Recomendación:**

Alembic está configurado pero no se usa. Opciones:

1. **Mantener SQL scripts manuales** (actual) - para proyectos Supabase es común
2. **Migrar a Alembic** - si se necesita control de versiones estricto

### 7.2 Sincronización entre Modelos SQLAlchemy y Tablas Supabase

**Búsqueda de modelos SQLAlchemy:**

```bash
$ find app/ -name "models.py" -o -name "*model.py"
(Sin resultados)
```

**❌ NO HAY MODELOS SQLALCHEMY.**

**Arquitectura actual:**

- Usa **Pydantic models** como entidades de dominio (Domain layer)
- Usa **cliente Supabase** directamente (sin ORM)
- Schemas SQL en `scripts/*.sql`

**Ventajas:**

- Menos complejidad (no mantener sincronía ORM <-> BD)
- Más flexible para usar features de PostgreSQL
- Queries más claras con Supabase client

**Desventajas:**

- Sin validación de tipos en tiempo de desarrollo (SQLAlchemy detecta errores)
- Sin migraciones automáticas

### 7.3 Triggers, Policies y Funciones en la Base de Datos

#### **Triggers Documentados:**

| Trigger | Tabla | Función | Propósito |
|---------|-------|---------|-----------|
| `on_auth_user_created` | `auth.users` | `handle_new_user()` | Crear perfil automáticamente |
| `update_profiles_updated_at` | `profiles` | `update_updated_at_column()` | Actualizar timestamp |
| `on_eventos_updated` | `eventos` | `handle_updated_at()` | Actualizar timestamp |
| `update_multimedia_updated_at` | `multimedia` | `update_updated_at_column()` | Actualizar timestamp |

#### **Funciones Documentadas:**

| Función | Parámetros | Retorno | Uso en Código |
|---------|-----------|---------|---------------|
| `handle_new_user()` | - | TRIGGER | ✅ Usado automáticamente |
| `update_updated_at_column()` | - | TRIGGER | ✅ Usado automáticamente |
| `handle_updated_at()` | - | TRIGGER | ✅ Usado automáticamente |
| `get_user_by_email(p_email)` | TEXT | TABLE | ✅ Llamado en repo (línea 95) |
| `user_exists(p_email)` | TEXT | BOOLEAN | ❌ No usado |

#### **Verificación de Trigger `on_auth_user_created`:**

**Código que depende del trigger:** `supabase_user_repository_impl.py:205-212`

```python
# 3. Intentar obtener el perfil, asumiendo que el trigger funcionó.
import asyncio

user = await self.get_by_id(user_id)
if not user:
    await asyncio.sleep(1.5)  # Esperar un poco más por si hay retardo
    user = await self.get_by_id(user_id)

# 4. Si el perfil sigue sin existir, crearlo manualmente.
if not user:
    # Crear perfil manualmente como fallback
    # ...
```

**✅ Excelente:** El código es resiliente ante fallo del trigger.

#### **Policies vs. Código:**

**Discrepancia encontrada:** `docs/database/schema.md` usa `public.users`, pero código usa `public.profiles`.

**Verificación necesaria:** Ejecutar en Supabase SQL Editor:

```sql
-- Ver si existe tabla users o profiles
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'profiles');

-- Ver policies de profiles
SELECT * FROM pg_policies WHERE tablename = 'profiles';
```

---

## 8. Métricas del Proyecto

### 8.1 Estadísticas de Código

| Métrica | Valor |
|---------|-------|
| Total archivos Python en `app/` | 60 |
| Repositorios implementados | 3 |
| Use cases implementados | 2 (auth) + 2 (eventos/multimedia) |
| Endpoints de API | ~15 |
| Entidades de dominio | 3 (SupabaseUser, Event, Multimedia) |
| Usos de `admin_client` | 19 |
| Usos de `client` regular | ~23 |
| Tests de integración | 2 archivos |
| Tests unitarios | ~3 archivos |

### 8.2 Cobertura de Funcionalidades

#### **Autenticación:**

- ✅ Registro con email/password
- ✅ Login con email/password
- ✅ Refresh token
- ✅ Logout (stateless)
- ❌ Confirmación de email (auto-confirmado)
- ❌ Recuperar password
- ❌ Cambiar email
- ❌ OAuth providers (Google, GitHub, etc.)
- ❌ MFA (Multi-factor authentication)

#### **Gestión de Usuarios:**

- ✅ Crear usuario
- ✅ Obtener usuario por ID
- ✅ Obtener usuario por email
- ✅ Listar usuarios con filtros
- ✅ Actualizar usuario
- ✅ Eliminar usuario
- ✅ Cambiar password
- ❌ Suspender/activar usuario (existe campo `is_active` pero no endpoint)
- ❌ Cambiar rol de usuario (existe método pero no endpoint)

#### **Eventos:**

- ✅ Crear evento (público)
- ❌ Listar eventos
- ❌ Obtener evento por ID
- ❌ Actualizar evento
- ❌ Eliminar evento
- ❌ Cambiar status de evento (pending → confirmed/cancelled)
- ❌ Filtrar eventos por fecha/tipo/status

#### **Multimedia:**

- ✅ Crear multimedia (⚠️ público, debería ser admin)
- ✅ Listar multimedia con filtros
- ✅ Obtener multimedia por ID
- ✅ Actualizar multimedia (⚠️ público, debería ser admin)
- ✅ Eliminar multimedia (⚠️ público, debería ser admin)
- ❌ Upload de archivos
- ❌ Generación de thumbnails
- ❌ URLs firmadas temporales

#### **Storage:**

- ❌ Upload de archivos
- ❌ Download de archivos
- ❌ Eliminación de archivos
- ❌ Buckets configurados
- ❌ Policies de acceso

#### **Realtime:**

- ❌ Subscripciones a cambios
- ❌ WebSocket endpoints

### 8.3 Deuda Técnica

#### **Alta prioridad:**

1. Endpoints de multimedia sin autenticación (CRÍTICO)
2. Auto-confirmación de email (CRÍTICO)
3. Mezcla de tokens FastAPI/Supabase (CRÍTICO)
4. Uso excesivo de `admin_client` (ALTO)
5. Sin rate limiting en endpoint público (ALTO)
6. Validación débil de passwords (ALTO)

#### **Media prioridad:**

7. Sin implementación de Storage (MEDIO)
8. Endpoints de eventos faltantes (MEDIO)
9. Sin verificación de RLS policies (MEDIO)
10. Sin migraciones Alembic (MEDIO)
11. Métodos helper no utilizados (MEDIO)

#### **Baja prioridad:**

12. Sin Realtime (BAJO)
13. Sin Edge Functions (BAJO)
14. Sin OAuth providers (BAJO)
15. Sin MFA (BAJO)

---

## 9. Plan de Acción

### 9.1 Fase 1: Correcciones Críticas de Seguridad (1-2 días)

**Objetivo:** Resolver vulnerabilidades de seguridad inmediatas.

#### Tareas:

1. **Proteger endpoints de multimedia**

   - [ ] Agregar `dependencies=[Depends(require_role("ADMIN"))]` a POST, PATCH, DELETE
   - [ ] Mantener GET público solo para `is_published=true`
   - [ ] Archivo: `app/presentation/api/v1/endpoints/multimedia.py`

2. **Eliminar auto-confirmación de email**

   - [ ] Comentar/eliminar líneas 195-196 en `supabase_user_repository_impl.py`
   - [ ] Configurar Supabase para enviar email de confirmación automáticamente
   - [ ] Actualizar documentación

3. **Estandarizar uso de tokens de Supabase**

   - [ ] Eliminar fallback de tokens FastAPI en registro (líneas 122-126)
   - [ ] Modificar endpoint `/refresh` para usar `client.auth.refresh_session()`
   - [ ] Actualizar `get_current_user_id()` para validar tokens de Supabase

4. **Rate limiting en endpoint de eventos**

   - [ ] Agregar `@limiter.limit("5/minute")` a `create_event()`
   - [ ] Considerar CAPTCHA para producción

**Estimación:** 1-2 días
**Impacto:** Alto - mejora significativa en seguridad

### 9.2 Fase 2: Optimización de RLS y Admin Client (2-3 días)

**Objetivo:** Reducir uso innecesario de `admin_client` y verificar RLS policies.

#### Tareas:

1. **Verificar RLS policies en base de datos**

   - [ ] Conectar a Supabase SQL Editor
   - [ ] Ejecutar queries de verificación de policies
   - [ ] Documentar policies realmente aplicadas
   - [ ] Corregir discrepancias (users vs profiles)

2. **Eliminar uso innecesario de admin_client**

   - [ ] `event_repository_impl.py:41` - cambiar a `client`
   - [ ] Evaluar necesidad en `multimedia_repository_impl.py:41,169,216`
   - [ ] Agregar logging de uso de `admin_client` para auditoría

3. **Aprovechar métodos helper de SupabaseClient**

   - [ ] Refactorizar repositorios para usar `get_by_id()`, `create()`, etc.
   - [ ] Eliminar código duplicado
   - [ ] Simplificar queries

**Estimación:** 2-3 días
**Impacto:** Medio - mejora mantenibilidad y seguridad

### 9.3 Fase 3: Implementación de Supabase Storage (3-5 días)

**Objetivo:** Permitir upload de archivos multimedia directamente.

#### Tareas:

1. **Configurar buckets en Supabase**

   - [ ] Crear bucket `public-multimedia` para imágenes/videos
   - [ ] Configurar policies de acceso (admin write, public read)

2. **Implementar SupabaseStorageService**

   - [ ] Crear `app/infrastructure/external/supabase/storage.py`
   - [ ] Métodos: `upload_file()`, `delete_file()`, `get_signed_url()`

3. **Endpoint de upload**

   - [ ] POST `/multimedia/upload` con autenticación ADMIN
   - [ ] Validación de tipo de archivo
   - [ ] Validación de tamaño (5MB max)
   - [ ] Generación automática de thumbnails (opcional)

4. **Migrar multimedia existente**

   - [ ] Script para migrar URLs externas a Storage (si aplica)

**Estimación:** 3-5 días
**Impacto:** Alto - feature importante para CMS de multimedia

### 9.4 Fase 4: Completar CRUD de Eventos (1-2 días)

**Objetivo:** Permitir a admins gestionar eventos desde la API.

#### Tareas:

1. **Implementar métodos en EventRepository**

   - [ ] `get_by_id()`
   - [ ] `list_all()` con filtros (status, fecha, tipo)
   - [ ] `update()`
   - [ ] `delete()`

2. **Crear use cases**

   - [ ] `ListEventsUseCase`
   - [ ] `GetEventUseCase`
   - [ ] `UpdateEventUseCase`
   - [ ] `DeleteEventUseCase`

3. **Endpoints en events.py**

   - [ ] GET `/events` con autenticación ADMIN
   - [ ] GET `/events/{event_id}` con autenticación ADMIN
   - [ ] PATCH `/events/{event_id}` con autenticación ADMIN
   - [ ] DELETE `/events/{event_id}` con autenticación ADMIN

**Estimación:** 1-2 días
**Impacto:** Medio - mejora usabilidad para admins

### 9.5 Fase 5: Mejoras de Validación y UX (2-3 días)

**Objetivo:** Validaciones más robustas y mejor experiencia de usuario.

#### Tareas:

1. **Validación de password con complejidad**

   - [ ] Integrar `validate_password_strength()` en `RegisterUserSupabaseUseCase`
   - [ ] Actualizar tests

2. **Validación de emails con regex completo**

   - [ ] Usar `EmailStr` de Pydantic en todos los schemas
   - [ ] Validar formato completo

3. **Endpoint de recuperar password**

   - [ ] POST `/auth/forgot-password`
   - [ ] Integrar con `client.auth.reset_password_for_email()`

4. **Endpoint de cambiar password del usuario actual**

   - [ ] POST `/auth/change-password`
   - [ ] Requiere autenticación
   - [ ] Verifica password actual antes de cambiar

**Estimación:** 2-3 días
**Impacto:** Medio - mejora UX y seguridad

### 9.6 Fase 6: Features Avanzadas (Opcional, 5-7 días)

**Objetivo:** Aprovechar features avanzadas de Supabase.

#### Tareas:

1. **Supabase Realtime**

   - [ ] Implementar subscripciones a cambios en eventos
   - [ ] WebSocket endpoint para notificaciones en tiempo real
   - [ ] Integración con frontend

2. **Edge Functions**

   - [ ] Función para enviar email cuando se crea evento
   - [ ] Función para generar thumbnails de imágenes
   - [ ] Deploy en Supabase

3. **OAuth Providers**

   - [ ] Configurar Google OAuth en Supabase
   - [ ] Endpoint de login con Google
   - [ ] Sincronizar perfil con metadata de Google

4. **Búsqueda avanzada**

   - [ ] Full-text search en eventos
   - [ ] Función RPC para búsqueda
   - [ ] Endpoint de búsqueda

**Estimación:** 5-7 días
**Impacto:** Bajo-Medio - features "nice to have"

---

## 10. Conclusiones

### 10.1 Estado General de la Integración

**Puntuación: 6.5/10**

**Aspectos positivos:**

- ✅ Arquitectura limpia y bien estructurada
- ✅ Cliente Supabase implementado correctamente
- ✅ Autenticación funcional con Supabase Auth
- ✅ Manejo de errores personalizado
- ✅ Tests mockeados apropiadamente
- ✅ Documentación de schemas SQL completa

**Aspectos negativos:**

- ❌ Uso excesivo de `admin_client` bypaseando RLS
- ❌ Endpoints críticos sin autenticación
- ❌ Storage de Supabase no implementado
- ❌ Auto-confirmación de email sin verificación
- ❌ Mezcla de tokens FastAPI y Supabase
- ❌ Features avanzadas de Supabase desaprovechadas

### 10.2 Recomendación Final

**Priorizar las fases 1 y 2 del plan de acción inmediatamente** para resolver vulnerabilidades críticas de seguridad.

Las fases 3, 4 y 5 deben implementarse según prioridad del negocio:

- **Si el CMS de multimedia es crítico:** Fase 3 primero
- **Si la gestión de eventos es crítica:** Fase 4 primero
- **Si la UX es crítica:** Fase 5 primero

La fase 6 es opcional y puede implementarse gradualmente según necesidades.

### 10.3 Riesgos de No Actuar

**Riesgos críticos:**

1. **Endpoints de multimedia públicos:** Cualquiera puede modificar/eliminar contenido
2. **Auto-confirmación de email:** Cuentas falsas sin verificación
3. **Mezcla de tokens:** Inconsistencia de estado de autenticación
4. **Uso excesivo de admin_client:** RLS policies no se aplican, vulnerabilidades potenciales

**Impacto en producción:**

- Seguridad comprometida
- Spam/abuso en endpoints públicos
- Dificultad para auditar accesos
- Costos innecesarios de almacenamiento (sin Storage de Supabase)

---

**Generado por:** Claude Code
**Fecha:** 2025-10-18
**Versión del reporte:** 1.0

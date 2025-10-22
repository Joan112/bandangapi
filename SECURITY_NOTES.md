# Notas de Seguridad - BandangWeb API

Este documento describe las medidas de seguridad implementadas en la aplicación y las decisiones de diseño relacionadas con la protección contra amenazas comunes.

## Protección CSRF (Cross-Site Request Forgery)

### Endpoints Autenticados (Mayoría)

**TODOS** los endpoints que modifican datos (POST, PUT, PATCH, DELETE) **REQUIEREN** autenticación JWT, excepto el endpoint de creación de eventos.

**Mecanismo de Protección:**
- Los tokens JWT se envían en el header `Authorization: Bearer <token>`
- Los tokens no se pueden leer ni enviar desde otros dominios debido a las políticas CORS restrictivas
- El token JWT actúa como protección CSRF inherente (no es una cookie, es un header custom)

**Endpoints Protegidos con JWT:**
- `/api/v1/supabase/register` - POST
- `/api/v1/supabase/login` - POST
- `/api/v1/supabase/refresh` - POST
- `/api/v1/supabase/logout` - POST (requiere JWT)
- `/api/v1/multimedia/*` - POST, PATCH, DELETE (requieren JWT + rol ADMIN)
- `/api/v1/users/*` - Todos los métodos (requieren JWT + roles apropiados)

**Por qué JWT previene CSRF:**
1. Los tokens JWT se almacenan en `localStorage` o memoria (no en cookies)
2. JavaScript de otro dominio NO puede leer `localStorage` debido a Same-Origin Policy
3. El atacante NO puede obtener el token para incluirlo en el header `Authorization`
4. Los navegadores NO envían headers custom automáticamente en requests cross-origin

### Endpoints Públicos (Excepción)

**Endpoint:** `POST /api/v1/events/` (Creación de eventos para formulario de contacto)

**Protecciones Implementadas:**
1. **Rate Limiting Estricto**: 5 intentos por hora por IP
2. **CORS Restrictivo**: Solo dominios whitelisted pueden hacer requests
3. **Validación Pydantic**: Input estrictamente validado
4. **Estado "Pending"**: Los eventos creados requieren aprobación manual del equipo
5. **Sin Operaciones Críticas**: No modifica datos sensibles ni realiza acciones privilegiadas

**Mitigación de Riesgo CSRF:**
- El atacante puede crear eventos falsos, pero:
  - Limitado a 5 por hora (rate limiting)
  - Solo desde dominios permitidos (CORS)
  - Todos quedan en estado "pending" para revisión
  - No compromete datos existentes ni ejecuta acciones privilegiadas

**Alternativas Consideradas:**
- ✗ **Implementar CSRF Token**: Complicaría formularios públicos sin beneficio significativo
- ✓ **Rate Limiting + Estado Pending**: Solución más simple y efectiva para este caso de uso

### Verificación de Implementación

```bash
# Verificar que endpoints de modificación requieren JWT
grep -r "Depends(require_role\|Depends(get_current_user" app/presentation/api/v1/endpoints/

# Verificar rate limiting en endpoints de auth
grep -r "@limiter.limit" app/presentation/api/v1/endpoints/supabase_auth.py
```

## Rate Limiting por Endpoint

### Endpoints de Autenticación (Críticos)
- `/supabase/register`: **5 intentos/minuto** (prevenir registro masivo)
- `/supabase/login`: **5 intentos/minuto** (prevenir fuerza bruta)
- `/supabase/refresh`: **10 intentos/minuto** (menos crítico que login)
- `/supabase/logout`: **20 intentos/minuto** (operación benigna)

### Endpoints Públicos
- `/events/` (POST): **5 intentos/hora** (formulario de contacto)

### Endpoints Generales
- Límite global: **60 requests/minuto, 1000 requests/hora**

## CORS (Cross-Origin Resource Sharing)

### Dominios Permitidos
```python
cors_origins = [
    "https://bandanuevageneracion.com",
    "https://www.bandanuevageneracion.com",
    "http://localhost:3000",  # Solo en desarrollo
]
```

### Configuración Restrictiva
- **Métodos Permitidos**: GET, POST, PUT, DELETE, PATCH, OPTIONS (NO wildcards)
- **Headers Permitidos**: Content-Type, Authorization, Accept, Origin, X-Requested-With, X-CSRF-Token (NO wildcards)
- **Credentials**: Habilitado (permite cookies/auth headers)
- **Max Age**: 3600 segundos (cache de preflight requests)

### Razón de la Restricción
- Eliminar wildcards (`*`) previene que cualquier dominio pueda hacer requests
- Solo dominios específicos pueden interactuar con la API
- Reduce superficie de ataque para CSRF y otros exploits cross-origin

## Uso de admin_client (Supabase Service Role Key)

El `admin_client` bypassa Row Level Security (RLS) y debe usarse **SOLO** cuando es absolutamente necesario.

### Usos Legítimos Documentados

#### 1. `SupabaseUserRepositoryImpl.get_by_id()`
**Ubicación**: `app/infrastructure/database/repositories/supabase_user_repository_impl.py:56`

**Razón**: Acceso a `auth.users` de Supabase
```python
# Obtener datos de auth.users usando admin_client (NECESARIO - no hay otra forma)
auth_response = await admin_client.auth.admin.get_user_by_id(str(user_id))
```

**Justificación**:
- La tabla `auth.users` de Supabase NO es accesible vía RLS policies
- El único método para obtener datos de autenticación es mediante el admin client
- Necesario para combinar datos de `profiles` (RLS) con `auth.users` (admin)
- El cliente regular se usa para `profiles`, admin solo para `auth.users`

#### 2. `SupabaseUserRepositoryImpl.create_user()` - Crear Perfil Manual
**Ubicación**: `app/infrastructure/database/repositories/supabase_user_repository_impl.py:216`

**Razón**: Fallback si el trigger de base de datos falla
```python
# Si el trigger de auto-creación de perfil falla, crearlo manualmente
insert_response = await admin_client.table("profiles").insert(profile_data).execute()
```

**Justificación**:
- Normalmente un trigger de BD crea el perfil automáticamente
- En caso de fallo del trigger, se crea manualmente como salvaguarda
- Requiere admin_client porque el perfil se crea en nombre de otro usuario (bypass RLS)
- Es una operación excepcional (se loguea como warning)

#### 3. `SupabaseUserRepositoryImpl.create_user()` - Obtener Datos de Auth
**Ubicación**: `app/infrastructure/database/repositories/supabase_user_repository_impl.py:229`

**Razón**: Obtener datos completos de autenticación del usuario recién creado
```python
auth_response = await admin_client.auth.admin.get_user_by_id(str(user_id))
```

**Justificación**: Mismo que #1 - acceso a `auth.users`

### Repositorios que NO Usan admin_client

- **EventRepositoryImpl**: ✓ Solo usa `client` (respeta RLS)
- **MultimediaRepositoryImpl**: ✓ Solo usa `client` (respeta RLS)

### Checklist de Validación

Antes de usar `admin_client`, pregúntate:

- [ ] ¿Es para acceder a `auth.users` de Supabase? (VÁLIDO)
- [ ] ¿Es un fallback crítico para operaciones que deben succeeder? (REVISAR)
- [ ] ¿Puedo lograr lo mismo con `client` y RLS policies? (PREFERIR ESTO)
- [ ] ¿Está documentado por qué se necesita admin_client? (REQUERIDO)

**Regla de Oro**: Si hay duda, usa `client` y deja que RLS maneje los permisos.

## Validación de Input

### Pydantic Schemas
- Todos los inputs de API están validados con Pydantic V2
- Validaciones en `app/presentation/api/v1/schemas/`

### Prevención de Inyecciones
- **SQL Injection**: Prevenido por Supabase/PostgREST (parámetros seguros)
- **XSS**: Input validation + output encoding
- **Path Traversal**: Validación estricta de UUIDs y enums

## Secrets Management

### Variables de Entorno Críticas
```bash
SECRET_KEY=<generado con secrets.token_urlsafe(64)>  # JWT signing
SUPABASE_SERVICE_ROLE_KEY=<solo para admin_client>   # Bypass RLS
SUPABASE_KEY=<anon key para client regular>          # Respeta RLS
```

### Generación de SECRET_KEY
```bash
# Generar un nuevo SECRET_KEY seguro
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Requisitos:**
- Mínimo 32 caracteres (recomendado: 64+)
- Generado criptográficamente (NO strings predecibles)
- Único por ambiente (dev/staging/prod)
- NUNCA commitear en git

## Logging de Seguridad

### Eventos de Seguridad Logueados
- Login exitoso/fallido
- Registro de usuarios
- Cambios de permisos/roles
- Acceso denegado (403)
- Errores de autenticación (401)

### NO Loguear
- Passwords (plaintext o hashed)
- Tokens JWT completos
- API keys
- Datos sensibles de usuarios

### Ejemplo de Logging Correcto
```python
# ✓ Correcto
logger.error(f"Error al obtener usuario por ID {user_id}: {type(e).__name__}")

# ✗ Incorrecto
print(f"Error: {e}")  # Usar logging, no print()
logger.info(f"Password: {password}")  # NUNCA loguear passwords
logger.debug(f"Token: {full_jwt_token}")  # NUNCA loguear tokens completos
```

## Security Headers

Implementados en `SecurityHeadersMiddleware`:

```python
Strict-Transport-Security: max-age=31536000; includeSubDomains  # Force HTTPS
X-Frame-Options: DENY                                           # Prevent clickjacking
X-Content-Type-Options: nosniff                                 # Prevent MIME sniffing
X-XSS-Protection: 1; mode=block                                 # Enable XSS filter
Content-Security-Policy: ...                                     # Restrict resources
Referrer-Policy: strict-origin-when-cross-origin                # Control referer info
Permissions-Policy: geolocation=(), microphone=(), camera=()    # Disable features
```

## Recomendaciones de Despliegue

### Producción
1. ✓ Usar HTTPS (TLS 1.2+)
2. ✓ Generar nuevo SECRET_KEY único
3. ✓ Variables de entorno desde secrets manager (no archivos)
4. ✓ Configurar firewall para limitar acceso a puerto 8080
5. ✓ Monitorear logs de seguridad
6. ✓ Actualizar dependencias regularmente (`poetry update`)

### Monitoreo
- Alertar en múltiples intentos de login fallidos (posible brute force)
- Alertar en rate limit exceeded frecuente (posible DoS)
- Revisar logs de `admin_client` usage periódicamente

## Contacto de Seguridad

Para reportar vulnerabilidades de seguridad:
- **NO** crear issues públicos en GitHub
- Contactar directamente al equipo de desarrollo
- Proporcionar: descripción, pasos para reproducir, impacto estimado

---

**Última actualización**: 2025-10-21
**Revisado por**: Claude Code (Security Guardian Agent)

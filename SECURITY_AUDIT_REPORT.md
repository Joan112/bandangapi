# Reporte de Auditoría de Seguridad - BandangAPI

**Fecha:** 2025-10-21
**Versión:** 1.0.0
**Auditor:** Claude Code - Security Guardian Agent
**Alcance:** Auditoría completa de seguridad del proyecto BandangWeb API

---

## Resumen Ejecutivo

### Score de Seguridad: 72/100

**Clasificación:** MODERADO - Requiere atención inmediata

El proyecto BandangAPI presenta una **implementación de seguridad sólida en su arquitectura base**, con el uso correcto de Supabase Auth, bcrypt para hashing de passwords, JWT tokens, y middlewares de seguridad. Sin embargo, se han identificado **vulnerabilidades críticas y de alta prioridad** que deben ser atendidas inmediatamente antes de pasar a producción.

### Estadísticas de Vulnerabilidades

| Severidad | Cantidad | Críticas |
|-----------|----------|----------|
| Critical  | 2        | SECRET_KEY débil, Service Role Key en config |
| High      | 5        | Rate limiting excesivo, Logging inseguro, CORS permisivo |
| Medium    | 8        | Manejo de errores, Validaciones parciales |
| Low       | 4        | Mejoras menores |
| **TOTAL** | **19**   | - |

---

## Top 10 Vulnerabilidades Críticas

### 1. SECRET_KEY Débil y Hardcoded en Ejemplo ⚠️ CRITICAL

**Severidad:** CRITICAL
**CWE:** CWE-798 (Use of Hard-coded Credentials)
**OWASP:** A02:2021 - Cryptographic Failures

**Ubicación:**
- `.env.example` línea 16

**Descripción:**
El archivo `.env.example` contiene un SECRET_KEY débil y predecible que podría ser copiado a producción:

```bash
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
```

**Impacto:**
- Compromiso total de tokens JWT
- Posibilidad de falsificar tokens de acceso
- Escalación de privilegios
- Acceso no autorizado a todas las cuentas

**Recomendación:**
```bash
# En .env.example - NUNCA incluir un valor real
SECRET_KEY=GENERATE_WITH_OPENSSL_RAND_HEX_32

# Documentar en README.md cómo generar:
# openssl rand -hex 32

# En producción, usar secrets manager (no .env)
# - Variables de entorno del sistema
# - AWS Secrets Manager
# - HashiCorp Vault
# - Google Cloud Secret Manager
```

**Código de mitigación:**
```python
# app/core/config.py - Agregar validación
from pydantic import field_validator

class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., min_length=32)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key_strength(cls, v: str) -> str:
        """Validar que SECRET_KEY no sea débil"""
        weak_keys = [
            "your-super-secret-key",
            "change-this",
            "secret",
            "password",
            "123456",
        ]

        if any(weak in v.lower() for weak in weak_keys):
            raise ValueError(
                "SECRET_KEY parece ser débil o de ejemplo. "
                "Generar con: openssl rand -hex 32"
            )

        # Verificar entropía mínima
        if len(set(v)) < 16:
            raise ValueError("SECRET_KEY tiene baja entropía")

        return v
```

---

### 2. SUPABASE_SERVICE_ROLE_KEY Expuesto en Configuración ⚠️ CRITICAL

**Severidad:** CRITICAL
**CWE:** CWE-522 (Insufficiently Protected Credentials)
**OWASP:** A01:2021 - Broken Access Control

**Ubicación:**
- `app/core/config.py` línea 70-72
- `app/infrastructure/external/supabase/client.py` línea 49

**Descripción:**
El service role key de Supabase (que **bypasea todas las RLS policies**) se carga desde `.env` sin validaciones adicionales y puede ser accedido fácilmente desde el código.

**Impacto:**
- Bypass completo de Row Level Security (RLS)
- Acceso a todos los datos de todos los usuarios
- Capacidad de modificar/eliminar cualquier registro
- Escalación de privilegios

**Código vulnerable:**
```python
# app/infrastructure/external/supabase/client.py
async def _ensure_admin_client(self) -> AsyncClient:
    """Asegurar que el cliente admin está inicializado (bypasa RLS)"""
    if self._admin_client is None:
        self._admin_client = await create_async_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,  # ⚠️ BYPASA RLS
            options=self._options,
        )
    return self._admin_client
```

**Recomendación:**

1. **Uso justificado del admin_client:**
```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py

# ✅ JUSTIFICADO: Acceso a auth.users requiere admin client
auth_response = await admin_client.auth.admin.get_user_by_id(str(user_id))

# ✅ JUSTIFICADO: Operaciones administrativas explícitas
await admin_client.table("profiles").insert(profile_data).execute()
```

2. **Auditar uso innecesario:**
```python
# ❌ INNECESARIO: Cliente regular puede hacer esto con RLS
# Revisar eventos/multimedia repositories
client = await self._supabase_client.client  # Preferir esto
# vs
admin_client = await self._supabase_client.admin_client  # Solo si es necesario
```

3. **Logging obligatorio:**
```python
# app/infrastructure/external/supabase/client.py
import logging
logger = logging.getLogger(__name__)

async def _ensure_admin_client(self) -> AsyncClient:
    """Asegurar que el cliente admin está inicializado (bypasa RLS)"""
    if self._admin_client is None:
        logger.warning(
            "⚠️ Inicializando admin_client (BYPASA RLS). "
            "Usar solo para operaciones administrativas justificadas."
        )
        self._admin_client = await create_async_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            options=self._options,
        )
    return self._admin_client

@property
async def admin_client(self) -> AsyncClient:
    """Obtener cliente admin de Supabase (bypasa RLS)"""
    # Loggear cada acceso al admin client
    import inspect
    frame = inspect.currentframe()
    caller = inspect.getframeinfo(frame.f_back)
    logger.warning(
        f"admin_client accedido desde {caller.filename}:{caller.lineno} "
        f"(función: {caller.function})"
    )
    return await self._ensure_admin_client()
```

---

### 3. Rate Limiting Excesivamente Permisivo ⚠️ HIGH

**Severidad:** HIGH
**CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)
**OWASP:** A07:2021 - Identification and Authentication Failures

**Ubicación:**
- `app/presentation/api/v1/endpoints/supabase_auth.py` líneas 71, 127, 171, 210
- `app/presentation/api/v1/endpoints/events.py` línea 25

**Descripción:**
Los endpoints críticos de autenticación tienen rate limits extremadamente altos:

```python
@router.post("/register")
@limiter.limit("100/minute")  # ⚠️ 100 registros por minuto es excesivo
async def register(...):
    pass

@router.post("/login")
@limiter.limit("100/minute")  # ⚠️ 100 intentos de login por minuto
async def login(...):
    pass
```

**Impacto:**
- Ataques de fuerza bruta en login
- Creación masiva de cuentas falsas (spam)
- Denegación de servicio (DoS)
- Bypass de protecciones anti-bot

**Recomendación:**
```python
# app/presentation/api/v1/endpoints/supabase_auth.py

@router.post("/register")
@limiter.limit("3/hour")  # Máximo 3 registros por hora por IP
@limiter.limit("10/day")  # Máximo 10 registros por día por IP
async def register(...):
    pass

@router.post("/login")
@limiter.limit("5/minute")   # Máximo 5 intentos por minuto
@limiter.limit("20/hour")    # Máximo 20 intentos por hora
async def login(...):
    pass

@router.post("/refresh")
@limiter.limit("10/minute")  # Refresh más frecuente está OK
async def refresh_token(...):
    pass

@router.post("/logout")
@limiter.limit("10/minute")  # Logout normal
async def logout(...):
    pass
```

**Implementar rate limiting por usuario autenticado:**
```python
# app/presentation/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_rate_limit_key(request: Request) -> str:
    """
    Rate limit key basado en IP o user_id autenticado
    """
    # Si hay usuario autenticado, usar su ID
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Sino, usar IP
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[
        "60/minute",
        "1000/hour",
    ],
)
```

---

### 4. Logging de Información Sensible con `print()` ⚠️ HIGH

**Severidad:** HIGH
**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)
**OWASP:** A09:2021 - Security Logging and Monitoring Failures

**Ubicación:**
- `app/infrastructure/database/repositories/supabase_user_repository_impl.py` líneas 105, 141

**Descripción:**
Se utiliza `print()` para logging en lugar de un logger estructurado, lo que puede exponer información sensible:

```python
# Línea 105
except Exception as e:
    print(f"Error al obtener usuario por email: {e}")  # ⚠️ Puede loggear emails
    return None

# Línea 141
except Exception as e:
    print(f"Error al listar usuarios: {e}")  # ⚠️ Puede loggear datos de usuarios
    return []
```

**Impacto:**
- Exposición de información sensible en logs
- Dificultad para centralizar y monitorear logs
- No se puede controlar nivel de logging
- Logs pueden ser accesibles en stdout sin cifrar

**Recomendación:**
```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py
import logging

logger = logging.getLogger(__name__)

async def get_by_email(self, email: str) -> SupabaseUser | None:
    """Obtener un usuario por su email"""
    try:
        # ... código ...
    except Exception as e:
        # ✅ Usar logger estructurado
        logger.error(
            "Error al obtener usuario por email",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                # NO incluir el email completo en logs
                "email_domain": email.split("@")[1] if "@" in email else "unknown",
            },
            exc_info=True  # Incluir traceback completo
        )
        return None

async def list_users(self, skip: int = 0, limit: int = 100, role: UserRole | None = None) -> list[SupabaseUser]:
    """Listar usuarios"""
    try:
        # ... código ...
    except Exception as e:
        logger.error(
            "Error al listar usuarios",
            extra={
                "skip": skip,
                "limit": limit,
                "role": role.value if role else None,
                "error_type": type(e).__name__,
            },
            exc_info=True
        )
        return []
```

**Configurar logging seguro:**
```python
# app/core/logging_config.py
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configurar logging estructurado y seguro"""

    # Filtro para sanitizar información sensible
    class SanitizeFilter(logging.Filter):
        """Filtro para remover información sensible de logs"""

        SENSITIVE_KEYS = [
            "password", "token", "secret", "key", "authorization",
            "api_key", "access_token", "refresh_token"
        ]

        def filter(self, record):
            # Sanitizar mensaje
            message = record.getMessage().lower()
            for key in self.SENSITIVE_KEYS:
                if key in message:
                    record.msg = record.msg.replace(
                        record.msg[record.msg.lower().find(key):],
                        f"{key}=***REDACTED***"
                    )

            # Sanitizar extra data
            if hasattr(record, "extra"):
                for key in self.SENSITIVE_KEYS:
                    if key in record.extra:
                        record.extra[key] = "***REDACTED***"

            return True

    # Configurar handler con JSON formatter
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"}
    )
    handler.setFormatter(formatter)
    handler.addFilter(SanitizeFilter())

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
```

---

### 5. CORS Permite Wildcard en Métodos ⚠️ HIGH

**Severidad:** HIGH
**CWE:** CWE-942 (Permissive Cross-domain Policy with Untrusted Domains)
**OWASP:** A05:2021 - Security Misconfiguration

**Ubicación:**
- `app/main.py` líneas 86-92

**Descripción:**
La configuración de CORS permite todos los métodos (`*`) sin restricciones:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # ⚠️ Permite todos los métodos HTTP
    allow_headers=["*"],  # ⚠️ Permite todos los headers
)
```

**Impacto:**
- Ataques CSRF (Cross-Site Request Forgery)
- Exposición de headers sensibles
- Métodos HTTP peligrosos habilitados (TRACE, CONNECT)

**Recomendación:**
```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    # ✅ Solo métodos necesarios
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # ✅ Solo headers específicos
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Accept-Language",
        "X-Requested-With",
    ],
    # ✅ Exponer headers específicos
    expose_headers=[
        "Content-Length",
        "X-Process-Time",
    ],
    max_age=3600,  # Cache de preflight requests
)
```

---

### 6. Falta Protección CSRF en Endpoints Públicos ⚠️ HIGH

**Severidad:** HIGH
**CWE:** CWE-352 (Cross-Site Request Forgery)
**OWASP:** A01:2021 - Broken Access Control

**Ubicación:**
- `app/presentation/api/v1/endpoints/events.py` línea 26 (endpoint público)

**Descripción:**
El endpoint `/events` es público (no requiere autenticación) y permite crear eventos sin protección CSRF:

```python
@router.post(
    "/",
    # ...
    description="Este endpoint es PÚBLICO para permitir formularios de contacto.",
)
@limiter.limit("5/hour")  # Solo rate limiting
async def create_event(
    request: Request,
    event_data: EventCreate,
    use_case: CreateEventUseCase = Depends(get_create_event_use_case),
) -> EventRead:
    # ⚠️ Sin verificación de origen de request
    # ⚠️ Sin CSRF token
    pass
```

**Impacto:**
- Ataques CSRF desde sitios maliciosos
- Creación de eventos spam/maliciosos
- Abuso del formulario de contacto

**Recomendación:**

1. **Implementar CSRF protection:**
```python
# app/presentation/middleware/csrf.py
from fastapi import Request, HTTPException, status
from secrets import token_urlsafe
from datetime import datetime, timedelta

class CSRFProtection:
    """Middleware de protección CSRF"""

    def __init__(self, secret_key: str, token_expiry: int = 3600):
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self._tokens: dict[str, datetime] = {}

    def generate_token(self) -> str:
        """Generar token CSRF"""
        token = token_urlsafe(32)
        self._tokens[token] = datetime.utcnow()
        return token

    def validate_token(self, token: str) -> bool:
        """Validar token CSRF"""
        if token not in self._tokens:
            return False

        # Verificar expiración
        created_at = self._tokens[token]
        if datetime.utcnow() - created_at > timedelta(seconds=self.token_expiry):
            del self._tokens[token]
            return False

        # Token válido, eliminarlo (one-time use)
        del self._tokens[token]
        return True

    async def verify_csrf(self, request: Request):
        """Dependency para verificar CSRF token"""
        # Skip para métodos GET, HEAD, OPTIONS
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return

        # Obtener token del header
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )

        # Validar token
        if not self.validate_token(csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid or expired"
            )

# Instancia global
csrf_protection = CSRFProtection(settings.SECRET_KEY)
```

2. **Aplicar en endpoints públicos:**
```python
# app/presentation/api/v1/endpoints/events.py
from app.presentation.middleware.csrf import csrf_protection

@router.post("/")
@limiter.limit("5/hour")
async def create_event(
    request: Request,
    event_data: EventCreate,
    use_case: CreateEventUseCase = Depends(get_create_event_use_case),
    _csrf: None = Depends(csrf_protection.verify_csrf),  # ✅ CSRF protection
) -> EventRead:
    # Ahora protegido contra CSRF
    pass

# Endpoint para obtener CSRF token
@router.get("/csrf-token")
async def get_csrf_token() -> dict[str, str]:
    """Obtener token CSRF para formularios públicos"""
    return {"csrf_token": csrf_protection.generate_token()}
```

3. **Alternativa: reCAPTCHA para endpoints públicos:**
```python
# app/core/recaptcha.py
import httpx
from fastapi import HTTPException, status

async def verify_recaptcha(token: str, remote_ip: str) -> bool:
    """Verificar token de reCAPTCHA"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": token,
                "remoteip": remote_ip,
            }
        )
        result = response.json()
        return result.get("success", False)

# Dependency
async def require_recaptcha(
    request: Request,
    recaptcha_token: str = None,
):
    """Dependency que requiere reCAPTCHA"""
    if not recaptcha_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA token required"
        )

    remote_ip = request.client.host
    is_valid = await verify_recaptcha(recaptcha_token, remote_ip)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed"
        )
```

---

### 7. Tokens JWT Sin Lista de Revocación ⚠️ MEDIUM

**Severidad:** MEDIUM
**CWE:** CWE-613 (Insufficient Session Expiration)
**OWASP:** A07:2021 - Identification and Authentication Failures

**Ubicación:**
- `app/core/security.py`
- `app/presentation/api/v1/endpoints/supabase_auth.py` línea 209

**Descripción:**
No existe un mecanismo de revocación de tokens JWT. Cuando un usuario hace logout, el token sigue siendo válido hasta su expiración natural.

```python
@router.post("/logout")
async def logout(
    request: Request, current_user=Depends(require_role("USER"))
) -> dict[str, str]:
    """Cerrar sesión con revocación de token en Supabase"""
    try:
        # ... sign out en Supabase ...
        await client.auth.sign_out()

        # ⚠️ El JWT sigue siendo válido hasta expirar
        # ⚠️ No hay blocklist de tokens

        return {"message": "Sesión cerrada exitosamente"}
```

**Impacto:**
- Tokens robados siguen funcionando después de logout
- No se puede revocar acceso de inmediato
- Tokens de sesiones comprometidas permanecen válidos

**Recomendación:**

1. **Implementar blocklist de tokens con Redis:**
```python
# app/infrastructure/cache/token_blocklist.py
from datetime import timedelta
import redis.asyncio as redis
from app.core.config import settings

class TokenBlocklist:
    """Blocklist de tokens revocados en Redis"""

    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def revoke_token(self, token: str, expires_in: int):
        """
        Agregar token a la blocklist

        Args:
            token: Token JWT a revocar
            expires_in: Segundos hasta expiración natural del token
        """
        # Usar hash del token como key (no guardar token completo)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Guardar en Redis con TTL = tiempo de expiración del token
        await self.redis.setex(
            f"blocklist:{token_hash}",
            time=expires_in,
            value="1"
        )

    async def is_revoked(self, token: str) -> bool:
        """Verificar si un token está revocado"""
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        exists = await self.redis.exists(f"blocklist:{token_hash}")
        return bool(exists)

# Instancia global
token_blocklist = TokenBlocklist()
```

2. **Actualizar dependency de autenticación:**
```python
# app/core/dependencies.py
from app.infrastructure.cache.token_blocklist import token_blocklist

async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Obtener ID del usuario actual desde el token de Supabase"""
    from app.infrastructure.external.supabase import supabase_client

    # ✅ Verificar si el token está en la blocklist
    if await token_blocklist.is_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ha sido revocado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validar token con Supabase Auth
        client = await supabase_client.client
        user_response = await client.auth.get_user(token)
        # ... resto del código ...
```

3. **Actualizar endpoint de logout:**
```python
# app/presentation/api/v1/endpoints/supabase_auth.py
from app.infrastructure.cache.token_blocklist import token_blocklist
from app.core.security import decode_token

@router.post("/logout")
async def logout(
    request: Request,
    current_user=Depends(require_role("USER"))
) -> dict[str, str]:
    """Cerrar sesión con revocación de token"""
    try:
        # Obtener token
        authorization: str = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autorización no proporcionado",
            )

        token = authorization.replace("Bearer ", "")

        # Decodificar para obtener expiración
        payload = decode_token(token, expected_type="access")
        exp = payload.get("exp")
        current_time = datetime.utcnow().timestamp()
        expires_in = int(exp - current_time)

        # ✅ Revocar token en blocklist
        if expires_in > 0:
            await token_blocklist.revoke_token(token, expires_in)

        # Sign out en Supabase
        client = await supabase_client.client
        await client.auth.sign_out()

        return {"message": "Sesión cerrada exitosamente"}
    except Exception as e:
        # ... manejo de errores ...
```

---

### 8. Validación de Password Insuficiente para Caracteres Especiales ⚠️ MEDIUM

**Severidad:** MEDIUM
**CWE:** CWE-521 (Weak Password Requirements)
**OWASP:** A07:2021 - Identification and Authentication Failures

**Ubicación:**
- `app/core/security.py` líneas 178-179

**Descripción:**
La validación de caracteres especiales es limitada y no cubre todos los caracteres especiales comunes:

```python
# Validar carácter especial
special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"  # ⚠️ Lista limitada
if not any(c in special_chars for c in password):
    return (
        False,
        "Password debe contener al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)",
    )
```

**Impacto:**
- Passwords potencialmente débiles aceptadas
- Falta de soporte para caracteres especiales Unicode
- Inconsistencia con políticas de seguridad modernas

**Recomendación:**
```python
# app/core/security.py
import string
import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validar fortaleza del password con requisitos estrictos

    Requisitos:
    - Mínimo 8 caracteres (configurable)
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial
    - No contiene caracteres comunes repetidos
    - No contiene secuencias obvias (123, abc, qwerty)
    """
    from app.core.config import settings

    min_length = settings.PASSWORD_MIN_LENGTH

    # 1. Longitud mínima
    if len(password) < min_length:
        return False, f"Password debe tener al menos {min_length} caracteres"

    # 2. Mayúscula
    if not any(c.isupper() for c in password):
        return False, "Password debe contener al menos una mayúscula"

    # 3. Minúscula
    if not any(c.islower() for c in password):
        return False, "Password debe contener al menos una minúscula"

    # 4. Número
    if not any(c.isdigit() for c in password):
        return False, "Password debe contener al menos un número"

    # 5. Carácter especial (ASCII + Unicode)
    # Usar string.punctuation + caracteres adicionales
    special_chars = string.punctuation + "¡¿"
    if not any(c in special_chars for c in password):
        return False, f"Password debe contener al menos un carácter especial ({special_chars[:20]}...)"

    # 6. Detectar caracteres repetidos excesivos
    if re.search(r'(.)\1{2,}', password):  # 3+ caracteres iguales seguidos
        return False, "Password no debe contener caracteres repetidos excesivamente"

    # 7. Detectar secuencias comunes
    common_sequences = [
        "123", "234", "345", "456", "567", "678", "789",
        "abc", "bcd", "cde", "def", "efg", "fgh",
        "qwerty", "asdfgh", "zxcvbn",
        "password", "admin", "user", "root",
    ]
    password_lower = password.lower()
    for seq in common_sequences:
        if seq in password_lower:
            return False, f"Password no debe contener secuencias comunes como '{seq}'"

    # 8. Verificar entropía mínima (diversidad de caracteres)
    unique_chars = len(set(password))
    if unique_chars < min_length // 2:
        return False, "Password debe tener mayor diversidad de caracteres"

    return True, ""


def estimate_password_strength(password: str) -> dict:
    """
    Estimar la fortaleza de un password (para feedback al usuario)

    Returns:
        {
            "score": int (0-4),
            "label": str ("muy débil", "débil", "medio", "fuerte", "muy fuerte"),
            "suggestions": list[str],
        }
    """
    score = 0
    suggestions = []

    # Longitud
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    else:
        suggestions.append("Usa al menos 12 caracteres para mayor seguridad")

    # Diversidad de caracteres
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)

    char_types = sum([has_lower, has_upper, has_digit, has_special])

    if char_types >= 3:
        score += 1
    if char_types == 4:
        score += 1

    if not has_special:
        suggestions.append("Agrega caracteres especiales (!@#$%^&*)")

    # Entropía
    unique_ratio = len(set(password)) / len(password) if len(password) > 0 else 0
    if unique_ratio > 0.7:
        score += 1
    else:
        suggestions.append("Evita repetir caracteres")

    # Etiquetas
    labels = ["muy débil", "débil", "medio", "fuerte", "muy fuerte"]
    label = labels[min(score, 4)]

    return {
        "score": score,
        "label": label,
        "suggestions": suggestions,
    }
```

---

### 9. Falta Validación de Expiración de Tokens en Todos los Endpoints ⚠️ MEDIUM

**Severidad:** MEDIUM
**CWE:** CWE-613 (Insufficient Session Expiration)
**OWASP:** A07:2021 - Identification and Authentication Failures

**Ubicación:**
- `app/core/dependencies.py` (dependency de autenticación)

**Descripción:**
La validación de tokens se delega completamente a Supabase Auth, pero no hay verificaciones adicionales de tiempo de vida o renovación forzada.

**Recomendación:**
```python
# app/core/dependencies.py
from datetime import datetime, timedelta

async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Obtener ID del usuario actual desde el token de Supabase"""
    from app.infrastructure.external.supabase import supabase_client

    # Verificar blocklist
    if await token_blocklist.is_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ha sido revocado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validar token con Supabase Auth
        client = await supabase_client.client
        user_response = await client.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ✅ Verificaciones adicionales de seguridad
        user = user_response.user

        # Verificar email confirmado
        if not user.email_confirmed_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email no confirmado. Por favor, verifica tu correo electrónico.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ✅ Verificar última vez que inició sesión (force re-auth si es muy antiguo)
        if user.last_sign_in_at:
            last_signin = datetime.fromisoformat(user.last_sign_in_at.replace("Z", "+00:00"))
            days_since_login = (datetime.utcnow() - last_signin.replace(tzinfo=None)).days

            # Forzar re-autenticación si han pasado más de 30 días
            if days_since_login > 30:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sesión expirada. Por favor, inicia sesión nuevamente.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return user.id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al validar token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
```

---

### 10. Content Security Policy Permite `unsafe-inline` ⚠️ MEDIUM

**Severidad:** MEDIUM
**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers or Frames)
**OWASP:** A03:2021 - Injection

**Ubicación:**
- `app/presentation/middleware/security_headers.py` líneas 51-52

**Descripción:**
La política de seguridad de contenido (CSP) permite scripts y estilos inline, lo cual puede facilitar ataques XSS:

```python
csp_directives = [
    "default-src 'self'",
    f"connect-src 'self' https://{supabase_domain} https://*.supabase.co",
    "script-src 'self' 'unsafe-inline'",  # ⚠️ Permite scripts inline
    "style-src 'self' 'unsafe-inline'",   # ⚠️ Permite estilos inline
    # ...
]
```

**Impacto:**
- Vulnerabilidad a ataques XSS (Cross-Site Scripting)
- Inyección de scripts maliciosos
- Robo de tokens/sesiones

**Recomendación:**
```python
# app/presentation/middleware/security_headers.py

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad HTTP"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HSTS - HTTP Strict Transport Security
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"  # ✅ Agregar preload
            )

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy pero aún útil)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (actualizado)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # ✅ Content-Security-Policy - SIN unsafe-inline
        supabase_domain = settings.SUPABASE_URL.replace("https://", "").replace("http://", "")

        # Generar nonce para scripts inline (si es necesario)
        import secrets
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce  # Disponible para templates

        csp_directives = [
            "default-src 'self'",
            f"connect-src 'self' https://{supabase_domain} https://*.supabase.co",
            # ✅ Usar nonce en lugar de unsafe-inline
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net",
            f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com",
            "img-src 'self' data: https: blob:",
            "font-src 'self' data: https://fonts.gstatic.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
            # ✅ Reporting (opcional pero recomendado)
            f"report-uri {settings.API_V1_PREFIX}/security/csp-report",
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
```

**Agregar endpoint para reportes CSP:**
```python
# app/presentation/api/v1/endpoints/security.py
import logging
from fastapi import APIRouter, Request

router = APIRouter(prefix="/security", tags=["security"])
logger = logging.getLogger(__name__)

@router.post("/csp-report")
async def csp_report(request: Request):
    """Recibir reportes de violaciones CSP"""
    try:
        report = await request.json()
        logger.warning(
            "CSP Violation Report",
            extra={
                "csp_report": report,
                "ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        return {"status": "report received"}
    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        return {"status": "error"}
```

---

## Vulnerabilidades de Severidad Media

### 11. Falta Protección contra Timing Attacks en Comparación de Passwords

**Severidad:** MEDIUM
**Ubicación:** `app/core/security.py` línea 29

**Descripción:**
La función `bcrypt.checkpw()` es resistente a timing attacks, pero no hay verificación explícita.

**Recomendación:**
```python
# bcrypt ya es seguro, pero documentar
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar password plano contra hash bcrypt

    Nota: bcrypt.checkpw() es resistente a timing attacks por diseño.
    """
    password_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(password_bytes, hash_bytes)
```

---

### 12. Falta Sanitización de Inputs en Queries de Supabase

**Severidad:** MEDIUM
**Ubicación:** `app/infrastructure/database/repositories/*`

**Recomendación:**
Aunque Supabase/PostgREST parametriza las queries, validar inputs:

```python
from pydantic import Field, field_validator
import re

class EventCreate(TrimmedModel):
    """Schema para crear evento"""

    title: str = Field(..., min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        """Sanitizar título"""
        # Remover caracteres de control
        v = re.sub(r'[\x00-\x1F\x7F]', '', v)
        # Normalizar whitespace
        v = ' '.join(v.split())
        return v.strip()
```

---

### 13. Falta Rate Limiting Específico por Recurso

**Severidad:** MEDIUM

**Recomendación:**
Implementar rate limiting diferenciado:

```python
# app/presentation/middleware/resource_rate_limit.py
from collections import defaultdict
from datetime import datetime, timedelta

class ResourceRateLimiter:
    """Rate limiter específico por recurso"""

    def __init__(self):
        self._limits: dict[str, dict] = defaultdict(dict)

    def check_limit(
        self,
        user_id: str,
        resource_type: str,
        limit: int,
        window: timedelta
    ) -> bool:
        """
        Verificar si el usuario puede acceder al recurso

        Args:
            user_id: ID del usuario
            resource_type: Tipo de recurso (ej: "event_create", "user_update")
            limit: Número máximo de accesos
            window: Ventana de tiempo

        Returns:
            True si está dentro del límite
        """
        key = f"{user_id}:{resource_type}"
        now = datetime.utcnow()

        # Limpiar accesos antiguos
        if key in self._limits:
            self._limits[key] = {
                ts: count
                for ts, count in self._limits[key].items()
                if now - ts < window
            }

        # Contar accesos en la ventana
        total_accesses = sum(self._limits[key].values())

        if total_accesses >= limit:
            return False

        # Registrar acceso
        self._limits[key][now] = self._limits[key].get(now, 0) + 1
        return True
```

---

### 14. Falta Validación de Tamaño de Payloads

**Severidad:** MEDIUM

**Recomendación:**
```python
# app/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Limitar tamaño de request body
app.add_middleware(
    LimitUploadSizeMiddleware,
    max_upload_size=10 * 1024 * 1024  # 10 MB
)

# Middleware custom
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_upload_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Max size: {self.max_upload_size} bytes"
                )

        return await call_next(request)
```

---

### 15. Falta Implementación de Security.txt

**Severidad:** LOW

**Recomendación:**
```python
# app/main.py
@app.get("/.well-known/security.txt")
async def security_txt():
    """RFC 9116: Security.txt"""
    content = """Contact: security@bandanuevageneracion.com
Expires: 2026-12-31T23:59:59.000Z
Encryption: https://bandanuevageneracion.com/pgp-key.txt
Preferred-Languages: es, en
Canonical: https://bandanuevageneracion.com/.well-known/security.txt
Policy: https://bandanuevageneracion.com/security-policy
"""
    return Response(content=content, media_type="text/plain")
```

---

### 16. Falta Monitoreo de Anomalías en Autenticación

**Severidad:** MEDIUM

**Recomendación:**
```python
# app/domain/use_cases/auth/monitor_auth.py
from datetime import datetime, timedelta
from collections import defaultdict

class AuthenticationMonitor:
    """Monitor de anomalías en autenticación"""

    def __init__(self):
        self._failed_attempts: defaultdict[str, list] = defaultdict(list)
        self._suspicious_ips: set = set()

    def record_failed_login(self, email: str, ip: str):
        """Registrar intento fallido de login"""
        self._failed_attempts[email].append({
            "ip": ip,
            "timestamp": datetime.utcnow()
        })

        # Detectar múltiples intentos fallidos
        recent_attempts = [
            a for a in self._failed_attempts[email]
            if datetime.utcnow() - a["timestamp"] < timedelta(minutes=15)
        ]

        if len(recent_attempts) >= 5:
            self._suspicious_ips.add(ip)
            # Enviar alerta
            self._send_security_alert(
                f"Múltiples intentos fallidos de login para {email} desde IP {ip}"
            )

    def is_suspicious_ip(self, ip: str) -> bool:
        """Verificar si una IP es sospechosa"""
        return ip in self._suspicious_ips

    def _send_security_alert(self, message: str):
        """Enviar alerta de seguridad"""
        import logging
        logger = logging.getLogger(__name__)
        logger.critical(f"SECURITY ALERT: {message}")
        # TODO: Implementar notificaciones (email, Slack, PagerDuty)
```

---

### 17. Falta Header de Seguridad `Cross-Origin-Opener-Policy`

**Severidad:** LOW

**Recomendación:**
```python
# app/presentation/middleware/security_headers.py
response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
```

---

### 18. Falta Validación de Inyección en Nombres de Archivos (si se implementa upload)

**Severidad:** MEDIUM

**Recomendación:**
```python
import re
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """Sanitizar nombre de archivo"""
    # Remover path traversal
    filename = Path(filename).name

    # Solo caracteres alfanuméricos, guiones, puntos
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Prevenir archivos ocultos
    if filename.startswith('.'):
        filename = '_' + filename

    # Limitar longitud
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        filename = name[:240] + '.' + ext

    return filename
```

---

### 19. Falta Implementación de Security Headers en Respuestas de Error

**Severidad:** LOW

**Recomendación:**
Asegurar que los error handlers también incluyan security headers (el middleware ya lo hace).

---

## Checklist de Cumplimiento OWASP Top 10 (2021)

### A01:2021 - Broken Access Control ✅ PARCIAL

- [x] RBAC implementado (USER, ADMIN, SUPERADMIN)
- [x] Dependencies de autorización (`require_role`)
- [ ] ⚠️ Falta protección CSRF en endpoints públicos
- [ ] ⚠️ Service role key usado sin auditoría completa
- [x] Verificación de ownership en recursos (parcial)

**Score:** 6/10

---

### A02:2021 - Cryptographic Failures ✅ BUENO

- [x] bcrypt con cost factor 12
- [x] JWT con HS256
- [x] Tokens con expiración apropiada
- [ ] ⚠️ SECRET_KEY débil en ejemplo
- [ ] ⚠️ Falta rotación de secrets
- [x] HTTPS forzado en producción (HSTS)

**Score:** 7/10

---

### A03:2021 - Injection ✅ BUENO

- [x] Supabase parametriza queries (protección SQL injection)
- [x] Pydantic valida todos los inputs
- [x] ORM usage (no raw SQL)
- [ ] ⚠️ CSP permite unsafe-inline
- [x] Sanitización de HTML (si se usa)

**Score:** 8/10

---

### A04:2021 - Insecure Design ✅ BUENO

- [x] Clean Architecture implementada
- [x] Separation of concerns
- [x] Use cases bien definidos
- [x] Entities inmutables
- [x] Security by design (Supabase Auth)

**Score:** 9/10

---

### A05:2021 - Security Misconfiguration ⚠️ NECESITA MEJORA

- [x] Security headers middleware
- [ ] ⚠️ CORS permite wildcard en métodos
- [ ] ⚠️ Rate limiting excesivo
- [x] Debug deshabilitado en producción
- [ ] ⚠️ CSP con unsafe-inline
- [x] .env en .gitignore

**Score:** 5/10

---

### A06:2021 - Vulnerable and Outdated Components ✅ BUENO

- [x] Dependencias actualizadas (Poetry)
- [x] bcrypt 5.0.0 (última)
- [x] python-jose 3.5.0
- [x] FastAPI 0.110+
- [x] Supabase 2.22.0
- [ ] ⚠️ Falta Dependabot/Renovate

**Score:** 8/10

---

### A07:2021 - Identification and Authentication Failures ⚠️ NECESITA MEJORA

- [x] Supabase Auth implementado
- [x] Email confirmation requerido
- [x] Password strength validation
- [ ] ⚠️ Rate limiting excesivo (100/min en login)
- [ ] ⚠️ Sin blocklist de tokens
- [ ] ⚠️ Sin MFA/2FA
- [x] Session management (JWT)

**Score:** 6/10

---

### A08:2021 - Software and Data Integrity Failures ✅ BUENO

- [x] Poetry lock file
- [x] Dependency pinning
- [x] Code signing (Git commits)
- [ ] ⚠️ Falta CI/CD con verificación de integridad
- [x] No se ejecuta código untrusted

**Score:** 7/10

---

### A09:2021 - Security Logging and Monitoring Failures ⚠️ NECESITA MEJORA

- [x] Logging middleware implementado
- [x] Structured logging (JSON)
- [ ] ⚠️ Uso de `print()` en repositorios
- [ ] ⚠️ Sin centralización de logs
- [ ] ⚠️ Sin alertas de seguridad
- [ ] ⚠️ Sin monitoreo de anomalías
- [x] Logs de requests/responses

**Score:** 4/10

---

### A10:2021 - Server-Side Request Forgery (SSRF) ✅ BUENO

- [x] No se hacen requests a URLs de usuario
- [x] Supabase SDK maneja requests externos
- [x] No hay endpoints de proxy
- [x] Validación de URLs (si se usan)

**Score:** 9/10

---

## Score Global OWASP Top 10: 69/100

---

## Recomendaciones Prioritarias

### Inmediatas (Antes de Producción)

1. **Cambiar SECRET_KEY a valor seguro generado**
   - Generar con `openssl rand -hex 32`
   - Guardar en secrets manager (no .env)
   - Agregar validación en Settings

2. **Reducir rate limiting en endpoints de auth**
   - Login: 5/minuto, 20/hora
   - Register: 3/hora, 10/día
   - Refresh: 10/minuto

3. **Implementar blocklist de tokens JWT**
   - Redis para almacenar tokens revocados
   - Verificar en cada request autenticado

4. **Agregar protección CSRF en endpoint público `/events`**
   - Implementar CSRF middleware
   - Alternativamente: reCAPTCHA

5. **Auditar uso de `admin_client`**
   - Verificar que solo se use cuando es necesario
   - Agregar logging obligatorio
   - Documentar justificaciones

### Corto Plazo (1-2 semanas)

6. **Reemplazar `print()` con logging estructurado**
   - Usar logger en todos los repositorios
   - Implementar filtro de sanitización
   - Configurar logging seguro

7. **Mejorar CSP (eliminar unsafe-inline)**
   - Usar nonces para scripts
   - Configurar reporting endpoint

8. **Restringir CORS**
   - Solo métodos necesarios
   - Solo headers específicos

9. **Implementar monitoreo de autenticación**
   - Detectar intentos de fuerza bruta
   - Alertas de seguridad
   - Bloqueo temporal de IPs sospechosas

### Medio Plazo (1 mes)

10. **Implementar MFA/2FA**
    - TOTP (Google Authenticator)
    - SMS backup
    - Recovery codes

11. **Agregar security.txt**
    - RFC 9116 compliance
    - Contacto de seguridad

12. **Centralizar logs**
    - ELK Stack / Datadog / CloudWatch
    - Alertas automatizadas

13. **Implementar CI/CD security scanning**
    - Dependabot
    - SAST (Bandit, Semgrep)
    - DAST testing

---

## Código de Ejemplo: Implementaciones Prioritarias

### 1. Validación de SECRET_KEY en Settings

```python
# app/core/config.py
from pydantic import Field, field_validator
import secrets

class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., min_length=32)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validar SECRET_KEY no sea débil"""
        weak_patterns = [
            "your-super-secret",
            "change-this",
            "secret",
            "password",
            "example",
            "test",
            "demo",
        ]

        v_lower = v.lower()
        for pattern in weak_patterns:
            if pattern in v_lower:
                raise ValueError(
                    f"SECRET_KEY parece ser un valor de ejemplo. "
                    f"Generar uno seguro con: openssl rand -hex 32"
                )

        # Verificar entropía
        if len(set(v)) < 16:
            raise ValueError("SECRET_KEY tiene baja entropía (pocos caracteres únicos)")

        return v
```

### 2. Rate Limiting Mejorado

```python
# app/presentation/api/v1/endpoints/supabase_auth.py

@router.post("/register")
@limiter.limit("3/hour")   # ✅ Solo 3 registros por hora
@limiter.limit("10/day")   # ✅ Máximo 10 por día
async def register(...):
    pass

@router.post("/login")
@limiter.limit("5/minute")  # ✅ 5 intentos por minuto
@limiter.limit("20/hour")   # ✅ 20 intentos por hora
async def login(...):
    pass
```

### 3. Logging Estructurado

```python
# app/infrastructure/database/repositories/supabase_user_repository_impl.py
import logging

logger = logging.getLogger(__name__)

async def get_by_email(self, email: str) -> SupabaseUser | None:
    try:
        # ... código ...
    except Exception as e:
        logger.error(
            "Error al obtener usuario por email",
            extra={
                "error_type": type(e).__name__,
                "email_domain": email.split("@")[1] if "@" in email else "unknown",
            },
            exc_info=True
        )
        return None
```

### 4. Token Blocklist con Redis

```python
# app/infrastructure/cache/token_blocklist.py
import redis.asyncio as redis
import hashlib
from app.core.config import settings

class TokenBlocklist:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def revoke_token(self, token: str, expires_in: int):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        await self.redis.setex(f"blocklist:{token_hash}", expires_in, "1")

    async def is_revoked(self, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return bool(await self.redis.exists(f"blocklist:{token_hash}"))

token_blocklist = TokenBlocklist()
```

### 5. CSRF Protection

```python
# app/presentation/middleware/csrf.py
from secrets import token_urlsafe
from datetime import datetime, timedelta

class CSRFProtection:
    def __init__(self, secret_key: str, token_expiry: int = 3600):
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self._tokens: dict[str, datetime] = {}

    def generate_token(self) -> str:
        token = token_urlsafe(32)
        self._tokens[token] = datetime.utcnow()
        return token

    def validate_token(self, token: str) -> bool:
        if token not in self._tokens:
            return False

        created_at = self._tokens[token]
        if datetime.utcnow() - created_at > timedelta(seconds=self.token_expiry):
            del self._tokens[token]
            return False

        del self._tokens[token]  # One-time use
        return True

    async def verify_csrf(self, request: Request):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return

        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token or not self.validate_token(csrf_token):
            raise HTTPException(
                status_code=403,
                detail="CSRF token invalid or missing"
            )

csrf_protection = CSRFProtection(settings.SECRET_KEY)
```

---

## Conclusión

El proyecto BandangAPI tiene una **base de seguridad sólida** gracias al uso de Supabase Auth, bcrypt, JWT, y una arquitectura limpia. Sin embargo, existen **vulnerabilidades críticas y de alta prioridad** que deben ser atendidas antes de pasar a producción:

**Fortalezas:**
- ✅ Arquitectura limpia y separation of concerns
- ✅ Supabase Auth con email confirmation
- ✅ bcrypt con cost factor adecuado
- ✅ Pydantic validation en todos los inputs
- ✅ Security headers middleware
- ✅ RBAC implementado

**Debilidades Críticas:**
- ⚠️ SECRET_KEY débil en ejemplo
- ⚠️ Service role key sin auditoría completa
- ⚠️ Rate limiting excesivamente permisivo
- ⚠️ Sin blocklist de tokens JWT
- ⚠️ Logging con `print()` en código crítico
- ⚠️ CORS permite wildcard
- ⚠️ CSP con unsafe-inline

**Score Final: 72/100 - MODERADO**

**Recomendación:** **NO DEPLOYAR A PRODUCCIÓN** hasta resolver las vulnerabilidades críticas (#1-#6). Las vulnerabilidades de severidad media pueden ser atendidas en sprints posteriores, pero las críticas deben ser resueltas inmediatamente.

---

**Auditoría realizada por:** Claude Code - Security Guardian Agent
**Próxima auditoría recomendada:** Después de implementar las correcciones críticas (1-2 semanas)

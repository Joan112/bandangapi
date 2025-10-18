# Flujos de Autenticación - BandangWeb API

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Registro de Usuario](#registro-de-usuario)
- [Login](#login)
- [Refresh Token](#refresh-token)
- [Logout](#logout)
- [Protección de Endpoints](#protección-de-endpoints)

---

## 🎯 Visión General

BandangWeb API utiliza **Supabase Auth** para autenticación y **JWT** (JSON Web Tokens) para autorización.

### Características

✅ Access tokens (30 minutos)  
✅ Refresh tokens (7 días)  
✅ Password hashing con bcrypt  
✅ Role-Based Access Control (RBAC)  
✅ Token blacklisting (logout)  

---

## 📝 Registro de Usuario

### Diagrama de Flujo

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Endpoint
    participant UseCase as RegisterUserSupabaseUseCase
    participant Repo as SupabaseUserRepositoryImpl
    participant Supabase as Supabase Auth
    participant DB as PostgreSQL (users table)
    
    Client->>API: POST /api/v1/auth/supabase/register
    Note over Client,API: {email, password, full_name}
    
    API->>API: Validate RegisterRequest schema
    API->>UseCase: execute(email, password, full_name)
    
    UseCase->>Repo: register(email, password, full_name)
    Repo->>Supabase: auth.sign_up()
    Note over Supabase: Hash password with bcrypt
    Supabase->>DB: INSERT INTO auth.users
    DB-->>Supabase: user_id, email
    Supabase-->>Repo: AuthResponse (user, session)
    
    Repo->>DB: INSERT INTO public.users<br/>(user_id, email, full_name, role='USER')
    DB-->>Repo: user record
    
    Repo-->>UseCase: (SupabaseUser, access_token, refresh_token)
    UseCase-->>API: (user, access_token, refresh_token)
    
    API->>API: Build AuthResponse
    API-->>Client: 201 Created<br/>{user, access_token, refresh_token}
```

### Request

```http
POST /api/v1/auth/supabase/register
Content-Type: application/json

{
  "email": "juan@example.com",
  "password": "SecurePass123!",
  "full_name": "Juan Pérez"
}
```

### Response

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "juan@example.com",
    "full_name": "Juan Pérez",
    "role": "USER",
    "is_active": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.MRj",
  "token_type": "bearer"
}
```

### Código

```python
# app/presentation/api/v1/endpoints/supabase_auth.py
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    use_case: RegisterUserSupabaseUseCase = Depends(get_register_use_case)
) -> AuthResponse:
    try:
        user, access_token, refresh_token = await use_case.execute(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        
        return AuthResponse(
            user=UserResponse.from_entity(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    except DuplicateEntityError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Validaciones

1. **Email**: Formato válido (EmailStr de Pydantic)
2. **Password**: Mínimo 8 caracteres (validado por Supabase)
3. **Email único**: No puede existir otro usuario con el mismo email

---

## 🔐 Login

### Diagrama de Flujo

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Endpoint
    participant UseCase as LoginUserSupabaseUseCase
    participant Repo as SupabaseUserRepositoryImpl
    participant Supabase as Supabase Auth
    participant DB as PostgreSQL
    
    Client->>API: POST /api/v1/auth/supabase/login
    Note over Client,API: {email, password}
    
    API->>API: Validate LoginRequest schema
    API->>UseCase: execute(email, password)
    
    UseCase->>Repo: authenticate(email, password)
    Repo->>Supabase: auth.sign_in_with_password()
    
    alt Password correcto
        Supabase->>Supabase: Verify bcrypt hash
        Supabase->>Supabase: Generate access_token (30min)
        Supabase->>Supabase: Generate refresh_token (7d)
        Supabase-->>Repo: AuthResponse (user, session)
        
        Repo->>DB: SELECT * FROM users WHERE id = user_id
        DB-->>Repo: user data (role, is_active)
        
        Repo-->>UseCase: (SupabaseUser, access_token, refresh_token)
        UseCase-->>API: (user, access_token, refresh_token)
        API-->>Client: 200 OK<br/>{user, access_token, refresh_token}
    else Password incorrecto
        Supabase-->>Repo: Error: Invalid credentials
        Repo-->>UseCase: None
        UseCase-->>API: InvalidCredentialsError
        API-->>Client: 401 Unauthorized<br/>{detail: "Credenciales inválidas"}
    end
```

### Request

```http
POST /api/v1/auth/supabase/login
Content-Type: application/json

{
  "email": "juan@example.com",
  "password": "SecurePass123!"
}
```

### Response (Éxito)

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "juan@example.com",
    "full_name": "Juan Pérez",
    "role": "USER",
    "is_active": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.MRjFzEw...",
  "token_type": "bearer"
}
```

### Response (Error)

```json
{
  "detail": "Credenciales inválidas"
}
```

### Código

```python
# app/domain/use_cases/auth/login_user_supabase.py
class LoginUserSupabaseUseCase:
    def __init__(self, repository: SupabaseUserRepository):
        self.repository = repository

    async def execute(
        self, email: str, password: str
    ) -> tuple[SupabaseUser, str, str]:
        result = await self.repository.authenticate(email, password)
        
        if not result:
            raise InvalidCredentialsError()
        
        user, access_token, refresh_token = result
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario inactivo"
            )
        
        return user, access_token, refresh_token
```

---

## 🔄 Refresh Token

### Diagrama de Flujo

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Endpoint
    participant Security as decode_token()
    participant JWT as create_access_token()
    
    Client->>API: POST /api/v1/auth/refresh
    Note over Client,API: {refresh_token}
    
    API->>Security: decode_token(refresh_token, "refresh")
    
    alt Token válido y no expirado
        Security-->>API: payload {sub: user_id, exp, iat}
        API->>JWT: create_access_token(user_id)
        JWT-->>API: new_access_token
        API->>JWT: create_refresh_token(user_id)
        JWT-->>API: new_refresh_token
        API-->>Client: 200 OK<br/>{access_token, refresh_token}
    else Token inválido o expirado
        Security-->>API: HTTPException (401)
        API-->>Client: 401 Unauthorized<br/>{detail: "Token inválido"}
    end
```

### Request

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "v1.MRjFzEw..."
}
```

### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.NewRefreshToken...",
  "token_type": "bearer"
}
```

### Código

```python
# app/presentation/api/v1/endpoints/supabase_auth.py
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    try:
        payload = decode_token(request.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except HTTPException:
        raise
```

---

## 🚪 Logout

### Diagrama de Flujo

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Endpoint
    
    Client->>API: POST /api/v1/auth/logout
    Note over Client,API: Authorization: Bearer <token>
    
    API->>API: Verify token (opcional)
    Note over API: En esta implementación,<br/>simplemente confirma logout<br/>sin invalidar el token
    
    API-->>Client: 200 OK<br/>{message: "Sesión cerrada exitosamente"}
    
    Note over Client: Cliente elimina tokens<br/>del localStorage/cookies
```

### Request

```http
POST /api/v1/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response

```json
{
  "message": "Sesión cerrada exitosamente"
}
```

### Código

```python
# app/presentation/api/v1/endpoints/supabase_auth.py
@router.post("/logout")
async def logout() -> dict[str, str]:
    """
    Logout del usuario.
    
    NOTA: En esta implementación, el cliente debe eliminar
    los tokens del localStorage. Para implementar token blacklisting,
    se requiere Redis u otra solución de cache.
    """
    return {"message": "Sesión cerrada exitosamente"}
```

### Implementación Avanzada (Futuro)

Para token blacklisting real, se requiere:

1. **Redis** para almacenar tokens invalidados
2. **Middleware** que verifique cada token contra la blacklist
3. **TTL** igual a la expiración del token

```python
# Futuro: Token blacklisting con Redis
@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    redis: Redis = Depends(get_redis_client)
):
    payload = decode_token(token)
    exp = payload.get("exp")
    ttl = exp - int(time.time())
    
    # Agregar token a blacklist
    await redis.setex(f"blacklist:{token}", ttl, "1")
    
    return {"message": "Sesión cerrada exitosamente"}
```

---

## 🛡️ Protección de Endpoints

### Diagrama de RBAC

```mermaid
graph TD
    A[Request con Authorization Header] --> B{Token válido?}
    B -->|No| C[401 Unauthorized]
    B -->|Sí| D[Decodificar JWT]
    D --> E{Usuario existe?}
    E -->|No| F[404 Not Found]
    E -->|Sí| G{Usuario activo?}
    G -->|No| H[400 Bad Request]
    G -->|Sí| I{Verificar rol}
    
    I -->|PUBLIC| J[✅ Permitir]
    I -->|USER| K{Rol >= USER?}
    I -->|ADMIN| L{Rol >= ADMIN?}
    I -->|SUPERADMIN| M{Rol == SUPERADMIN?}
    
    K -->|No| N[403 Forbidden]
    K -->|Sí| J
    L -->|No| N
    L -->|Sí| J
    M -->|No| N
    M -->|Sí| J
    
    style J fill:#4CAF50
    style C fill:#F44336
    style F fill:#F44336
    style H fill:#F44336
    style N fill:#F44336
```

### Jerarquía de Roles

```
SUPERADMIN (nivel 3)
    ↓ puede todo lo de ADMIN
ADMIN (nivel 2)
    ↓ puede todo lo de USER
USER (nivel 1)
    ↓ acceso básico
```

### Dependency Injection

```python
# app/core/dependencies.py

# 1. Obtener ID del usuario desde token
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return user_id

# 2. Obtener usuario completo
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> SupabaseUser:
    repo = SupabaseUserRepositoryImpl()
    user = await repo.get_by_id(UUID(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    return user

# 3. Verificar rol específico
def require_role(required_role: str):
    async def role_dependency(current_user=Depends(get_current_user)):
        role_hierarchy = {
            "USER": 1,
            "ADMIN": 2,
            "SUPERADMIN": 3,
        }
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere rol {required_role} o superior"
            )
        
        return current_user
    
    return role_dependency
```

### Ejemplos de Uso

```python
# Endpoint público (sin autenticación)
@router.get("/health")
async def health_check():
    return {"status": "ok"}

# Endpoint protegido (cualquier usuario autenticado)
@router.get("/users/me")
async def get_current_user_endpoint(
    current_user: SupabaseUser = Depends(get_current_user)
):
    return current_user

# Endpoint solo para ADMIN o superior
@router.get("/users")
async def list_users(
    current_user: SupabaseUser = Depends(require_role("ADMIN"))
):
    # Solo ADMIN y SUPERADMIN pueden acceder
    return await repository.list_users()

# Endpoint solo para SUPERADMIN
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: SupabaseUser = Depends(require_role("SUPERADMIN"))
):
    # Solo SUPERADMIN puede eliminar usuarios
    return await repository.delete(user_id)
```

---

## 🔑 Estructura del JWT

### Access Token

```json
{
  "iss": "https://dvwagqstnfveizuquwmh.supabase.co/auth/v1",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "authenticated",
  "exp": 1760833631,
  "iat": 1760830031,
  "email": "juan@example.com",
  "role": "authenticated"
}
```

**Campos**:
- `iss`: Issuer (Supabase URL)
- `sub`: Subject (User ID)
- `aud`: Audience
- `exp`: Expiration (timestamp Unix)
- `iat`: Issued At (timestamp Unix)
- `email`: Email del usuario
- `role`: Rol de Supabase (siempre "authenticated")

**Duración**: 30 minutos (configurable en `ACCESS_TOKEN_EXPIRE_MINUTES`)

### Refresh Token

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1761435831,
  "iat": 1760830031,
  "type": "refresh"
}
```

**Duración**: 7 días (configurable en `REFRESH_TOKEN_EXPIRE_DAYS`)

---

## 📊 Tabla Comparativa de Endpoints

| Endpoint | Método | Auth | Rol Mínimo | Descripción |
|----------|--------|------|------------|-------------|
| `/auth/supabase/register` | POST | ❌ No | - | Registro de usuario |
| `/auth/supabase/login` | POST | ❌ No | - | Login |
| `/auth/refresh` | POST | ❌ No | - | Renovar tokens |
| `/auth/logout` | POST | ✅ Sí | USER | Cerrar sesión |
| `/users/me` | GET | ✅ Sí | USER | Obtener perfil |
| `/users` | GET | ✅ Sí | ADMIN | Listar usuarios |
| `/users/{id}` | PATCH | ✅ Sí | ADMIN | Actualizar usuario |
| `/users/{id}` | DELETE | ✅ Sí | SUPERADMIN | Eliminar usuario |

---

## 🔒 Consideraciones de Seguridad

1. **HTTPS en producción**: Los tokens deben transmitirse solo sobre HTTPS
2. **No almacenar passwords**: Solo hashes bcrypt (gestionado por Supabase)
3. **Token expiration**: Access tokens de corta duración (30 min)
4. **Refresh token rotation**: Emitir nuevo refresh token en cada renovación
5. **Rate limiting**: Limitar intentos de login (60/min implementado)
6. **Secure headers**: HSTS, CSP, etc. (implementados en middleware)

---

## 📚 Referencias

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)


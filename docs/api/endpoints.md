# API Endpoints - BandangWeb API

## 📋 Tabla de Contenidos

- [Base URL](#base-url)
- [Autenticación](#autenticación)
- [Usuarios](#usuarios)
- [Eventos](#eventos)
- [Multimedia](#multimedia)
- [Health Check](#health-check)

---

## 🌐 Base URL

```
Desarrollo: http://localhost:8000
Producción: https://api.bandanuevageneracion.com
```

Todos los endpoints tienen el prefijo: `/api/v1`

---

## 🔐 Autenticación

### POST /api/v1/auth/supabase/register
Registrar nuevo usuario.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Juan Pérez"
}
```

**Response** `201 Created`:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Juan Pérez",
    "role": "USER",
    "is_active": true
  },
  "access_token": "eyJhbG...",
  "refresh_token": "v1.MRj...",
  "token_type": "bearer"
}
```

---

### POST /api/v1/auth/supabase/login
Autenticar usuario.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** `200 OK`: Igual que register

---

### POST /api/v1/auth/refresh
Renovar access token.

**Request**:
```json
{
  "refresh_token": "v1.MRj..."
}
```

**Response** `200 OK`:
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "v1.New...",
  "token_type": "bearer"
}
```

---

### POST /api/v1/auth/logout
Cerrar sesión.

**Headers**: `Authorization: Bearer <token>`

**Response** `200 OK`:
```json
{
  "message": "Sesión cerrada exitosamente"
}
```

---

## 👤 Usuarios

### GET /api/v1/users/me
Obtener perfil del usuario actual.

**Auth**: Required (USER)  
**Headers**: `Authorization: Bearer <token>`

**Response** `200 OK`:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Juan Pérez",
  "role": "USER",
  "is_active": true
}
```

---

### GET /api/v1/users
Listar todos los usuarios.

**Auth**: Required (ADMIN)  
**Headers**: `Authorization: Bearer <token>`  
**Query Params**: `skip=0&limit=100`

**Response** `200 OK`:
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "Juan Pérez",
      "role": "USER",
      "is_active": true
    }
  ],
  "total": 1
}
```

---

### PATCH /api/v1/users/{user_id}
Actualizar usuario.

**Auth**: Required (ADMIN)  
**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "full_name": "Juan Manuel Pérez",
  "role": "ADMIN"
}
```

**Response** `200 OK`:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Juan Manuel Pérez",
  "role": "ADMIN",
  "is_active": true
}
```

---

## 📅 Eventos

### POST /api/v1/events
Crear solicitud de evento.

**Auth**: Optional (puede ser público)

**Request**:
```json
{
  "name": "Juan Pérez",
  "email": "juan@example.com",
  "phone": "+5215512345678",
  "event_type": "Boda",
  "event_date": "2025-12-20",
  "location": "Salón de Fiestas 'El Jardín'",
  "guest_count": "150-200",
  "message": "Necesitamos cotización para barra de postres"
}
```

**Response** `201 Created`:
```json
{
  "id": "uuid",
  "name": "Juan Pérez",
  "email": "juan@example.com",
  "phone": "+5215512345678",
  "event_type": "Boda",
  "event_date": "2025-12-20",
  "location": "Salón de Fiestas 'El Jardín'",
  "guest_count": "150-200",
  "message": "Necesitamos cotización...",
  "status": "pending",
  "created_at": "2025-10-18T10:00:00Z"
}
```

---

### GET /api/v1/events
Listar eventos.

**Auth**: Required (ADMIN)  
**Query Params**: `skip=0&limit=100&status=pending`

**Response** `200 OK`:
```json
{
  "events": [...],
  "total": 10
}
```

---

### GET /api/v1/events/{event_id}
Obtener evento por ID.

**Auth**: Required (ADMIN)

**Response** `200 OK`: Event object

---

## 📸 Multimedia

### POST /api/v1/multimedia
Crear contenido multimedia.

**Auth**: Required (ADMIN)

**Request**:
```json
{
  "title": "Video promocional",
  "media_type": "video",
  "url": "https://example.com/video.mp4",
  "thumbnail_url": "https://example.com/thumbnail.jpg",
  "description": "Video de muestra",
  "category": "promotional",
  "is_published": true,
  "featured": false
}
```

**Response** `201 Created`: Multimedia object

---

### GET /api/v1/multimedia
Listar contenido multimedia.

**Auth**: Optional  
**Query Params**: `skip=0&limit=100&category=promotional&type=video&is_published=true&featured=false`

**Response** `200 OK`:
```json
{
  "multimedia": [...],
  "total": 5
}
```

---

### GET /api/v1/multimedia/{media_id}
Obtener multimedia por ID.

**Auth**: Optional

**Response** `200 OK`: Multimedia object

---

### PATCH /api/v1/multimedia/{media_id}
Actualizar multimedia.

**Auth**: Required (ADMIN)

**Request**:
```json
{
  "title": "Nuevo título",
  "is_published": true
}
```

**Response** `200 OK`: Updated multimedia object

---

### DELETE /api/v1/multimedia/{media_id}
Eliminar multimedia.

**Auth**: Required (ADMIN)

**Response** `200 OK`:
```json
{
  "message": "Contenido multimedia eliminado exitosamente"
}
```

---

## 🏥 Health Check

### GET /api/v1/health
Verificar estado del servicio.

**Auth**: No required

**Response** `200 OK`:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-18T10:00:00Z"
}
```

---

## 📊 Diagrama de Endpoints

```mermaid
graph TD
    A[API v1] --> B[/auth]
    A --> C[/users]
    A --> D[/events]
    A --> E[/multimedia]
    A --> F[/health]
    
    B --> B1[POST /supabase/register]
    B --> B2[POST /supabase/login]
    B --> B3[POST /refresh]
    B --> B4[POST /logout]
    
    C --> C1[GET /me]
    C --> C2[GET /]
    C --> C3[PATCH /:id]
    
    D --> D1[POST /]
    D --> D2[GET /]
    D --> D3[GET /:id]
    
    E --> E1[POST /]
    E --> E2[GET /]
    E --> E3[GET /:id]
    E --> E4[PATCH /:id]
    E --> E5[DELETE /:id]
    
    F --> F1[GET /]
    
    style B fill:#9C27B0
    style C fill:#2196F3
    style D fill:#4CAF50
    style E fill:#FF9800
    style F fill:#607D8B
```

---

## 🔒 Códigos de Estado HTTP

| Código | Descripción | Cuándo se usa |
|--------|-------------|---------------|
| 200 | OK | Request exitoso |
| 201 | Created | Recurso creado exitosamente |
| 400 | Bad Request | Datos inválidos |
| 401 | Unauthorized | Token inválido o expirado |
| 403 | Forbidden | Sin permisos suficientes |
| 404 | Not Found | Recurso no encontrado |
| 422 | Unprocessable Entity | Validación de Pydantic falló |
| 500 | Internal Server Error | Error del servidor |

---

## 📚 Documentación Interactiva

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`


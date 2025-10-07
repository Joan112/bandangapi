# Ejemplos de CURL para BandangWeb API

## Base URL
```bash
BASE_URL="http://localhost:8000/api/v1"
```

---

## 1. Health Check

### Verificar estado del servidor
```bash
curl -X GET "${BASE_URL}/health"
```

---

## 2. Autenticación (Supabase)

### Registrar un nuevo usuario
```bash
curl -X POST "${BASE_URL}/auth/supabase/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "password123",
    "full_name": "Juan Pérez"
  }'
```

**Respuesta exitosa:**
```json
{
  "user": {
    "id": "uuid-aqui",
    "email": "usuario@example.com",
    "full_name": "Juan Pérez",
    "role": "user",
    "is_active": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Login de usuario
```bash
curl -X POST "${BASE_URL}/auth/supabase/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "password123"
  }'
```

---

## 3. Eventos

### Crear un nuevo evento
```bash
curl -X POST "${BASE_URL}/events/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan Pérez",
    "email": "juan.perez@example.com",
    "phone": "+5215512345678",
    "eventType": "Boda",
    "eventDate": "2025-12-20",
    "location": "Salón de Fiestas El Jardín",
    "guestCount": "150-200",
    "message": "Necesitamos cotización para barra de postres"
  }'
```

**Respuesta exitosa:**
```json
{
  "id": "uuid-del-evento",
  "name": "Juan Pérez",
  "email": "juan.perez@example.com",
  "phone": "+5215512345678",
  "eventType": "Boda",
  "eventDate": "2025-12-20",
  "location": "Salón de Fiestas El Jardín",
  "guestCount": "150-200",
  "message": "Necesitamos cotización para barra de postres",
  "status": "pending",
  "createdAt": "2025-10-06T23:00:00Z",
  "updatedAt": "2025-10-06T23:00:00Z"
}
```

---

## 4. Multimedia

### Crear contenido multimedia (imagen)
```bash
curl -X POST "${BASE_URL}/multimedia/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "image",
    "title": "Concierto en vivo - Teatro Nacional 2024",
    "description": "Presentación especial de la banda Bandang en el Teatro Nacional",
    "url": "https://example.com/images/concierto-2024.jpg",
    "thumbnail": "https://example.com/images/concierto-2024-thumb.jpg",
    "category": "conciertos",
    "tags": ["concierto", "2024", "teatro nacional", "en vivo"],
    "featured": true,
    "size": 2048576,
    "width": 1920,
    "height": 1080,
    "isPublished": true,
    "order": 1
  }'
```

### Crear contenido multimedia (video)
```bash
curl -X POST "${BASE_URL}/multimedia/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "video",
    "title": "Video promocional Bandang 2024",
    "description": "Video oficial de la gira 2024",
    "url": "https://example.com/videos/promo-2024.mp4",
    "thumbnail": "https://example.com/videos/promo-2024-thumb.jpg",
    "category": "promocionales",
    "tags": ["video", "promocional", "gira", "2024"],
    "featured": true,
    "size": 52428800,
    "duration": 180,
    "isPublished": true,
    "order": 1
  }'
```

**Respuesta exitosa:**
```json
{
  "id": "uuid-del-contenido",
  "type": "image",
  "title": "Concierto en vivo - Teatro Nacional 2024",
  "description": "Presentación especial de la banda Bandang en el Teatro Nacional",
  "url": "https://example.com/images/concierto-2024.jpg",
  "thumbnail": "https://example.com/images/concierto-2024-thumb.jpg",
  "category": "conciertos",
  "tags": ["concierto", "2024", "teatro nacional", "en vivo"],
  "featured": true,
  "uploadedAt": "2025-10-06T23:00:00Z",
  "updatedAt": "2025-10-06T23:00:00Z",
  "createdBy": null,
  "size": 2048576,
  "width": 1920,
  "height": 1080,
  "duration": null,
  "isPublished": true,
  "order": 1
}
```

### Listar todo el contenido multimedia
```bash
curl -X GET "${BASE_URL}/multimedia/"
```

### Listar multimedia con filtros
```bash
# Solo imágenes publicadas
curl -X GET "${BASE_URL}/multimedia/?type=image&isPublished=true"

# Solo contenido destacado
curl -X GET "${BASE_URL}/multimedia/?featured=true"

# Por categoría
curl -X GET "${BASE_URL}/multimedia/?category=conciertos"

# Combinando filtros con paginación
curl -X GET "${BASE_URL}/multimedia/?type=video&category=promocionales&isPublished=true&skip=0&limit=10"
```

### Obtener multimedia por ID
```bash
curl -X GET "${BASE_URL}/multimedia/{multimedia_id}"
```

Ejemplo:
```bash
curl -X GET "${BASE_URL}/multimedia/123e4567-e89b-12d3-a456-426614174000"
```

### Actualizar multimedia
```bash
curl -X PATCH "${BASE_URL}/multimedia/{multimedia_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Nuevo título actualizado",
    "description": "Descripción actualizada",
    "featured": false,
    "isPublished": true,
    "order": 5
  }'
```

### Eliminar multimedia
```bash
curl -X DELETE "${BASE_URL}/multimedia/{multimedia_id}"
```

---

## Ejemplos completos con variables

### Script completo para probar eventos
```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

# Crear evento
echo "=== Creando evento ==="
EVENT_RESPONSE=$(curl -s -X POST "${BASE_URL}/events/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "María González",
    "email": "maria.gonzalez@example.com",
    "phone": "+5215598765432",
    "eventType": "XV Años",
    "eventDate": "2026-03-15",
    "location": "Jardín Las Rosas",
    "guestCount": "100-120",
    "message": "Queremos música en vivo para toda la noche"
  }')

echo "$EVENT_RESPONSE" | jq '.'
```

### Script completo para probar multimedia
```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

# Crear imagen
echo "=== Creando contenido multimedia (imagen) ==="
IMAGE_RESPONSE=$(curl -s -X POST "${BASE_URL}/multimedia/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "image",
    "title": "Ensayo general 2024",
    "description": "Preparativos para el concierto del Teatro Nacional",
    "url": "https://example.com/images/ensayo-2024.jpg",
    "thumbnail": "https://example.com/images/ensayo-2024-thumb.jpg",
    "category": "ensayos",
    "tags": ["ensayo", "2024", "preparación"],
    "featured": false,
    "size": 1536000,
    "width": 1280,
    "height": 720,
    "isPublished": true,
    "order": 2
  }')

echo "$IMAGE_RESPONSE" | jq '.'

# Extraer ID del contenido creado
MULTIMEDIA_ID=$(echo "$IMAGE_RESPONSE" | jq -r '.id')

# Listar multimedia
echo -e "\n=== Listando contenido multimedia ==="
curl -s -X GET "${BASE_URL}/multimedia/?limit=5" | jq '.'

# Obtener por ID
echo -e "\n=== Obteniendo contenido por ID ==="
curl -s -X GET "${BASE_URL}/multimedia/${MULTIMEDIA_ID}" | jq '.'

# Actualizar
echo -e "\n=== Actualizando contenido ==="
curl -s -X PATCH "${BASE_URL}/multimedia/${MULTIMEDIA_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Ensayo general 2024 - ACTUALIZADO",
    "featured": true
  }' | jq '.'
```

---

## Autenticación con JWT (para endpoints protegidos)

Si tienes endpoints que requieren autenticación, primero obtén el token:

```bash
# 1. Login
TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/supabase/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "password123"
  }')

# 2. Extraer el access_token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

# 3. Usar el token en peticiones protegidas
curl -X GET "${BASE_URL}/protected-endpoint" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

---

## Notas importantes

1. **Reemplaza `{multimedia_id}`** con un UUID real de tu base de datos
2. **Ejecuta primero el SQL** del archivo `scripts/create_multimedia_schema.sql` en Supabase antes de usar los endpoints de multimedia
3. **Los campos con alias camelCase** en el JSON se mapean automáticamente a snake_case en la base de datos:
   - `eventType` → `event_type`
   - `eventDate` → `event_date`
   - `guestCount` → `guest_count`
   - `isPublished` → `is_published`
   - `createdBy` → `created_by`
   - `uploadedAt` → `uploaded_at`
   - `updatedAt` → `updated_at`

4. **Formatos de fecha**: Usa formato ISO 8601 (`YYYY-MM-DD` para dates, `YYYY-MM-DDTHH:MM:SSZ` para timestamps)

5. **El servidor debe estar corriendo** en `http://localhost:8000`

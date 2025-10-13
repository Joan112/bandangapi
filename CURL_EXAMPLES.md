# Ejemplos de Comandos cURL para la API Bandang

Aquí se encuentran los comandos `curl` correctos para interactuar con los endpoints de la API desplegada en Cloud Run.

**URL Base de Producción:** `https://bandangapi-service-icloflh2la-ew.a.run.app`

---

### Registrar un Nuevo Usuario

Crea un nuevo usuario en el sistema.

```bash
curl --location 'https://bandangapi-service-icloflh2la-ew.a.run.app/api/v1/auth/supabase/register' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "tu-email@example.com",
    "password": "tu-password-segura",
    "full_name": "Tu Nombre Completo"
}'
```

---

### Iniciar Sesión (Login)

Autentica un usuario y obtiene los tokens de acceso.

```bash
curl --location 'https://bandangapi-service-icloflh2la-ew.a.run.app/api/v1/auth/supabase/login' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "tu-email@example.com",
    "password": "tu-password-segura"
}'
```

---

### Crear un Nuevo Evento

Registra un nuevo evento en el sistema. Requiere un token JWT de Supabase válido en la cabecera `Authorization`.

```bash
curl --location 'https://bandangapi-service-icloflh2la-ew.a.run.app/api/v1/events/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TU_SUPABASE_JWT' \
--data-raw '{
    "name": "Ana García",
    "email": "ana.garcia@example.com",
    "phone": "+5215587654321",
    "eventType": "XV Años",
    "eventDate": "2026-04-15",
    "location": "Terraza Real",
    "guestCount": "100",
    "message": "Cotizar también mesa de dulces."
}'
```
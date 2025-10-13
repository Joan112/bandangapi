# Configuración de CORS para Producción

## Problema
El frontend en `https://bandanuevageneracion.com` no puede hacer peticiones a la API en Google Cloud Run debido a que falta configurar los orígenes permitidos en CORS.

## Error
```
Access to fetch at 'https://bandangapi-service-icloflh2la-ew.a.run.app/api/v1/events/'
from origin 'https://bandanuevageneracion.com' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Solución

### Opción 1: Desde la Consola de Google Cloud (Recomendado)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Navega a **Cloud Run**
3. Selecciona el servicio: `bandangapi-service`
4. Click en **EDIT & DEPLOY NEW REVISION**
5. Ve a la pestaña **Variables & Secrets**
6. Click en **ADD VARIABLE**
7. Configura:
   - **Nombre:** `BACKEND_CORS_ORIGINS`
   - **Valor:** `https://bandanuevageneracion.com,https://www.bandanuevageneracion.com,http://localhost:3000`
8. Click en **DEPLOY**
9. Espera a que se complete el despliegue (1-2 minutos)

### Opción 2: Desde gcloud CLI

```bash
# Asegúrate de estar autenticado
gcloud auth login

# Configura el proyecto
gcloud config set project TU_PROJECT_ID

# Actualiza el servicio con la nueva variable
gcloud run services update bandangapi-service \
  --region=europe-west1 \
  --update-env-vars BACKEND_CORS_ORIGINS="https://bandanuevageneracion.com,https://www.bandanuevageneracion.com,http://localhost:3000"
```

## Verificación

Después de configurar la variable, prueba el endpoint desde el frontend:

```bash
curl -X OPTIONS 'https://bandangapi-service-icloflh2la-ew.a.run.app/api/v1/events/' \
  -H 'Origin: https://bandanuevageneracion.com' \
  -H 'Access-Control-Request-Method: POST' \
  -v
```

Deberías ver en la respuesta:
```
< access-control-allow-origin: https://bandanuevageneracion.com
< access-control-allow-credentials: true
< access-control-allow-methods: *
< access-control-allow-headers: *
```

## Notas Importantes

- **Sin espacios después de las comas** en el valor de la variable
- Incluye tanto `https://bandanuevageneracion.com` como `https://www.bandanuevageneracion.com`
- Mantén `http://localhost:3000` para desarrollo local
- El código ya está preparado para parsear el string con comas (ver `app/core/config.py:38-43`)
- No necesitas modificar ningún código, solo configurar la variable de entorno en Cloud Run

## Variables de Entorno Recomendadas para Producción

Además de CORS, verifica que tengas configuradas todas estas variables en producción:

```env
# App
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=<tu-secret-key-seguro>

# CORS
BACKEND_CORS_ORIGINS=https://bandanuevageneracion.com,https://www.bandanuevageneracion.com

# Supabase
SUPABASE_URL=https://dvwagstnfveizuquqwmh.supabase.co
SUPABASE_KEY=<tu-supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<tu-supabase-service-role-key>

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

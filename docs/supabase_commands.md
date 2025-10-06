# Comandos para BandangAPI con Supabase

Este documento contiene los comandos curl para interactuar con los endpoints de Supabase en BandangAPI, así como los comandos para gestionar el sistema.

## Comandos curl para Supabase

### Registro de Usuario

```bash
curl -X POST http://localhost:8000/api/v1/supabase/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "contraseña123",
    "full_name": "Usuario Ejemplo"
  }'
```

### Login de Usuario

```bash
curl -X POST http://localhost:8000/api/v1/supabase/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "contraseña123"
  }'
```

### Obtener Productos

```bash
curl -X GET http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer {tu_token_de_acceso}"
```

### Filtrar Productos por Categoría

```bash
curl -X GET http://localhost:8000/api/v1/products?category_id=1 \
  -H "Authorization: Bearer {tu_token_de_acceso}"
```

### Buscar Productos

```bash
curl -X GET "http://localhost:8000/api/v1/products?search=smartphone" \
  -H "Authorization: Bearer {tu_token_de_acceso}"
```

## Comandos para Gestionar el Sistema

### Levantar el Sistema

```bash
# Iniciar el sistema con uvicorn
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Iniciar con Docker Compose
docker-compose -f docker/docker-compose.yml up -d
```

### Refrescar el Sistema

```bash
# Refrescar dependencias
poetry update

# Refrescar migraciones de base de datos
poetry run alembic revision --autogenerate -m "refresh_migrations"
poetry run alembic upgrade head
```

### Reconstruir el Sistema

```bash
# Reconstruir desde cero
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml build --no-cache
docker-compose -f docker/docker-compose.yml up -d

# Reconstruir base de datos
poetry run python scripts/init_db.py
poetry run python scripts/seed_data.py
```

### Comandos Adicionales

```bash
# Ejecutar pruebas
poetry run pytest -v

# Ejecutar linting
poetry run black app/
poetry run ruff check app/
poetry run mypy app/

# Crear un usuario administrador
poetry run python scripts/create_admin.py
```

## Variables de Entorno Necesarias

Asegúrate de tener configuradas las siguientes variables en tu archivo `.env`:

```
# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-clave-de-api-supabase

# Aplicación
SECRET_KEY=tu-clave-secreta-para-jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Notas Importantes

- Los tokens JWT son necesarios para acceder a los endpoints protegidos
- El sistema utiliza PostgreSQL a través de Supabase para la persistencia de datos
- Las migraciones se gestionan con Alembic
- El sistema está configurado para usar Redis como caché (opcional)
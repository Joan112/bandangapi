# INICIO RAPIDO - BandangWeb API

## Opcion 1: Ejecutar con Docker (MAS FACIL)

```bash
# 1. Ir al directorio del proyecto
cd /Users/digitalizacion/Documents/Python/bandangweb

# 2. Levantar todos los servicios (PostgreSQL + Redis + App)
docker-compose -f docker/docker-compose.yml up -d

# 3. Esperar 10 segundos a que la BD este lista
sleep 10

# 4. Ejecutar migraciones de base de datos
docker-compose -f docker/docker-compose.yml exec app alembic upgrade head

# 5. Crear usuario administrador
docker-compose -f docker/docker-compose.yml exec app python scripts/create_admin.py

# 6. LISTO! La API esta corriendo en:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/api/docs
# - Health: http://localhost:8000/api/v1/health
```

```
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Credenciales del admin creado:**
- Email: admin@bandangweb.com
- Password: AdminPassword123

## Opcion 2: Ejecucion Local (Requiere PostgreSQL y Redis instalados)

```bash
# 1. Ir al directorio del proyecto
cd /Users/digitalizacion/Documents/Python/bandangweb

# 2. Instalar Poetry (si no lo tienes)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Instalar dependencias
poetry install

# 4. Verificar que PostgreSQL y Redis esten corriendo localmente
# PostgreSQL: localhost:5432
# Redis: localhost:6379

# 5. Ejecutar migraciones
poetry run alembic upgrade head

# 6. Crear usuario administrador
poetry run python scripts/create_admin.py

# 7. Ejecutar la aplicacion
poetry run uvicorn app.main:app --reload

# 8. LISTO! La API esta corriendo en:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/api/docs
# - Health: http://localhost:8000/api/v1/health
```

## Pruebas Rapidas

### 1. Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### 2. Login con admin
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bandangweb.com",
    "password": "AdminPassword123"
  }'
```

### 3. Registrar nuevo usuario
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123",
    "full_name": "Test User"
  }'
```

## Ver documentacion interactiva

Abrir en el navegador:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Comandos Utiles

### Ver logs (Docker)
```bash
docker-compose -f docker/docker-compose.yml logs -f app
```

### Ejecutar tests
```bash
# Con Docker
docker-compose -f docker/docker-compose.yml exec app pytest

# Local
poetry run pytest
```

### Poblar con datos de prueba
```bash
# Con Docker
docker-compose -f docker/docker-compose.yml exec app python scripts/seed_data.py 10

# Local
poetry run python scripts/seed_data.py 10
```

### Detener servicios (Docker)
```bash
docker-compose -f docker/docker-compose.yml down
```

## Problemas Comunes

### Error: "Connection refused" en PostgreSQL
- Verificar que PostgreSQL este corriendo
- Docker: `docker-compose -f docker/docker-compose.yml ps`
- Local: `pg_isready -h localhost -p 5432`

### Error: "Connection refused" en Redis
- Verificar que Redis este corriendo
- Docker: `docker-compose -f docker/docker-compose.yml ps`
- Local: `redis-cli ping` (debe responder "PONG")

### Error: "ModuleNotFoundError"
- Ejecutar: `poetry install`

### Puerto 8000 ya en uso
- Cambiar puerto en docker-compose.yml: `ports: - "8001:8000"`
- O local: `uvicorn app.main:app --port 8001`

## Siguiente Paso

Lee el README.md completo para documentacion detallada.

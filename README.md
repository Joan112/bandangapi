# BandangWeb API

Backend API completo con **Clean Architecture**, **FastAPI**, **PostgreSQL** y seguridad enterprise-level.

## Características

### Arquitectura
- Clean Architecture (Domain, Infrastructure, Presentation)
- Separación de responsabilidades (SoC)
- Dependency Injection
- Repository Pattern
- Use Cases para lógica de negocio

### Stack Tecnológico
- **Framework**: FastAPI 0.110+
- **Python**: 3.11+
- **Base de Datos**: PostgreSQL con SQLAlchemy 2.0 (async)
- **Migraciones**: Alembic
- **Cache**: Redis
- **Task Queue**: Celery (opcional)
- **Validación**: Pydantic V2
- **Testing**: Pytest + pytest-asyncio
- **Containerización**: Docker + Docker Compose

### Seguridad
- JWT con access y refresh tokens
- Password hashing con bcrypt (cost factor 12)
- Token blacklisting (logout)
- Role-based access control (RBAC)
- Rate limiting (60 req/min, 1000 req/hour)
- Security headers (HSTS, X-Frame, CSP, etc)
- Input validation estricta (Pydantic)
- SQL injection prevention (ORM)
- CORS configurado
- Structured logging

### CI/CD
- Integración continua con GitHub Actions
- Pruebas automatizadas en cada push
- Análisis de calidad de código
- Despliegue automatizado

### Funcionalidades
- Registro y autenticación de usuarios
- Login con JWT
- Refresh token
- Logout con invalidación de tokens
- CRUD completo de usuarios
- Sistema de roles (USER, ADMIN, SUPERADMIN)
- Paginación en listados
- Health checks
- API documentada (Swagger + ReDoc)

---

## Estructura del Proyecto

```
bandangweb/
├── app/
│   ├── core/                    # Configuración y utilidades core
│   │   ├── config.py           # Settings con Pydantic
│   │   ├── security.py         # JWT, hashing, tokens
│   │   ├── database.py         # DB connection
│   │   ├── dependencies.py     # FastAPI dependencies
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── domain/                  # Capa de Dominio
│   │   ├── entities/           # Entidades de negocio
│   │   │   └── user.py
│   │   ├── repositories/       # Interfaces/Protocolos
│   │   │   └── user_repository.py
│   │   └── use_cases/          # Lógica de negocio
│   │       ├── create_user.py
│   │       └── authenticate_user.py
│   │
│   ├── infrastructure/          # Capa de Infraestructura
│   │   ├── database/
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   │   ├── base.py
│   │   │   │   └── user_model.py
│   │   │   └── repositories/   # Implementaciones
│   │   │       └── user_repository_impl.py
│   │   ├── external/           # APIs externas
│   │   └── cache/              # Redis
│   │       └── redis_client.py
│   │
│   ├── presentation/            # Capa de Presentación
│   │   ├── api/v1/
│   │   │   ├── endpoints/      # Routes
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   └── health.py
│   │   │   └── schemas/        # Pydantic schemas
│   │   │       ├── user.py
│   │   │       └── auth.py
│   │   └── middleware/
│   │       ├── security_headers.py
│   │       ├── rate_limit.py
│   │       └── logging.py
│   │
│   └── main.py                 # FastAPI app instance
│
├── tests/
│   ├── unit/                   # Tests unitarios
│   │   └── test_security.py
│   └── integration/            # Tests de integración
│       ├── test_auth_api.py
│       └── test_users_api.py
│
├── alembic/                    # Database migrations
├── docker/                     # Docker files
├── scripts/                    # Scripts de utilidad
├── .env.example                # Template de variables
├── pyproject.toml              # Poetry dependencies
└── README.md
```

---

## Instalación y Configuración

### Requisitos Previos
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker + Docker Compose (opcional)

### Opción 1: Con Docker (Recomendado)

1. **Clonar el repositorio**
```bash
cd /Users/digitalizacion/Documents/Python/bandangweb
```

2. **Crear archivo .env**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

3. **Levantar servicios con Docker Compose**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

4. **Ejecutar migraciones**
```bash
docker-compose -f docker/docker-compose.yml exec app alembic upgrade head
```

5. **Crear usuario administrador**
```bash
docker-compose -f docker/docker-compose.yml exec app python scripts/create_admin.py
```

6. **Acceder a la API**
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Opción 2: Instalación Local

1. **Instalar Poetry**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Instalar dependencias**
```bash
poetry install
```

3. **Configurar entorno**
```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL y Redis
```

4. **Ejecutar migraciones**
```bash
poetry run alembic upgrade head
```

5. **Crear usuario administrador**
```bash
poetry run python scripts/create_admin.py
```

6. **Ejecutar aplicación**
```bash
poetry run uvicorn app.main:app --reload
```

---

## Uso de la API

### Documentación Interactiva

Para ejemplos de uso de la API, consulte la documentación interactiva:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

Toda la documentación de endpoints, esquemas de datos y ejemplos de uso se encuentra
disponible en estas interfaces interactivas.

---

## Testing

### Ejecutar todos los tests
```bash
poetry run pytest
```

### Ejecutar tests con coverage
```bash
poetry run pytest --cov=app --cov-report=html
```

### Ejecutar tests específicos
```bash
# Tests unitarios
poetry run pytest tests/unit/

# Tests de integración
poetry run pytest tests/integration/

# Test específico
poetry run pytest tests/integration/test_auth_api.py::test_login_success
```

---

## Migraciones de Base de Datos

### Crear nueva migración
```bash
poetry run alembic revision --autogenerate -m "Descripción de la migración"
```

### Aplicar migraciones
```bash
poetry run alembic upgrade head
```

### Revertir última migración
```bash
poetry run alembic downgrade -1
```

### Ver historial de migraciones
```bash
poetry run alembic history
```

---

## Scripts de Utilidad

### Inicializar base de datos
```bash
poetry run python scripts/init_db.py
```

### Crear usuario administrador
```bash
poetry run python scripts/create_admin.py
```

### Poblar con datos de ejemplo
```bash
# Crear 10 usuarios de ejemplo
poetry run python scripts/seed_data.py 10

# Crear 50 usuarios de ejemplo
poetry run python scripts/seed_data.py 50
```

---

## Variables de Entorno

Configurar en `.env`:

```env
# Aplicación
PROJECT_NAME=BandangWeb API
ENVIRONMENT=development
DEBUG=true

# Base de Datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bandangweb_db

# Seguridad (IMPORTANTE: Cambiar en producción)
SECRET_KEY=tu-clave-secreta-segura-minimo-32-caracteres
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

---

## Seguridad

### Medidas Implementadas

- **Autenticación JWT**: Access y refresh tokens
- **Password Hashing**: Bcrypt con cost factor 12
- **Role-Based Access Control (RBAC)**: USER, ADMIN, SUPERADMIN
- **Rate Limiting**: 60 req/min, 1000 req/hour
- **Security Headers**: HSTS, X-Frame-Options, CSP, etc
- **Input Validation**: Pydantic V2 con validación estricta
- **SQL Injection Prevention**: SQLAlchemy ORM
- **CORS**: Configurado y restrictivo
- **Audit Logging**: Todas las requests loggeadas

### Recomendaciones para Producción

1. Generar SECRET_KEY seguro:
```bash
openssl rand -hex 32
```

2. Usar HTTPS (TLS/SSL)
3. Configurar firewall
4. Habilitar 2FA para admins (implementar)
5. Rotar tokens regularmente
6. Monitorear logs de seguridad
7. Implementar backup automático de BD
8. Usar secrets manager (AWS Secrets, Vault, etc)

---

## Deployment

### Docker Production

1. Build imagen de producción:
```bash
docker build -f docker/Dockerfile.prod -t bandangweb:latest .
```

2. Ejecutar con docker-compose:
```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Kubernetes

(Pendiente: Agregar manifests de Kubernetes)

### AWS/GCP/Azure

(Pendiente: Agregar guías de deployment cloud)

---

## Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-feature`)
3. Commit cambios (`git commit -m 'Agregar nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Crear Pull Request

---

## Licencia

Este proyecto está bajo la Licencia MIT.

---

## Contacto

- Email: team@bandangweb.com
- Web: https://bandangweb.com

---

## Créditos

Desarrollado con:
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Redis
- Docker

**Versión**: 1.0.0
**Última actualización**: 2025

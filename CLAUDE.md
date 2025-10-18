# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BandangWeb API is a FastAPI backend built with **Clean Architecture** principles, using **Supabase** as the primary backend-as-a-service (authentication, database, storage) and PostgreSQL. The project emphasizes type safety, security, and separation of concerns.

**Key Stack:**
- Python 3.11+ with Poetry for dependency management
- FastAPI 0.110+ with async/await patterns
- Supabase for auth, database, and storage
- Pydantic V2 for validation and schemas
- SQLAlchemy 2.0 (async) for direct database operations when needed
- Alembic for database migrations
- Redis for caching (optional)
- Docker for containerization

## Architecture

The project follows **Clean Architecture** with three main layers:

### 1. Domain Layer (`app/domain/`)
- **Entities** (`entities/`): Core business objects (e.g., `SupabaseUser`, `Event`, `Multimedia`)
- **Repositories** (`repositories/`): Abstract interfaces defining data operations (e.g., `SupabaseUserRepository`, `EventRepository`)
- **Use Cases** (`use_cases/`): Business logic orchestration (e.g., `register_user_supabase.py`, `create_event.py`)

### 2. Infrastructure Layer (`app/infrastructure/`)
- **Database** (`database/`): SQLAlchemy models and repository implementations
- **External** (`external/`): Third-party service integrations
  - `external/supabase/client.py`: Supabase client singleton with utility methods
- **Cache** (`cache/`): Redis client and caching logic

### 3. Presentation Layer (`app/presentation/`)
- **API** (`api/v1/`): FastAPI routers, endpoints, and Pydantic schemas
  - Endpoints: `health.py`, `supabase_auth.py`, `events.py`, `multimedia.py`
  - Schemas: Request/response models inheriting from base schemas
- **Middleware**: Security headers, rate limiting, logging

### Core (`app/core/`)
- `config.py`: Centralized configuration with Pydantic Settings (loads from `.env`)
- `security.py`: JWT handling, password hashing, token management
- `database.py`: Database connection management
- `dependencies.py`: FastAPI dependency injection functions
- `exceptions.py`: Custom exception classes

## Development Commands

### Setup and Installation

```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
# Edit .env with your Supabase credentials and other settings
```

### Running the Application

```bash
# Development mode with hot reload
poetry run uvicorn app.main:app --reload

# Production mode
poetry run gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 app.main:app

# With Docker
docker-compose -f docker/docker-compose.yml up -d
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test types
poetry run pytest tests/unit/
poetry run pytest tests/integration/

# Run a single test
poetry run pytest tests/integration/test_auth_api.py::test_login_success
```

### Code Quality

```bash
# Format code with Black
poetry run black app/ tests/

# Lint with Ruff
poetry run ruff check app/ tests/

# Type check with mypy
poetry run mypy app/
```

### Database Migrations

```bash
# Create a new migration (auto-detect changes from models)
poetry run alembic revision --autogenerate -m "Description of change"

# Apply all pending migrations
poetry run alembic upgrade head

# Rollback last migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history

# View current migration version
poetry run alembic current
```

### Utility Scripts

```bash
# Initialize database (if needed for legacy setup)
poetry run python scripts/init_db.py

# Create admin user
poetry run python scripts/create_admin.py

# Seed database with sample data
poetry run python scripts/seed_data.py 10  # Creates 10 sample users
```

## Important Configuration

### Environment Variables (`.env`)

Key variables defined in `app/core/config.py`:

- `SECRET_KEY`: JWT secret (minimum 32 characters) - **MUST** be set
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY`: Admin key for bypassing RLS
- `ENVIRONMENT`: `development`, `staging`, or `production`
- `DEBUG`: Enable debug mode
- `BACKEND_CORS_ORIGINS`: Comma-separated list of allowed origins
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT access token lifetime (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: JWT refresh token lifetime (default: 7)

### CORS Configuration

CORS is configured in `app/main.py` with hardcoded production domains:
- `https://bandanuevageneracion.com`
- `https://www.bandanuevageneracion.com`
- Plus any origins from `BACKEND_CORS_ORIGINS` in `.env`

When modifying CORS, update both the hardcoded list and environment variables.

## Supabase Integration

This project uses **Supabase** for authentication and database operations. Key points:

### Supabase Client (`app/infrastructure/external/supabase/client.py`)

The `SupabaseClient` class provides:
- `client` property: Regular client (respects RLS)
- `admin_client` property: Admin client (bypasses RLS - use with service role key)
- Helper methods: `get_by_id()`, `get_by_field()`, `list_all()`, `create()`, `update()`, `delete()`, `execute_rpc()`

Access via singleton: `from app.infrastructure.external.supabase.client import supabase_client`

### Repository Pattern with Supabase

Repositories follow the protocol defined in `app/domain/repositories/`:
- Abstract interface in domain layer
- Implementation in `app/infrastructure/database/repositories/`
- Example: `SupabaseUserRepository` → `SupabaseUserRepositoryImpl`

### Authentication Flow

1. User registers/logs in via `/api/v1/auth/register` or `/api/v1/auth/login`
2. Supabase handles password hashing and auth tokens
3. Use cases in `app/domain/use_cases/auth/` orchestrate business logic
4. JWT tokens are managed by Supabase Auth

## API Structure

All API endpoints are prefixed with `/api/v1` (configured via `settings.API_V1_PREFIX`).

Main routers defined in `app/presentation/api/router.py`:
- `/health` - Health check endpoints
- `/auth` - Authentication (register, login, logout, refresh)
- `/events` - Event management CRUD
- `/multimedia` - Multimedia resource management

Interactive documentation available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Security Features

- **JWT Authentication**: Access and refresh tokens
- **Password Hashing**: Bcrypt with cost factor 12
- **Role-Based Access Control (RBAC)**: USER, ADMIN, SUPERADMIN roles
- **Rate Limiting**: 60 req/min, 1000 req/hour (via SlowAPI)
- **Security Headers**: HSTS, X-Frame-Options, CSP, etc. (via `SecurityHeadersMiddleware`)
- **Input Validation**: Strict Pydantic V2 schemas
- **CORS**: Restrictive origin list
- **Structured Logging**: All requests logged via `LoggingMiddleware`

## Adding New Features

### 1. Add a New Entity

```bash
# Create entity in domain layer
app/domain/entities/new_entity.py

# Create repository interface
app/domain/repositories/new_entity_repository.py

# Create repository implementation
app/infrastructure/database/repositories/new_entity_repository_impl.py

# If using SQLAlchemy models:
app/infrastructure/database/models/new_entity_model.py
```

### 2. Add a Use Case

```bash
# Create use case in domain layer
app/domain/use_cases/feature/action_name.py
```

### 3. Add API Endpoints

```bash
# Create endpoint router
app/presentation/api/v1/endpoints/feature.py

# Create Pydantic schemas
app/presentation/api/v1/schemas/feature.py

# Register router in app/presentation/api/router.py
```

### 4. Create Database Migration

```bash
# After updating SQLAlchemy models
poetry run alembic revision --autogenerate -m "Add new_table"
poetry run alembic upgrade head
```

## Dependency Injection

FastAPI dependencies are defined in `app/core/dependencies.py`. Common patterns:

- `get_current_user()`: Extracts and validates JWT, returns current user
- `get_current_active_user()`: Ensures user is active
- `require_role()`: Role-based access control decorator

Example:
```python
from app.core.dependencies import get_current_user, require_role

@router.get("/admin-only")
async def admin_endpoint(current_user: User = Depends(require_role("ADMIN"))):
    ...
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# Run migrations in container
docker-compose -f docker/docker-compose.yml exec app alembic upgrade head

# View logs
docker-compose -f docker/docker-compose.yml logs -f app
```

The Dockerfile uses:
- Python 3.11-slim base image
- Gunicorn with Uvicorn workers
- Port 8080 (configurable via `$PORT`)

## Common Patterns

### Async Repository Methods
All repository methods are async. Always use `await`:
```python
user = await user_repository.get_by_email(email)
```

### Error Handling
Use custom exceptions from `app/core/exceptions.py`:
- `EntityNotFoundError(entity="User", id=user_id)`
- `DuplicateEntityError(entity="User", field="email", value=email)`
- `InvalidCredentialsError()`
- `InsufficientPermissionsError(required_role="ADMIN")`
- `ValidationError(message="...")`

### Schema Inheritance
Schemas inherit from base classes in `app/presentation/api/v1/schemas/base.py` to ensure consistent structure.

## Testing Conventions

- Unit tests in `tests/unit/` (test pure functions, use cases)
- Integration tests in `tests/integration/` (test API endpoints)
- Use `pytest-asyncio` for async tests
- Mock external dependencies (Supabase, Redis) in unit tests
- Use test database for integration tests
- no agreges esta parte en el commit -  🤖 Generated with [Claude Code](https://claude.com/claude-code)                                                                                                                                               │
│                                                                                                                                                                                                                 │
│   Co-Authored-By: Claude <noreply@anthropic.com>"                                                                                                                                                               │
│   Create comprehensive commit
# 📦 Guía de Instalación - BandangWeb API

Esta guía te ayudará a configurar y ejecutar BandangWeb API en tu entorno local.

## 📋 Prerequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.11+** ([Descargar](https://www.python.org/downloads/))
- **Poetry** (gestor de dependencias) - [Instalación](#instalar-poetry)
- **Git** ([Descargar](https://git-scm.com/downloads))
- **Cuenta de Supabase** ([Crear cuenta gratis](https://supabase.com))

### Instalar Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

Verifica la instalación:
```bash
poetry --version
# Debería mostrar: Poetry (version 1.7.0 o superior)
```

---

## 🚀 Instalación Rápida

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/bandangapi.git
cd bandangapi
```

### 2. Configurar Variables de Entorno

Copia el archivo de ejemplo y edítalo con tus credenciales:

```bash
cp .env.example .env
```

Edita `.env` y configura las siguientes variables **obligatorias**:

```env
# Supabase (obtén estas credenciales desde https://app.supabase.com/project/_/settings/api)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key

# JWT Secret (genera una clave segura de mínimo 32 caracteres)
SECRET_KEY=tu-secret-key-super-segura-minimo-32-caracteres-aqui

# Entorno
ENVIRONMENT=development
DEBUG=True

# CORS (dominios permitidos, separados por coma)
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### 🔐 Generar SECRET_KEY Segura

```bash
# macOS/Linux
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Python (cualquier OS)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Instalar Dependencias

```bash
# Instalar todas las dependencias (producción + desarrollo)
poetry install

# Solo dependencias de producción
poetry install --only main
```

### 4. Ejecutar el Servidor de Desarrollo

```bash
# Opción 1: Usar el script de inicio (recomendado)
./start_dev.sh

# Opción 2: Comando directo
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en:
- 📍 **API**: http://localhost:8000
- 📚 **Documentación Swagger**: http://localhost:8000/api/docs
- 📖 **ReDoc**: http://localhost:8000/api/redoc
- 🔍 **Health Check**: http://localhost:8000/api/v1/health

---

## 🐳 Instalación con Docker (Alternativa)

Si prefieres usar Docker:

```bash
# Construir y ejecutar con Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# Ver logs
docker-compose -f docker/docker-compose.yml logs -f app

# Detener
docker-compose -f docker/docker-compose.yml down
```

---

## 🗄️ Configuración de Base de Datos (Opcional)

Si usas migraciones de Alembic:

```bash
# Ejecutar migraciones pendientes
poetry run alembic upgrade head

# Crear una nueva migración (después de modificar modelos)
poetry run alembic revision --autogenerate -m "Descripción del cambio"

# Ver historial de migraciones
poetry run alembic history

# Rollback última migración
poetry run alembic downgrade -1
```

---

## 🧪 Ejecutar Tests

```bash
# Ejecutar todos los tests
poetry run pytest

# Con reporte de cobertura
poetry run pytest --cov=app --cov-report=html

# Solo tests de integración
poetry run pytest tests/integration/

# Solo tests unitarios
poetry run pytest tests/unit/

# Ver reporte de cobertura en el navegador
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## 🔧 Herramientas de Desarrollo

### Formateo y Linting

```bash
# Formatear código con Black
poetry run black app/ tests/

# Lint con Ruff (auto-fix)
poetry run ruff check --fix app/ tests/

# Type checking con mypy
poetry run mypy app/
```

### Pre-commit Hooks (Recomendado)

```bash
# Instalar hooks de git
poetry run pre-commit install

# Ejecutar manualmente
poetry run pre-commit run --all-files
```

---

## 📦 Gestión de Dependencias con Poetry

### Agregar Nueva Dependencia

```bash
# Dependencia de producción
poetry add nombre-paquete

# Dependencia de desarrollo
poetry add --group dev nombre-paquete

# Con versión específica
poetry add "fastapi==0.110.0"
```

### Actualizar Dependencias

```bash
# Actualizar todas
poetry update

# Actualizar una específica
poetry update nombre-paquete

# Ver dependencias desactualizadas
poetry show --outdated
```

### Exportar requirements.txt (Si lo Necesitas)

```bash
# Para producción (sin dev dependencies)
poetry export -f requirements.txt --output requirements.txt --without-hashes --only main

# Con todas las dependencias
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

**Nota**: Los archivos `requirements*.txt` están en `.gitignore` porque Poetry es la fuente de verdad. Solo genera `requirements.txt` si lo necesitas para deployment en plataformas legacy.

---

## 🌍 Variables de Entorno Disponibles

| Variable | Descripción | Requerida | Ejemplo |
|----------|-------------|-----------|---------|
| `SUPABASE_URL` | URL de tu proyecto Supabase | ✅ | `https://abc.supabase.co` |
| `SUPABASE_KEY` | Anon/Public key de Supabase | ✅ | `eyJhbGc...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (admin) | ✅ | `eyJhbGc...` |
| `SECRET_KEY` | Secreto JWT (min 32 chars) | ✅ | `super-secret-key-32+` |
| `ENVIRONMENT` | Entorno (`development`/`production`) | ❌ | `development` |
| `DEBUG` | Modo debug | ❌ | `True` |
| `BACKEND_CORS_ORIGINS` | Dominios CORS (separados por coma) | ❌ | `http://localhost:3000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración access token | ❌ | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Duración refresh token | ❌ | `7` |

---

## 🚨 Troubleshooting

### Error: "No module named 'app'"

**Solución**: Asegúrate de ejecutar comandos con `poetry run`:
```bash
poetry run uvicorn app.main:app --reload
```

### Error: "SUPABASE_URL is required"

**Solución**: Verifica que `.env` existe y tiene las variables correctas:
```bash
cat .env | grep SUPABASE_URL
```

### Error: "Poetry not found"

**Solución**: Agrega Poetry al PATH o usa la ruta completa:
```bash
# macOS/Linux
export PATH="$HOME/.local/bin:$PATH"

# O reinstala Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### Tests Fallando

**Solución**: Asegúrate de tener las variables de entorno de test:
```bash
# Las variables de test están en tests/conftest.py
poetry run pytest -v
```

### Puerto 8000 ya en uso

**Solución**: Usa otro puerto:
```bash
PORT=3000 ./start_dev.sh
# O directamente:
poetry run uvicorn app.main:app --reload --port 3000
```

---

## 📚 Siguientes Pasos

Después de la instalación:

1. **Explora la documentación**: http://localhost:8000/api/docs
2. **Lee el README.md**: Para entender la arquitectura
3. **Revisa CLAUDE.md**: Guía para trabajar con el proyecto
4. **Ejecuta los tests**: `poetry run pytest`
5. **Crea tu primer endpoint**: Sigue los ejemplos en `app/presentation/api/v1/endpoints/`

---

## 🤝 Soporte

Si tienes problemas:

1. Revisa la sección [Troubleshooting](#-troubleshooting)
2. Consulta `CLAUDE.md` para detalles de arquitectura
3. Abre un issue en GitHub
4. Contacta al equipo de desarrollo

---

**¡Listo!** 🎉 Ya tienes BandangWeb API corriendo localmente.

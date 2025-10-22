# 🚀 Guía de Despliegue y Actualización en Supabase

## 📋 Tabla de Contenidos

- [Resumen de Cambios](#resumen-de-cambios)
- [Pre-requisitos](#pre-requisitos)
- [Paso 1: Actualizar Base de Datos](#paso-1-actualizar-base-de-datos)
- [Paso 2: Configurar RLS Policies](#paso-2-configurar-rls-policies)
- [Paso 3: Configurar Supabase Storage](#paso-3-configurar-supabase-storage)
- [Paso 4: Configurar Email Templates](#paso-4-configurar-email-templates)
- [Paso 5: Verificar Configuración](#paso-5-verificar-configuración)
- [Paso 6: Actualizar Variables de Entorno](#paso-6-actualizar-variables-de-entorno)
- [Troubleshooting](#troubleshooting)
- [Rollback](#rollback)

---

## 🎯 Resumen de Cambios

Esta guía documenta todos los cambios necesarios en Supabase para implementar las **Fases 1, 2 y 3** del proyecto BandangWeb API.

### Cambios Implementados:

| Fase | Descripción | Impacto en Supabase |
|------|-------------|---------------------|
| **Fase 1** | Correcciones Críticas de Seguridad | ✅ RLS Policies actualizadas |
| **Fase 2** | Mejoras Importantes | ✅ Nuevas funciones RPC, validación email |
| **Fase 3** | Supabase Storage | ✅ Nuevo bucket, Storage policies, trigger cleanup |

### ⚠️ IMPORTANTE - Cambios que Rompen Compatibilidad:

1. **Flujo de Registro Modificado**: Los usuarios ahora DEBEN confirmar su email antes de poder autenticarse
2. **Endpoints de Multimedia Protegidos**: Requieren autenticación (token válido)
3. **Nueva Columna en Tabla `multimedia`**: Se agregaron 4 columnas nuevas para Storage

---

## ✅ Pre-requisitos

Antes de comenzar, asegúrate de tener:

- [ ] Acceso al Dashboard de Supabase (https://app.supabase.com)
- [ ] Permisos de administrador en el proyecto
- [ ] Los archivos SQL del directorio `scripts/`:
  - `supabase_rls_setup.sql`
  - `supabase_storage_setup.sql`
- [ ] Backup reciente de la base de datos (recomendado)

### Crear Backup (Recomendado)

```bash
# Desde el Dashboard de Supabase:
# Settings → Database → Backups → Create Backup
```

---

## 📊 Paso 1: Actualizar Base de Datos

### 1.1. Verificar Tabla `profiles`

La tabla debe llamarse `profiles` (no `users`). Si tu tabla se llama `users`, ejecutar:

```sql
-- Renombrar tabla (solo si es necesario)
ALTER TABLE IF EXISTS public.users RENAME TO profiles;

-- Actualizar índices
ALTER INDEX IF EXISTS users_pkey RENAME TO profiles_pkey;
ALTER INDEX IF EXISTS users_email_key RENAME TO profiles_email_key;
ALTER INDEX IF EXISTS idx_users_role RENAME TO idx_profiles_role;
ALTER INDEX IF EXISTS idx_users_active RENAME TO idx_profiles_active;
```

### 1.2. Actualizar Tabla `multimedia`

Agregar nuevas columnas para Supabase Storage:

```sql
-- Agregar columnas para Storage
ALTER TABLE public.multimedia
ADD COLUMN IF NOT EXISTS storage_path TEXT,
ADD COLUMN IF NOT EXISTS file_size BIGINT,
ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);

-- Crear índice
CREATE INDEX IF NOT EXISTS idx_multimedia_storage_path
ON public.multimedia(storage_path);

-- Agregar comentarios descriptivos
COMMENT ON COLUMN public.multimedia.storage_path IS 'Ruta del archivo en el bucket (e.g., images/uuid.jpg)';
COMMENT ON COLUMN public.multimedia.file_size IS 'Tamaño del archivo en bytes';
COMMENT ON COLUMN public.multimedia.mime_type IS 'Tipo MIME del archivo (e.g., image/jpeg)';
COMMENT ON COLUMN public.multimedia.original_filename IS 'Nombre original del archivo subido';
```

### 1.3. Verificar Estado de la Migración

```sql
-- Verificar que las columnas existen
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'multimedia'
AND column_name IN ('storage_path', 'file_size', 'mime_type', 'original_filename')
ORDER BY ordinal_position;

-- Debe retornar 4 filas
```

**✅ Checkpoint**: Si ves 4 filas, las columnas se crearon correctamente.

---

## 🔒 Paso 2: Configurar RLS Policies

### 2.1. Ejecutar Script de RLS Policies

**Ubicación del script**: `scripts/supabase_rls_setup.sql`

**Pasos:**

1. Ir a: **Dashboard de Supabase → SQL Editor**
2. Crear nueva query
3. Copiar y pegar TODO el contenido de `supabase_rls_setup.sql`
4. Click en **Run**

### 2.2. Verificar Policies Creadas

```sql
-- Verificar policies de tabla profiles
SELECT
    policyname,
    cmd,
    permissive
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'profiles'
ORDER BY policyname;

-- Debe retornar 5 policies:
-- 1. Admins can update users
-- 2. Admins can view all users
-- 3. Superadmins can delete users
-- 4. Users can update own profile
-- 5. Users can view own profile
```

```sql
-- Verificar policies de tabla eventos
SELECT
    policyname,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'eventos'
ORDER BY policyname;

-- Debe retornar 4 policies:
-- 1. Admins can delete events
-- 2. Admins can update events
-- 3. Admins can view events
-- 4. Anyone can insert events
```

```sql
-- Verificar policies de tabla multimedia
SELECT
    policyname,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'multimedia'
ORDER BY policyname;

-- Debe retornar 4 policies:
-- 1. Admins can delete multimedia
-- 2. Admins can insert multimedia
-- 3. Admins can update multimedia
-- 4. Authenticated users can view all multimedia
```

**✅ Checkpoint**: Si ves el número correcto de policies en cada tabla, RLS está configurado.

### 2.3. Verificar Función RPC

```sql
-- Verificar que la función existe
SELECT
    proname,
    prosrc
FROM pg_proc
WHERE proname = 'get_user_by_email';

-- Debe retornar 1 fila
```

---

## 🗄️ Paso 3: Configurar Supabase Storage

### 3.1. Ejecutar Script de Storage Setup

**Ubicación del script**: `scripts/supabase_storage_setup.sql`

**Pasos:**

1. Ir a: **Dashboard de Supabase → SQL Editor**
2. Crear nueva query
3. Copiar y pegar TODO el contenido de `supabase_storage_setup.sql`
4. Click en **Run**

### 3.2. Verificar Bucket Creado

**Opción 1: Via SQL**

```sql
-- Verificar bucket
SELECT
    id,
    name,
    public,
    file_size_limit,
    array_length(allowed_mime_types, 1) as allowed_types_count
FROM storage.buckets
WHERE id = 'bandang-multimedia';

-- Debe retornar 1 fila:
-- id: bandang-multimedia
-- public: false
-- file_size_limit: 209715200 (200 MB)
-- allowed_types_count: 7
```

**Opción 2: Via Dashboard**

1. Ir a: **Storage** en el menú lateral
2. Verificar que existe el bucket **bandang-multimedia**
3. Configuración esperada:
   - Public: ❌ No
   - File size limit: 200 MB
   - Allowed MIME types: 7 tipos (image/jpeg, image/png, etc.)

### 3.3. Verificar Storage Policies

```sql
-- Verificar policies de Storage
SELECT
    policyname,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'storage'
AND tablename = 'objects'
AND policyname LIKE '%multimedia%'
ORDER BY policyname;

-- Debe retornar 4 policies:
-- 1. Admins can delete multimedia
-- 2. Admins can update multimedia
-- 3. Admins can upload multimedia
-- 4. Authenticated users can read multimedia
```

**✅ Checkpoint**: Si ves 4 policies de Storage, está configurado correctamente.

### 3.4. Verificar Trigger de Cleanup

```sql
-- Verificar que el trigger existe
SELECT
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE event_object_table = 'multimedia'
AND trigger_name = 'on_multimedia_delete_cleanup_storage';

-- Debe retornar 1 fila con evento DELETE
```

### 3.5. Probar Función de Cleanup (Opcional)

```sql
-- Listar archivos huérfanos (sin registro en DB)
SELECT * FROM cleanup_orphaned_storage_files();

-- Si es un proyecto nuevo, debe retornar 0 filas
```

---

## 📧 Paso 4: Configurar Email Templates

### 4.1. Habilitar Email Confirmation

1. Ir a: **Authentication → Settings → Email Auth**
2. Asegurarse de que **Enable email confirmations** está ✅ **ON**
3. Configurar:
   - **Confirm email**: ✅ Habilitado
   - **Secure email change**: ✅ Habilitado (recomendado)

### 4.2. Personalizar Email de Confirmación

1. Ir a: **Authentication → Email Templates**
2. Seleccionar: **Confirm signup**
3. Personalizar el template:

```html
<h2>¡Bienvenido a BandangWeb!</h2>

<p>Gracias por registrarte. Para completar tu registro, por favor confirma tu dirección de email haciendo clic en el siguiente enlace:</p>

<p>
  <a href="{{ .ConfirmationURL }}">Confirmar Email</a>
</p>

<p>Si no creaste esta cuenta, puedes ignorar este email.</p>

<p>
  Saludos,<br>
  El equipo de BandangWeb
</p>
```

4. Click en **Save**

### 4.3. Configurar Redirect URLs

1. Ir a: **Authentication → URL Configuration**
2. Agregar URLs de redirección permitidas:

```
https://bandanuevageneracion.com/auth/confirm
https://www.bandanuevageneracion.com/auth/confirm
http://localhost:3000/auth/confirm (para desarrollo)
```

**✅ Checkpoint**: Enviar un email de prueba registrando un usuario nuevo.

---

## ✅ Paso 5: Verificar Configuración

### 5.1. Script de Verificación Completo

Ejecutar este script para verificar que TODO está configurado:

```sql
-- ============================================================================
-- SCRIPT DE VERIFICACIÓN COMPLETA
-- ============================================================================

-- 1. Verificar tabla profiles
SELECT 'Tabla profiles' as check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.tables
           WHERE table_schema = 'public' AND table_name = 'profiles'
       ) THEN '✅ OK' ELSE '❌ FALTA' END as status;

-- 2. Verificar columnas nuevas en multimedia
SELECT 'Columnas Storage en multimedia' as check_name,
       CASE WHEN COUNT(*) = 4 THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'multimedia'
AND column_name IN ('storage_path', 'file_size', 'mime_type', 'original_filename');

-- 3. Verificar RLS habilitado
SELECT 'RLS en profiles' as check_name,
       CASE WHEN rowsecurity THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'profiles';

SELECT 'RLS en eventos' as check_name,
       CASE WHEN rowsecurity THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'eventos';

SELECT 'RLS en multimedia' as check_name,
       CASE WHEN rowsecurity THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'multimedia';

-- 4. Verificar policies de tabla
SELECT 'Policies de profiles' as check_name,
       CASE WHEN COUNT(*) = 5 THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'profiles';

SELECT 'Policies de eventos' as check_name,
       CASE WHEN COUNT(*) = 4 THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'eventos';

SELECT 'Policies de multimedia' as check_name,
       CASE WHEN COUNT(*) = 4 THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'multimedia';

-- 5. Verificar bucket de Storage
SELECT 'Bucket bandang-multimedia' as check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM storage.buckets WHERE id = 'bandang-multimedia'
       ) THEN '✅ OK' ELSE '❌ FALTA' END as status;

-- 6. Verificar Storage policies
SELECT 'Storage policies' as check_name,
       CASE WHEN COUNT(*) = 4 THEN '✅ OK' ELSE '❌ FALTA' END as status
FROM pg_policies
WHERE schemaname = 'storage'
AND tablename = 'objects'
AND policyname LIKE '%multimedia%';

-- 7. Verificar trigger de cleanup
SELECT 'Trigger cleanup Storage' as check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.triggers
           WHERE event_object_table = 'multimedia'
           AND trigger_name = 'on_multimedia_delete_cleanup_storage'
       ) THEN '✅ OK' ELSE '❌ FALTA' END as status;

-- 8. Verificar función RPC
SELECT 'Función get_user_by_email' as check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM pg_proc WHERE proname = 'get_user_by_email'
       ) THEN '✅ OK' ELSE '❌ FALTA' END as status;

-- 9. Verificar función cleanup
SELECT 'Función cleanup_orphaned_storage_files' as check_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM pg_proc WHERE proname = 'cleanup_orphaned_storage_files'
       ) THEN '✅ OK' ELSE '❌ FALTA' END as status;
```

**Resultado esperado**: Todas las filas deben mostrar `✅ OK`

---

## 🔧 Paso 6: Actualizar Variables de Entorno

### 6.1. Variables Requeridas en `.env`

```bash
# Supabase Configuration
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key-aqui
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-aqui

# API Configuration
SECRET_KEY=tu-secret-key-minimo-32-caracteres-aleatorios
ENVIRONMENT=production
DEBUG=False

# CORS Origins (separados por coma)
BACKEND_CORS_ORIGINS=https://bandanuevageneracion.com,https://www.bandanuevageneracion.com

# Token Configuration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Policy
PASSWORD_MIN_LENGTH=8
```

### 6.2. Obtener Claves de Supabase

1. Ir a: **Settings → API**
2. Copiar:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ SECRETO)

**⚠️ IMPORTANTE**: La `service_role key` bypasea RLS. Mantenerla SECRETA.

---

## 🧪 Paso 7: Pruebas de Funcionalidad

### Test 1: Registro de Usuario

```bash
curl -X POST https://tu-api.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Usuario de Prueba"
  }'

# Respuesta esperada (201 Created):
{
  "user": {
    "id": "uuid",
    "email": "test@example.com",
    "full_name": "Usuario de Prueba",
    "role": "USER",
    "is_active": true
  },
  "access_token": "",
  "refresh_token": "",
  "message": "Usuario registrado exitosamente. Por favor, confirma tu email antes de iniciar sesión."
}
```

**✅ Verificar**: El usuario debe recibir un email de confirmación.

### Test 2: Login sin Confirmar Email

```bash
curl -X POST https://tu-api.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Respuesta esperada (401 Unauthorized):
{
  "detail": "Email no confirmado. Por favor, verifica tu correo electrónico."
}
```

### Test 3: Acceso a Multimedia sin Token

```bash
curl https://tu-api.com/api/v1/multimedia/

# Respuesta esperada (401 Unauthorized):
{
  "detail": "Not authenticated"
}
```

---

## 🐛 Troubleshooting

### Problema: "relation 'users' does not exist"

**Solución**: Renombrar tabla `users` a `profiles`

```sql
ALTER TABLE public.users RENAME TO profiles;
```

### Problema: "bucket 'bandang-multimedia' already exists"

**Solución**: El bucket ya existe. Verificar policies:

```sql
SELECT * FROM pg_policies
WHERE schemaname = 'storage'
AND policyname LIKE '%multimedia%';
```

### Problema: Usuarios no reciben email de confirmación

**Verificar:**

1. **Authentication → Email Auth** → ✅ Enable email confirmations
2. **Authentication → Email Templates** → Confirm signup configurado
3. **Settings → API** → SMTP configurado (o usar Supabase default)

### Problema: Error al subir archivos a Storage

**Verificar:**

1. Bucket existe: `SELECT * FROM storage.buckets WHERE id = 'bandang-multimedia'`
2. Policies de Storage creadas (4 policies)
3. Usuario tiene rol ADMIN o SUPERADMIN

### Problema: RLS bloquea queries

**Verificar contexto de usuario:**

```sql
-- Verificar que el usuario está autenticado
SELECT auth.uid();

-- Verificar rol del usuario
SELECT role FROM public.profiles WHERE id = auth.uid();
```

---

## ⏮️ Rollback

Si necesitas revertir los cambios:

### Rollback Paso 1: Eliminar Columnas de Storage

```sql
ALTER TABLE public.multimedia
DROP COLUMN IF EXISTS storage_path,
DROP COLUMN IF EXISTS file_size,
DROP COLUMN IF EXISTS mime_type,
DROP COLUMN IF EXISTS original_filename;

DROP INDEX IF EXISTS idx_multimedia_storage_path;
```

### Rollback Paso 2: Eliminar RLS Policies

```sql
-- Profiles
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Admins can view all users" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Admins can update users" ON public.profiles;
DROP POLICY IF EXISTS "Superadmins can delete users" ON public.profiles;

-- Eventos
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;

-- Multimedia
DROP POLICY IF EXISTS "Authenticated users can view all multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can insert multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can update multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can delete multimedia" ON public.multimedia;
```

### Rollback Paso 3: Eliminar Storage

```sql
-- Eliminar trigger
DROP TRIGGER IF EXISTS on_multimedia_delete_cleanup_storage ON public.multimedia;
DROP FUNCTION IF EXISTS delete_storage_file_on_multimedia_delete();

-- Eliminar función cleanup
DROP FUNCTION IF EXISTS cleanup_orphaned_storage_files();

-- Eliminar Storage policies
DROP POLICY IF EXISTS "Admins can upload multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can read multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Admins can update multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Admins can delete multimedia" ON storage.objects;

-- Eliminar bucket (⚠️ esto eliminará TODOS los archivos)
DELETE FROM storage.buckets WHERE id = 'bandang-multimedia';
```

---

## 📚 Referencias

- [Documentación de RLS Policies](docs/database/schema.md#rls-policies)
- [Arquitectura de Storage](docs/supabase_storage_architecture.md)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase Storage](https://supabase.com/docs/guides/storage)

---

## ✅ Checklist Final

Antes de dar por completado el deployment:

- [ ] Tabla `profiles` existe y tiene RLS habilitado
- [ ] Tabla `multimedia` tiene las 4 columnas nuevas de Storage
- [ ] RLS policies creadas para `profiles` (5), `eventos` (4), `multimedia` (4)
- [ ] Bucket `bandang-multimedia` creado con 4 Storage policies
- [ ] Trigger de cleanup de Storage creado
- [ ] Función RPC `get_user_by_email` existe
- [ ] Email confirmation habilitado en Auth settings
- [ ] Email template personalizado
- [ ] Variables de entorno actualizadas
- [ ] Script de verificación ejecutado (todos ✅ OK)
- [ ] Pruebas funcionales completadas

---

## 🎉 ¡Deployment Completado!

Si todos los checkpoints están ✅, tu instancia de Supabase está lista para producción con:

- ✅ Seguridad mejorada (RLS policies completas)
- ✅ Validación de email obligatoria
- ✅ Supabase Storage configurado
- ✅ Cleanup automático de archivos
- ✅ Protección de endpoints

**Fecha de última actualización**: 2025-01-18
**Versión del documento**: 1.0.0

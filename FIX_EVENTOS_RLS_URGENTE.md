# FIX CRÍTICO: Habilitar INSERT Público en Tabla Eventos

## PROBLEMA

El endpoint público `POST /api/v1/events/` está fallando con error 500:

```
new row violates row-level security policy for table "eventos"
```

## CAUSA RAÍZ

La tabla `eventos` en Supabase tiene RLS (Row Level Security) habilitado, pero la política actual **SOLO permite INSERT a usuarios autenticados**. Sin embargo, el endpoint:

1. Es **público intencionalmente** (no requiere autenticación)
2. Usa `supabase_client.client` (no `admin_client`) para respetar RLS
3. Esto significa que usa el **rol anon** de Supabase
4. El rol anon NO puede insertar debido a la política restrictiva

Ver código: `app/infrastructure/database/repositories/event_repository_impl.py:46`

```python
# Usar cliente regular (RLS permite insertar eventos públicamente)
client = await self._supabase_client.client
```

## SOLUCIÓN

Ejecutar el script SQL que corrige las políticas RLS para:
- **Permitir INSERT público** (rol anon + authenticated)
- **Mantener SELECT/UPDATE/DELETE solo para ADMIN**

## ARCHIVOS CREADOS

### 1. Script SQL para ejecutar en Supabase

```
scripts/fix_eventos_rls.sql
```

### 2. Script Python auxiliar

```
scripts/fix_eventos_rls.py
```

### 3. Migración Alembic (no funcional - solo documentación)

```
alembic/versions/ecf5c4495f39_fix_eventos_rls_allow_public_insert.py
```

**NOTA:** La migración Alembic NO funciona porque el proyecto usa Supabase, no SQLAlchemy directo. Queda como documentación del cambio.

## PASOS PARA APLICAR FIX (URGENTE)

### Opción 1: Ejecutar SQL en Supabase UI (RECOMENDADO)

1. **Ve al SQL Editor de Supabase:**
   ```
   https://app.supabase.com/project/dvwagstnfveizuquqwmh/sql/new
   ```

2. **Copia y pega el contenido completo de:**
   ```
   scripts/fix_eventos_rls.sql
   ```

3. **Ejecuta el SQL** (botón "Run" o `Ctrl+Enter`)

4. **Verifica el resultado:**
   - Deberías ver 4 políticas creadas:
     - `Admins can delete events` (DELETE - authenticated)
     - `Admins can update events` (UPDATE - authenticated)
     - `Admins can view events` (SELECT - authenticated)
     - `Anyone can insert events` (INSERT - anon, authenticated) ← **CRÍTICA**

5. **Prueba el endpoint:**
   ```bash
   curl -X POST https://tu-api.com/api/v1/events/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Cliente",
       "email": "test@example.com",
       "phone": "1234567890",
       "event_type": "Boda",
       "event_date": "2025-12-31",
       "location": "Ciudad de México",
       "guest_count": "100-150",
       "message": "Solicitud de prueba"
     }'
   ```

   Deberías recibir `HTTP 201 Created`.

### Opción 2: Ejecutar script Python (genera SQL manual)

```bash
poetry run python scripts/fix_eventos_rls.py
```

**NOTA:** Este script NO aplica cambios automáticamente porque Supabase PostgREST no permite DDL via API. Genera el SQL que debes copiar manualmente.

## SQL COMPLETO A EJECUTAR

```sql
-- ============================================================================
-- CORRECCIÓN RLS CRÍTICA PARA TABLA EVENTOS
-- ============================================================================

-- 1. Limpiar políticas existentes
DROP POLICY IF EXISTS "Allow authenticated users to insert events" ON public.eventos;
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
DROP POLICY IF EXISTS "Allow authenticated users to view all events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;

-- 2. Crear política INSERT pública (CRÍTICA)
CREATE POLICY "Anyone can insert events"
ON public.eventos
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- 3. Crear política SELECT solo para ADMIN
CREATE POLICY "Admins can view events"
ON public.eventos
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- 4. Crear política UPDATE solo para ADMIN
CREATE POLICY "Admins can update events"
ON public.eventos
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- 5. Crear política DELETE solo para ADMIN
CREATE POLICY "Admins can delete events"
ON public.eventos
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- 6. Verificar que RLS está habilitado
ALTER TABLE public.eventos ENABLE ROW LEVEL SECURITY;

-- 7. Verificar políticas creadas
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'eventos'
ORDER BY policyname;
```

## CONSIDERACIONES DE SEGURIDAD

**PREGUNTA:** ¿Es seguro permitir INSERT público?

**RESPUESTA:** SÍ, porque:

1. **Rate Limiting:** El endpoint tiene rate limiting estricto:
   - 5 solicitudes por hora por IP
   - Implementado con `SlowAPI`

2. **Validación:** Todos los campos son validados con Pydantic:
   - Email válido (formato email)
   - Teléfono válido (solo dígitos)
   - Fecha futura (no permite eventos pasados)
   - Guest count dentro de rangos válidos

3. **Status Automático:** Todos los eventos se crean con `status='pending'`
   - Requieren revisión manual de un ADMIN
   - No son visibles públicamente

4. **Sin Datos Sensibles:** El formulario NO permite:
   - Modificar status
   - Establecer IDs manualmente
   - Acceder a otros eventos

5. **Protección RLS:** Solo ADMIN puede:
   - Ver eventos (SELECT)
   - Actualizar eventos (UPDATE)
   - Eliminar eventos (DELETE)

## ARCHIVO DE REFERENCIA CORRECTO

El archivo `scripts/supabase_rls_setup.sql` (líneas 79-136) YA contiene las políticas correctas. Parece que este archivo no se ejecutó en producción o se ejecutó un script diferente (`create_events_schema.sql`).

## ROLLBACK (en caso de necesidad)

Si necesitas revertir el cambio (NO RECOMENDADO en producción):

```sql
-- Volver a política restrictiva (solo authenticated)
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;

CREATE POLICY "Allow authenticated users to insert events"
ON public.eventos
FOR INSERT
TO authenticated
WITH CHECK (true);
```

**ADVERTENCIA:** Esto romperá el formulario público de cotizaciones.

## VERIFICACIÓN POST-FIX

Después de aplicar el fix, verifica:

1. **Políticas creadas correctamente:**
   ```sql
   SELECT policyname, cmd, roles
   FROM pg_policies
   WHERE tablename = 'eventos'
   ORDER BY policyname;
   ```

2. **Endpoint funciona sin autenticación:**
   ```bash
   curl -X POST https://tu-api.com/api/v1/events/ \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","email":"test@test.com","phone":"1234567890","event_type":"Boda","event_date":"2025-12-31","location":"CDMX","guest_count":"50-100"}'
   ```

3. **Rate limiting funciona:**
   ```bash
   # Ejecuta el comando anterior 6 veces seguidas
   # La 6ta solicitud debería recibir HTTP 429 (Too Many Requests)
   ```

4. **Admins pueden ver eventos:**
   ```bash
   curl -X GET https://tu-api.com/api/v1/events/ \
     -H "Authorization: Bearer <admin-token>"
   ```

5. **No admins NO pueden ver eventos:**
   ```bash
   curl -X GET https://tu-api.com/api/v1/events/
   # Sin token → HTTP 401 Unauthorized
   ```

## RESUMEN EJECUTIVO

- **Problema:** Endpoint público falla por política RLS restrictiva
- **Causa:** Solo permite INSERT a usuarios autenticados, pero endpoint usa rol anon
- **Solución:** Crear política que permite INSERT a anon + authenticated
- **Seguridad:** Protegido por rate limiting (5 req/hour) + validación Pydantic
- **Acción:** Ejecutar `scripts/fix_eventos_rls.sql` en Supabase SQL Editor
- **Urgencia:** CRÍTICA - formulario de cotizaciones no funciona actualmente

## LINKS DIRECTOS

- **Supabase SQL Editor:**
  https://app.supabase.com/project/dvwagstnfveizuquqwmh/sql/new

- **Supabase Table Editor (eventos):**
  https://app.supabase.com/project/dvwagstnfveizuquqwmh/editor/eventos

- **Supabase Authentication (RLS Policies):**
  https://app.supabase.com/project/dvwagstnfveizuquqwmh/auth/policies

---

**Creado:** 2025-11-07
**Prioridad:** CRÍTICA
**Status:** PENDIENTE APLICACIÓN
**Impacto:** Formulario de cotizaciones público no funciona

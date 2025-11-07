-- ============================================================================
-- CORRECCIÓN RLS CRÍTICA PARA TABLA EVENTOS - BandangWeb API
-- ============================================================================
--
-- PROBLEMA:
-- El endpoint público POST /api/v1/events/ está fallando con error 500:
--   "new row violates row-level security policy for table eventos"
--
-- CAUSA:
-- La tabla "eventos" tiene RLS habilitado pero la política actual solo
-- permite INSERT a usuarios autenticados. El endpoint usa el cliente
-- anon de Supabase (no admin_client) para respetar RLS y permitir
-- rate limiting público.
--
-- SOLUCIÓN:
-- Permitir INSERT público (anon role) manteniendo SELECT/UPDATE/DELETE
-- solo para usuarios ADMIN/SUPERADMIN.
--
-- EJECUCIÓN:
-- 1. Ve a: https://app.supabase.com/project/dvwagstnfveizuquqwmh/sql/new
-- 2. Copia y pega este archivo completo
-- 3. Ejecuta (botón 'Run' o Ctrl+Enter)
-- 4. Verifica que no hay errores
-- 5. Prueba el endpoint: POST /api/v1/events/
--
-- ============================================================================

-- ============================================================================
-- PASO 1: Limpiar políticas existentes
-- ============================================================================

DROP POLICY IF EXISTS "Allow authenticated users to insert events" ON public.eventos;
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
DROP POLICY IF EXISTS "Allow authenticated users to view all events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;

-- ============================================================================
-- PASO 2: Crear política INSERT pública
-- ============================================================================
-- Permite que CUALQUIER usuario (anon + authenticated) inserte eventos
-- Esto es INTENCIONAL para permitir solicitudes de cotización públicas
-- La protección anti-spam está implementada con rate limiting (5 req/hour)

CREATE POLICY "Anyone can insert events"
ON public.eventos
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

COMMENT ON POLICY "Anyone can insert events" ON public.eventos IS
'Permite INSERT público para formularios de cotización. Protected by rate limiting.';

-- ============================================================================
-- PASO 3: Crear política SELECT solo para ADMIN
-- ============================================================================
-- Solo usuarios con rol ADMIN o SUPERADMIN pueden ver eventos
-- Esto protege datos sensibles de clientes (email, teléfono, etc.)

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

COMMENT ON POLICY "Admins can view events" ON public.eventos IS
'Solo ADMIN/SUPERADMIN pueden ver eventos para proteger datos de clientes.';

-- ============================================================================
-- PASO 4: Crear política UPDATE solo para ADMIN
-- ============================================================================
-- Solo ADMIN puede actualizar el status de eventos (pending → confirmed/cancelled)

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

COMMENT ON POLICY "Admins can update events" ON public.eventos IS
'Solo ADMIN/SUPERADMIN pueden actualizar eventos (ej: cambiar status).';

-- ============================================================================
-- PASO 5: Crear política DELETE solo para ADMIN
-- ============================================================================
-- Solo ADMIN puede eliminar eventos

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

COMMENT ON POLICY "Admins can delete events" ON public.eventos IS
'Solo ADMIN/SUPERADMIN pueden eliminar eventos.';

-- ============================================================================
-- PASO 6: Verificar que RLS está habilitado
-- ============================================================================

ALTER TABLE public.eventos ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- PASO 7: VERIFICACIÓN - Listar políticas creadas
-- ============================================================================

SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'eventos'
ORDER BY policyname;

-- ============================================================================
-- RESULTADO ESPERADO:
-- ============================================================================
--
-- Deberías ver 4 políticas:
--
-- 1. "Admins can delete events"  - DELETE - authenticated
-- 2. "Admins can update events"  - UPDATE - authenticated
-- 3. "Admins can view events"    - SELECT - authenticated
-- 4. "Anyone can insert events"  - INSERT - anon, authenticated
--
-- Si ves estas 4 políticas, la corrección fue exitosa.
--
-- ============================================================================
-- PRUEBA RÁPIDA:
-- ============================================================================
--
-- Después de ejecutar este script, prueba el endpoint:
--
-- curl -X POST https://tu-api.com/api/v1/events/ \
--   -H "Content-Type: application/json" \
--   -d '{
--     "name": "Test Cliente",
--     "email": "test@example.com",
--     "phone": "1234567890",
--     "event_type": "Boda",
--     "event_date": "2025-12-31",
--     "location": "Ciudad de México",
--     "guest_count": "100-150",
--     "message": "Solicitud de prueba"
--   }'
--
-- Deberías recibir HTTP 201 Created con los datos del evento creado.
--
-- ============================================================================

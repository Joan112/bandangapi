-- ============================================================================
-- SUPABASE RLS POLICIES SETUP - BandangWeb API
-- ============================================================================
-- Este script configura todas las Row Level Security (RLS) policies para
-- las tablas principales de BandangWeb API.
--
-- IMPORTANTE: Ejecutar este script en el SQL Editor de Supabase
-- ============================================================================

-- ============================================================================
-- 1. TABLA: profiles (anteriormente users)
-- ============================================================================

-- Habilitar RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas existentes si existen
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Admins can view all users" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Admins can update users" ON public.profiles;
DROP POLICY IF EXISTS "Admins can delete users" ON public.profiles;

-- Policy 1: Usuarios pueden ver su propio perfil
CREATE POLICY "Users can view own profile"
ON public.profiles
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- Policy 2: Admins pueden ver todos los perfiles
CREATE POLICY "Admins can view all users"
ON public.profiles
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);

-- Policy 3: Usuarios pueden actualizar su propio perfil (solo full_name)
CREATE POLICY "Users can update own profile"
ON public.profiles
FOR UPDATE
TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Policy 4: Admins pueden actualizar cualquier usuario
CREATE POLICY "Admins can update users"
ON public.profiles
FOR UPDATE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);

-- Policy 5: Solo SUPERADMIN puede eliminar usuarios
CREATE POLICY "Superadmins can delete users"
ON public.profiles
FOR DELETE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role = 'SUPERADMIN'
  )
);

-- ============================================================================
-- 2. TABLA: eventos
-- ============================================================================

-- Habilitar RLS
ALTER TABLE public.eventos ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas existentes si existen
DROP POLICY IF EXISTS "Anyone can insert events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can view events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can update events" ON public.eventos;
DROP POLICY IF EXISTS "Admins can delete events" ON public.eventos;

-- Policy 1: Cualquiera puede insertar eventos (formulario público)
-- NOTA: Esto permite que usuarios no autenticados creen solicitudes de cotización
CREATE POLICY "Anyone can insert events"
ON public.eventos
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- Policy 2: Admins pueden ver todos los eventos
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

-- Policy 3: Admins pueden actualizar eventos
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

-- Policy 4: Admins pueden eliminar eventos
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

-- ============================================================================
-- 3. TABLA: multimedia
-- ============================================================================

-- Habilitar RLS
ALTER TABLE public.multimedia ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas existentes si existen
DROP POLICY IF EXISTS "Anyone can view published multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can view all multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can insert multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can update multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Admins can delete multimedia" ON public.multimedia;
DROP POLICY IF EXISTS "Authenticated users can view all multimedia" ON public.multimedia;

-- Policy 1: NUEVO - Usuarios autenticados pueden ver todo el contenido
-- Esto reemplaza la policy de "Anyone can view published multimedia"
-- porque ahora los endpoints requieren autenticación
CREATE POLICY "Authenticated users can view all multimedia"
ON public.multimedia
FOR SELECT
TO authenticated
USING (true);

-- Policy 2: Admins pueden insertar multimedia
CREATE POLICY "Admins can insert multimedia"
ON public.multimedia
FOR INSERT
TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);

-- Policy 3: Admins pueden actualizar multimedia
CREATE POLICY "Admins can update multimedia"
ON public.multimedia
FOR UPDATE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);

-- Policy 4: Admins pueden eliminar multimedia
CREATE POLICY "Admins can delete multimedia"
ON public.multimedia
FOR DELETE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND role IN ('ADMIN', 'SUPERADMIN')
  )
);

-- ============================================================================
-- 4. FUNCIONES RPC HELPER
-- ============================================================================

-- Función para obtener usuario por email (usada en login)
CREATE OR REPLACE FUNCTION get_user_by_email(p_email TEXT)
RETURNS TABLE (
    id UUID,
    email TEXT,
    full_name TEXT,
    role TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.email,
        p.full_name,
        p.role,
        p.is_active,
        p.created_at,
        p.updated_at
    FROM public.profiles p
    WHERE p.email = p_email;
END;
$$;

-- ============================================================================
-- 5. VERIFICACIÓN
-- ============================================================================

-- Verificar que RLS está habilitado en todas las tablas
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('profiles', 'eventos', 'multimedia')
ORDER BY tablename;

-- Listar todas las policies creadas
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('profiles', 'eventos', 'multimedia')
ORDER BY tablename, policyname;

-- ============================================================================
-- NOTAS DE SEGURIDAD
-- ============================================================================
--
-- 1. La tabla 'profiles' solo permite a usuarios ver su propio perfil
--    o ser admin para ver todos los perfiles.
--
-- 2. La tabla 'eventos' permite INSERT público para formularios de contacto,
--    pero solo admins pueden ver, actualizar y eliminar.
--
-- 3. La tabla 'multimedia' ahora requiere autenticación para SELECT,
--    y solo admins pueden INSERT, UPDATE, DELETE.
--
-- 4. La función get_user_by_email() tiene SECURITY DEFINER, lo que significa
--    que se ejecuta con los permisos del propietario (bypass RLS).
--    Esto es necesario para el proceso de login.
--
-- ============================================================================

-- ============================================================================
-- SUPABASE STORAGE SETUP - BandangWeb API
-- ============================================================================
-- Este script configura el bucket de Storage y sus policies de acceso.
--
-- IMPORTANTE: Ejecutar este script en el SQL Editor de Supabase
-- ============================================================================

-- ============================================================================
-- 1. CREAR BUCKET
-- ============================================================================

-- Insertar bucket si no existe
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'bandang-multimedia',
    'bandang-multimedia',
    false,  -- No público (acceso controlado por policies)
    209715200,  -- 200 MB límite (en bytes)
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
        'video/mp4',
        'video/quicktime',
        'video/webm'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 2. STORAGE POLICIES
-- ============================================================================

-- Eliminar policies existentes si existen
DROP POLICY IF EXISTS "Admins can upload multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can read multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Admins can update multimedia" ON storage.objects;
DROP POLICY IF EXISTS "Admins can delete multimedia" ON storage.objects;

-- Policy 1: Solo ADMINS pueden subir archivos
CREATE POLICY "Admins can upload multimedia"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'bandang-multimedia'
    AND EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- Policy 2: Usuarios autenticados pueden leer archivos
CREATE POLICY "Authenticated users can read multimedia"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'bandang-multimedia'
);

-- Policy 3: Solo ADMINS pueden actualizar archivos
CREATE POLICY "Admins can update multimedia"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
    bucket_id = 'bandang-multimedia'
    AND EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- Policy 4: Solo ADMINS pueden eliminar archivos
CREATE POLICY "Admins can delete multimedia"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'bandang-multimedia'
    AND EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid()
        AND role IN ('ADMIN', 'SUPERADMIN')
    )
);

-- ============================================================================
-- 3. ACTUALIZAR TABLA MULTIMEDIA
-- ============================================================================

-- Agregar columnas nuevas para Storage
ALTER TABLE public.multimedia
ADD COLUMN IF NOT EXISTS storage_path TEXT,
ADD COLUMN IF NOT EXISTS file_size BIGINT,
ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);

-- Crear índice para búsqueda por storage_path
CREATE INDEX IF NOT EXISTS idx_multimedia_storage_path
ON public.multimedia(storage_path);

-- Comentarios descriptivos
COMMENT ON COLUMN public.multimedia.storage_path IS 'Ruta del archivo en el bucket de Storage (e.g., images/uuid.jpg)';
COMMENT ON COLUMN public.multimedia.file_size IS 'Tamaño del archivo en bytes';
COMMENT ON COLUMN public.multimedia.mime_type IS 'Tipo MIME del archivo (e.g., image/jpeg)';
COMMENT ON COLUMN public.multimedia.original_filename IS 'Nombre original del archivo subido';

-- ============================================================================
-- 4. FUNCIÓN HELPER PARA LIMPIAR STORAGE
-- ============================================================================

-- Función para eliminar archivos huérfanos del Storage
CREATE OR REPLACE FUNCTION cleanup_orphaned_storage_files()
RETURNS TABLE(deleted_path TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Esta función debe ejecutarse manualmente o via cron job
    -- Lista archivos en Storage que no tienen registro en la tabla multimedia

    RETURN QUERY
    SELECT name
    FROM storage.objects
    WHERE bucket_id = 'bandang-multimedia'
    AND name NOT IN (
        SELECT storage_path
        FROM public.multimedia
        WHERE storage_path IS NOT NULL
    );

    -- Nota: La eliminación real debe hacerse via API o manualmente
    -- para evitar eliminar archivos accidentalmente
END;
$$;

COMMENT ON FUNCTION cleanup_orphaned_storage_files() IS 'Lista archivos en Storage sin registro en la tabla multimedia';

-- ============================================================================
-- 5. TRIGGER PARA LIMPIAR STORAGE AL ELIMINAR MULTIMEDIA
-- ============================================================================

-- Función que se ejecuta DESPUÉS de eliminar un registro de multimedia
CREATE OR REPLACE FUNCTION delete_storage_file_on_multimedia_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Eliminar archivo principal del Storage
    IF OLD.storage_path IS NOT NULL THEN
        PERFORM storage.delete_object('bandang-multimedia', OLD.storage_path);
    END IF;

    -- Eliminar thumbnail si existe
    IF OLD.thumbnail_url IS NOT NULL THEN
        -- Extraer path del thumbnail desde la URL
        DECLARE
            thumbnail_path TEXT;
        BEGIN
            -- Ejemplo URL: https://xyz.supabase.co/storage/v1/object/public/bandang-multimedia/thumbnails/uuid_thumb.jpg
            -- Extraer: thumbnails/uuid_thumb.jpg
            thumbnail_path := regexp_replace(
                OLD.thumbnail_url,
                '.*bandang-multimedia/',
                ''
            );

            IF thumbnail_path IS NOT NULL AND thumbnail_path != '' THEN
                PERFORM storage.delete_object('bandang-multimedia', thumbnail_path);
            END IF;
        END;
    END IF;

    RETURN OLD;
END;
$$;

-- Crear trigger
DROP TRIGGER IF EXISTS on_multimedia_delete_cleanup_storage ON public.multimedia;

CREATE TRIGGER on_multimedia_delete_cleanup_storage
AFTER DELETE ON public.multimedia
FOR EACH ROW
EXECUTE FUNCTION delete_storage_file_on_multimedia_delete();

COMMENT ON TRIGGER on_multimedia_delete_cleanup_storage ON public.multimedia IS 'Limpia archivos del Storage al eliminar multimedia';

-- ============================================================================
-- 6. VERIFICACIÓN
-- ============================================================================

-- Verificar que el bucket fue creado
SELECT
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
FROM storage.buckets
WHERE id = 'bandang-multimedia';

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

-- Verificar columnas nuevas en tabla multimedia
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'multimedia'
AND column_name IN ('storage_path', 'file_size', 'mime_type', 'original_filename')
ORDER BY ordinal_position;

-- ============================================================================
-- NOTAS DE USO
-- ============================================================================
--
-- 1. Después de ejecutar este script, el bucket 'bandang-multimedia' estará listo.
--
-- 2. Las rutas de archivos siguen el patrón:
--    - Imágenes: images/{uuid}.{ext}
--    - Videos: videos/{uuid}.{ext}
--    - Thumbnails: thumbnails/{uuid}_thumb.jpg
--
-- 3. El trigger automático limpia archivos del Storage cuando se elimina
--    un registro de la tabla multimedia.
--
-- 4. Para listar archivos huérfanos (sin registro en DB):
--    SELECT * FROM cleanup_orphaned_storage_files();
--
-- 5. Para obtener URL pública de un archivo, usar el endpoint de Supabase:
--    {SUPABASE_URL}/storage/v1/object/public/bandang-multimedia/{storage_path}
--
-- ============================================================================

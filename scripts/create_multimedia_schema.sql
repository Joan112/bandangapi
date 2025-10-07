-- Esquema para la tabla de Multimedia

-- 1. Crear tabla para contenido multimedia
CREATE TABLE public.multimedia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL CHECK (type IN ('image', 'video')),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    thumbnail TEXT,
    category TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    featured BOOLEAN NOT NULL DEFAULT false,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    size BIGINT,
    width INTEGER,
    height INTEGER,
    duration INTEGER,
    is_published BOOLEAN NOT NULL DEFAULT false,
    "order" INTEGER NOT NULL DEFAULT 0
);

-- 2. Añadir comentarios a la tabla y columnas
COMMENT ON TABLE public.multimedia IS 'Almacena el contenido multimedia (imágenes y videos)';
COMMENT ON COLUMN public.multimedia.id IS 'Identificador único del contenido multimedia (UUID)';
COMMENT ON COLUMN public.multimedia.type IS 'Tipo de contenido (image o video)';
COMMENT ON COLUMN public.multimedia.title IS 'Título descriptivo del contenido';
COMMENT ON COLUMN public.multimedia.description IS 'Descripción detallada del contenido';
COMMENT ON COLUMN public.multimedia.url IS 'URL del recurso multimedia';
COMMENT ON COLUMN public.multimedia.thumbnail IS 'URL de la miniatura (especialmente para videos)';
COMMENT ON COLUMN public.multimedia.category IS 'Categoría del contenido (conciertos, ensayos, promocionales, etc.)';
COMMENT ON COLUMN public.multimedia.tags IS 'Etiquetas para facilitar búsquedas';
COMMENT ON COLUMN public.multimedia.featured IS 'Indica si está destacado en la página principal';
COMMENT ON COLUMN public.multimedia.uploaded_at IS 'Fecha y hora de subida del contenido';
COMMENT ON COLUMN public.multimedia.updated_at IS 'Fecha y hora de última actualización';
COMMENT ON COLUMN public.multimedia.created_by IS 'ID del usuario que subió el contenido';
COMMENT ON COLUMN public.multimedia.size IS 'Tamaño del archivo en bytes';
COMMENT ON COLUMN public.multimedia.width IS 'Ancho de la imagen en píxeles';
COMMENT ON COLUMN public.multimedia.height IS 'Alto de la imagen en píxeles';
COMMENT ON COLUMN public.multimedia.duration IS 'Duración del video en segundos';
COMMENT ON COLUMN public.multimedia.is_published IS 'Estado de publicación del contenido';
COMMENT ON COLUMN public.multimedia."order" IS 'Orden de aparición en la galería';

-- 3. Crear índices para mejorar el rendimiento
CREATE INDEX idx_multimedia_type ON public.multimedia(type);
CREATE INDEX idx_multimedia_category ON public.multimedia(category);
CREATE INDEX idx_multimedia_featured ON public.multimedia(featured);
CREATE INDEX idx_multimedia_is_published ON public.multimedia(is_published);
CREATE INDEX idx_multimedia_created_by ON public.multimedia(created_by);
CREATE INDEX idx_multimedia_tags ON public.multimedia USING GIN(tags);

-- 4. Crear la función para actualizar el timestamp de `updated_at`
CREATE OR REPLACE FUNCTION public.handle_multimedia_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Crear el trigger que actualiza `updated_at`
CREATE TRIGGER on_multimedia_updated
BEFORE UPDATE ON public.multimedia
FOR EACH ROW
EXECUTE FUNCTION public.handle_multimedia_updated_at();

-- 6. Habilitar Row Level Security (RLS)
ALTER TABLE public.multimedia ENABLE ROW LEVEL SECURITY;

-- 7. Políticas de RLS
-- Permitir a usuarios autenticados insertar contenido
CREATE POLICY "Allow authenticated users to insert multimedia"
ON public.multimedia
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Permitir a todos ver contenido publicado
CREATE POLICY "Allow everyone to view published multimedia"
ON public.multimedia
FOR SELECT
USING (is_published = true);

-- Permitir a usuarios autenticados ver todo el contenido
CREATE POLICY "Allow authenticated users to view all multimedia"
ON public.multimedia
FOR SELECT
TO authenticated
USING (true);

-- Permitir a los creadores actualizar su propio contenido
CREATE POLICY "Allow creators to update their own multimedia"
ON public.multimedia
FOR UPDATE
TO authenticated
USING (created_by = auth.uid())
WITH CHECK (created_by = auth.uid());

-- Permitir a los creadores eliminar su propio contenido
CREATE POLICY "Allow creators to delete their own multimedia"
ON public.multimedia
FOR DELETE
TO authenticated
USING (created_by = auth.uid());

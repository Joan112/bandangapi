-- Esquema para la tabla de Eventos

-- 1. Crear la tabla para los eventos
CREATE TABLE public.eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date DATE NOT NULL,
    location TEXT NOT NULL,
    guest_count TEXT NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Añadir comentarios a la tabla y columnas para mayor claridad
COMMENT ON TABLE public.eventos IS 'Almacena la información de los eventos de los clientes.';
COMMENT ON COLUMN public.eventos.id IS 'Identificador único del evento (UUID)';
COMMENT ON COLUMN public.eventos.name IS 'Nombre del cliente';
COMMENT ON COLUMN public.eventos.email IS 'Correo electrónico del cliente';
COMMENT ON COLUMN public.eventos.phone IS 'Teléfono de contacto del cliente';
COMMENT ON COLUMN public.eventos.event_type IS 'Tipo de evento (Boda, XV Años, etc.)';
COMMENT ON COLUMN public.eventos.event_date IS 'Fecha del evento';
COMMENT ON COLUMN public.eventos.location IS 'Ubicación del evento';
COMMENT ON COLUMN public.eventos.guest_count IS 'Cantidad de invitados';
COMMENT ON COLUMN public.eventos.message IS 'Mensaje o notas adicionales del cliente';
COMMENT ON COLUMN public.eventos.status IS 'Estado actual del evento (pending, confirmed, cancelled)';
COMMENT ON COLUMN public.eventos.created_at IS 'Fecha y hora de creación del registro';
COMMENT ON COLUMN public.eventos.updated_at IS 'Fecha y hora de la última actualización del registro';

-- 3. Crear la función para actualizar el timestamp de `updated_at`
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Crear el trigger que utiliza la función anterior en cada actualización
CREATE TRIGGER on_eventos_updated
BEFORE UPDATE ON public.eventos
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- 5. Habilitar Row Level Security (RLS) para la tabla
ALTER TABLE public.eventos ENABLE ROW LEVEL SECURITY;

-- 6. Crear políticas de RLS
-- Política para permitir a los usuarios autenticados insertar eventos
CREATE POLICY "Allow authenticated users to insert events"
ON public.eventos
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Política para permitir a los usuarios ver sus propios eventos (si se implementa la lógica de user_id)
-- CREATE POLICY "Allow users to view their own events"
-- ON public.eventos
-- FOR SELECT
-- USING (auth.uid() = user_id);
-- NOTA: Se necesitaría una columna `user_id UUID REFERENCES auth.users(id)` en la tabla `eventos`.

-- Política para permitir a los administradores acceso total (ejemplo)
-- CREATE POLICY "Allow admin users full access"
-- ON public.eventos
-- FOR ALL
-- TO authenticated
-- USING (
--   (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin'
-- );

-- Por ahora, una política de selección simple para usuarios autenticados.
CREATE POLICY "Allow authenticated users to view all events"
ON public.eventos
FOR SELECT
TO authenticated
USING (true);

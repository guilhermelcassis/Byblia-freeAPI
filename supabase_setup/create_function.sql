-- Função para inserir interações ignorando as políticas RLS
CREATE OR REPLACE FUNCTION public.insert_interaction(
    p_user_prompt TEXT,
    p_model VARCHAR,
    p_timestamp TIMESTAMPTZ,
    p_temperature FLOAT8,
    p_message TEXT,
    p_token_usage INT4,
    p_interaction_number INT4
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER -- Isso faz com que a função seja executada com os privilégios do criador
AS $$
BEGIN
    INSERT INTO public.interactions(
        user_prompt,
        model,
        timestamp,
        temperature,
        message,
        token_usage,
        interaction_number
    ) VALUES (
        p_user_prompt,
        p_model,
        p_timestamp,
        p_temperature,
        p_message,
        p_token_usage,
        p_interaction_number
    );
END;
$$;

-- Garante que a função possa ser executada por todos
GRANT EXECUTE ON FUNCTION public.insert_interaction TO anon, authenticated, service_role;

-- Desabilita RLS para administradores (opcional)
ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;

-- Cria uma política que permite leitura para todos
CREATE POLICY "Allow select for everyone" ON public.interactions
    FOR SELECT
    USING (true);
    
-- Cria uma política que permite inserção para usuários autenticados
CREATE POLICY "Allow insert for authenticated users" ON public.interactions
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated'); 
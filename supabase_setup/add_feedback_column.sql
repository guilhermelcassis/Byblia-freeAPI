-- Adicionar coluna de avaliação do usuário à tabela interactions
ALTER TABLE public.interactions ADD COLUMN user_feedback BOOLEAN DEFAULT NULL;

-- Criar função RPC para atualizar o feedback
CREATE OR REPLACE FUNCTION public.update_interaction_feedback(
    p_interaction_id INT8,
    p_user_feedback BOOLEAN
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE public.interactions
    SET user_feedback = p_user_feedback
    WHERE id = p_interaction_id;
END;
$$;

-- Garantir permissões para a função
GRANT EXECUTE ON FUNCTION public.update_interaction_feedback TO anon, authenticated, service_role; 
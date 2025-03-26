# Supabase Setup Guide

This guide covers how to set up Supabase for your FastAPI chat application.

## 1. Prerequisites

- A Supabase account (you can sign up at [supabase.com](https://supabase.com))
- Your Supabase project URL: `https://fsoawtkezlwivfpmqtja.supabase.co`
- Your Supabase API key (available in your Supabase project dashboard)

## 2. Setting Up Your Environment

1. Create a `.env` file in the root of your project based on the `.env.example` file
2. Add your Supabase credentials:
   ```
   SUPABASE_URL=https://fsoawtkezlwivfpmqtja.supabase.co
   SUPABASE_KEY=your_supabase_api_key
   ```

## 3. Creating the Database Table

In your Supabase dashboard:

1. Go to the "Table Editor" section
2. Click "Create a new table"
3. Name the table `interactions`
4. Add the following columns:

| Name              | Type      | Default Value | Primary | Is Nullable |
|-------------------|-----------|---------------|---------|-------------|
| id                | int8      | (auto)        | Yes     | No          |
| user_prompt       | text      |               | No      | No          |
| model             | varchar   |               | No      | No          |
| timestamp         | timestamptz | now()       | No      | No          |
| temperature       | float8    |               | No      | No          |
| message           | text      |               | No      | No          |
| token_usage       | int4      |               | No      | No          |
| interaction_number| int4      |               | No      | No          |

## 4. Configurando as Políticas de Segurança (RLS)

Para permitir que a API insira dados na tabela `interactions` seguindo as melhores práticas de segurança, você precisa configurar corretamente as Row-Level Security policies.

1. Vá até a interface de SQL do Supabase (SQL Editor)
2. Copie e cole o código do arquivo `supabase_setup/create_function.sql`
3. Execute o script

Isso criará:
- Uma função RPC com `SECURITY DEFINER` que permite inserir dados de forma segura
- Políticas RLS que permitem leitura e inserção controladas

> **Importante**: Nunca desabilite o RLS nas tabelas. Isso é uma prática insegura que pode comprometer todos os seus dados. A função RPC criada pelo script fornece uma maneira segura de inserir dados enquanto mantém a proteção do RLS.

## 5. API Usage

The API now uses Supabase for data storage. No changes are needed in how you call the API endpoints.

## 6. Security Considerations

- Keep your Supabase API key secure and never commit it to version control
- Use Row-Level Security (RLS) policies in Supabase for additional security
- Consider using a service account key for production use

## 7. Troubleshooting

If you encounter issues:

1. Check that your environment variables are set correctly
2. Verify your Supabase API key has the correct permissions
3. Ensure the `interactions` table exists with the correct schema
4. Check the application logs for detailed error messages

## 8. Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [supabase-py Documentation](https://github.com/supabase-community/supabase-py)
- [FastAPI Documentation](https://fastapi.tiangolo.com/) 
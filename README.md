# AI Chat API com Supabase

API para interação com modelos de IA e armazenamento de histórico de conversas usando FastAPI e Supabase.

## Visão Geral

Este projeto implementa uma API RESTful que permite:
- Interagir com modelos de IA (DeepSeek) para gerar respostas de chat
- Armazenar histórico de interações no Supabase
- Controlar a temperatura de forma automática no backend

## Tecnologias

- **Backend**: FastAPI (Python)
- **Banco de Dados**: Supabase (PostgreSQL)
- **Modelo de IA**: DeepSeek via pydantic-ai

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/guilhermelcassis/api-byblia.git
   cd api-byblia
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure o Supabase:
   - Siga o guia em `SUPABASE_SETUP.md`
   - Execute o script SQL para configurar as políticas de segurança RLS

4. Configure as variáveis de ambiente:
   - Crie um arquivo `.env` baseado no `.env.example`
   - Adicione suas credenciais DeepSeek e Supabase

## Executando o Projeto

Para iniciar o servidor em modo de desenvolvimento:
```bash
python run.py
```

Ou diretamente com uvicorn:
```bash
uvicorn app.main:app --reload
```

## Endpoints da API

### Chat

**Endpoint**: `POST /api/chat`

**Corpo da Requisição**:
```json
{
  "prompt": "Sua pergunta aqui"
}
```

**Resposta**:
```json
{
  "message": "Resposta do modelo de IA",
  "token_usage": 123,
  "temperature": 0.7
}
```

## Características

- **Temperaturas Automáticas**: O backend gera automaticamente temperaturas entre 0.2 e 1.0 para cada interação
- **Armazenamento Seguro**: Interações são armazenadas no Supabase com políticas de segurança adequadas
- **Tratamento de Erros**: Implementação robusta para lidar com falhas na API ou no banco de dados

## Segurança

- Este projeto utiliza Row-Level Security (RLS) do Supabase através de funções RPC para operações seguras
- As chaves de API devem ser protegidas e nunca comprometidas em repositórios públicos

## Contribuições

Contribuições são bem-vindas! Por favor, abra uma issue antes de enviar pull requests.

## Licença

[MIT](LICENSE) 
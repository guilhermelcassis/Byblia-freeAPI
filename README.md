# AI Chat API com Supabase

API para interação com modelos de IA e armazenamento de histórico de conversas usando FastAPI e Supabase.

## Visão Geral

Este projeto implementa uma API RESTful que permite:
- Interagir com modelos de IA (LLM) para gerar respostas de chat
- Armazenar histórico de interações no Supabase
- Controlar a temperatura de forma automática no backend

## Tecnologias

- **Backend**: FastAPI (Python)
- **Banco de Dados**: Supabase (PostgreSQL)
- **Modelo de IA**: LLM via pydantic-ai

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
   - Adicione suas credenciais LLM e Supabase

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

**Resposta (Streaming)**:

O servidor envia eventos usando Server-Sent Events (SSE) com o formato:

```
data: {"type":"chunk","content":"Parte da resposta..."}

data: {"type":"chunk","content":" continuação..."}

data: {"type":"complete","token_usage":123,"temperature":0.7,"interaction_id":42}

data: [DONE]
```

**Exemplo de uso no frontend (com JavaScript)**:
```javascript
// Função para consumir resposta em streaming
async function streamChat(prompt) {
  try {
    const response = await fetch('https://byblia-freeapi.onrender.com', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });

    // Cria um leitor para o stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullMessage = '';
    let metadata = null;

    // Processa o stream
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // Decodifica o chunk
      const chunk = decoder.decode(value);
      
      // Processa cada linha do formato SSE
      const lines = chunk.split('\n\n');
      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue;
        
        const data = line.replace('data: ', '');
        if (data === '[DONE]') continue;
        
        try {
          const parsed = JSON.parse(data);
          
          // Se for um chunk de texto, exibe na tela
          if (parsed.type === 'chunk') {
            fullMessage += parsed.content;
            // Atualiza a UI em tempo real
            document.getElementById('response').innerText = fullMessage;
          }
          
          // Se for a conclusão, armazena os metadados
          if (parsed.type === 'complete') {
            metadata = parsed;
            // Aqui você pode exibir os metadados ou armazená-los para feedback
            console.log('Metadados:', metadata);
          }
        } catch (e) {
          console.error('Erro ao processar chunk:', e);
        }
      }
    }

    return { message: fullMessage, metadata };
  } catch (error) {
    console.error('Erro ao fazer streaming:', error);
    throw error;
  }
}

// Uso
document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = document.getElementById('prompt-input').value;
  
  // Iniciar o streaming
  try {
    await streamChat(prompt);
    // O texto já estará sendo atualizado na UI durante o streaming
  } catch (error) {
    alert('Erro ao processar sua pergunta. Por favor, tente novamente.');
  }
});
```

### Feedback

**Endpoint**: `POST /api/feedback`

**Corpo da Requisição**:
```json
{
  "interaction_id": 42,
  "feedback": true
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Feedback recebido com sucesso"
}
```

## Características

- **Temperaturas Automáticas**: O backend gera automaticamente temperaturas entre 0.2 e 1.0 para cada interação
- **Armazenamento Seguro**: Interações são armazenadas no Supabase com políticas de segurança adequadas
- **Feedback do Usuário**: Os usuários podem avaliar a qualidade das respostas com feedback positivo ou negativo
- **Tratamento de Erros**: Implementação robusta para lidar com falhas na API ou no banco de dados

## Segurança

- Este projeto utiliza Row-Level Security (RLS) do Supabase através de funções RPC para operações seguras
- As chaves de API devem ser protegidas e nunca comprometidas em repositórios públicos

## Contribuições

Contribuições são bem-vindas! Por favor, abra uma issue antes de enviar pull requests.

## Licença

[MIT](LICENSE) 
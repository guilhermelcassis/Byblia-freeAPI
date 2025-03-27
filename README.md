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

**Exemplo de uso no frontend (com React):**

Usando a API de Server-Sent Events (SSE) nativa para melhor desempenho:

```jsx
import React, { useState, useEffect, useRef } from 'react';

function ChatComponent() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [debugLogs, setDebugLogs] = useState([]);  // Array para armazenar logs de debug
  const eventSourceRef = useRef(null);

  // Função de debug para adicionar logs
  const addDebugLog = (message) => {
    console.log(`[FRONTEND_DEBUG] ${message}`);
    setDebugLogs(prev => [...prev, { time: new Date().toISOString(), message }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    
    // Limpar respostas anteriores
    setResponse('');
    setMetadata(null);
    setDebugLogs([]);  // Limpar logs de debug
    setIsLoading(true);
    
    // Fechar conexão anterior se existir
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      addDebugLog("Conexão anterior fechada");
    }
    
    addDebugLog(`Iniciando solicitação para prompt: "${prompt.substring(0, 30)}..."`);
    
    try {
      // Preparar os parâmetros para o fetch
      const params = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      };
      
      // Criar URL com os parâmetros
      const requestInit = {
        method: params.method,
        headers: params.headers,
        body: params.body,
        credentials: 'same-origin',
      };

      addDebugLog("Enviando solicitação ao servidor...");
      // Fazer a solicitação inicial ao servidor
      const response = await fetch('https://sua-api.com/api/chat', requestInit);
      
      if (!response.ok) {
        throw new Error(`Erro HTTP: ${response.status}`);
      }
      
      addDebugLog(`Resposta recebida com status: ${response.status}`);
      addDebugLog("Configurando leitor de stream...");
      
      // Usar o EventSource para processamento em tempo real (SSE)
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullMessage = '';
      let buffer = '';
      let chunkCount = 0;
      
      // Função para processar chunks do stream
      const processStream = async () => {
        addDebugLog("Iniciando processamento do stream");
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            addDebugLog("Stream finalizado pelo servidor");
            break;
          }
          
          // Decodificar o chunk e adicionar ao buffer
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;
          
          addDebugLog(`Recebido dados brutos (${value.length} bytes): "${chunk.substring(0, 50)}..."`);
          
          // Processar cada evento SSE completo
          let eventEnd = buffer.indexOf('\n\n');
          while (eventEnd !== -1) {
            const event = buffer.substring(0, eventEnd);
            buffer = buffer.substring(eventEnd + 2);
            
            // Processar apenas linhas data:
            if (event.startsWith('data: ')) {
              const data = event.replace('data: ', '');
              
              // Verificar se é o evento de final do stream
              if (data === '[DONE]') {
                addDebugLog("Evento [DONE] recebido");
                continue;
              }
              
              try {
                const parsed = JSON.parse(data);
                
                if (parsed.type === 'start') {
                  addDebugLog("Evento de início do stream recebido");
                  continue;
                }
                
                // Se for um chunk de texto, adiciona à mensagem atual
                if (parsed.type === 'chunk') {
                  chunkCount++;
                  fullMessage += parsed.content;
                  addDebugLog(`Chunk #${chunkCount} recebido: "${parsed.content.substring(0, 30)}..." (${parsed.content.length} caracteres)`);
                  
                  // Atualiza o estado para re-renderizar com o novo conteúdo
                  setResponse(fullMessage);
                }
                
                // Se for a conclusão, salva os metadados
                if (parsed.type === 'complete') {
                  setMetadata(parsed);
                  addDebugLog(`Metadados recebidos: Tokens=${parsed.token_usage}, Temp=${parsed.temperature}, ID=${parsed.interaction_id}`);
                }
              } catch (e) {
                addDebugLog(`ERRO ao processar chunk: ${e.message}, Dados: ${data}`);
                console.error('Erro ao processar chunk:', e, data);
              }
            } else if (event.startsWith(': ')) {
              // Comentário do servidor (heartbeat ou informativo)
              const comment = event.replace(': ', '');
              addDebugLog(`Comentário do servidor: ${comment}`);
            }
            
            // Procurar o próximo evento no buffer
            eventEnd = buffer.indexOf('\n\n');
          }
        }
        
        // Finalizar quando o stream terminar
        addDebugLog(`Stream completo - total de ${chunkCount} chunks recebidos`);
        setIsLoading(false);
      };
      
      // Iniciar o processamento do stream
      processStream();
      
    } catch (error) {
      addDebugLog(`ERRO FATAL: ${error.message}`);
      console.error('Erro ao fazer streaming:', error);
      setResponse('Erro ao processar sua pergunta. Por favor, tente novamente.');
      setIsLoading(false);
    }
  };
  
  // Limpar conexões ao desmontar o componente
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        console.log("[FRONTEND_DEBUG] Conexão fechada no cleanup");
      }
    };
  }, []);

  return (
    <div className="chat-container">
      <form onSubmit={handleSubmit} className="chat-form">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Digite sua pergunta..."
          disabled={isLoading}
          className="chat-input"
        />
        <button type="submit" disabled={isLoading} className="chat-button">
          {isLoading ? 'Enviando...' : 'Enviar'}
        </button>
      </form>
      
      <div className="response-container">
        {isLoading && !response && <div className="loading">Processando...</div>}
        
        {response && (
          <div className="response-content">
            <div className="response-text">{response}</div>
            
            {metadata && (
              <div className="response-metadata">
                <small>
                  Tokens: {metadata.token_usage} | 
                  Temperatura: {metadata.temperature.toFixed(2)} |
                  ID: {metadata.interaction_id}
                </small>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Seção de Logs para Debug - Remover em produção */}
      <div className="debug-logs" style={{ marginTop: '20px', padding: '10px', background: '#f0f0f0', maxHeight: '200px', overflow: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
        <h4>Logs de Debug (Remover em produção)</h4>
        {debugLogs.map((log, index) => (
          <div key={index} style={{ borderBottom: '1px solid #ddd', padding: '2px 0' }}>
            <span style={{ color: '#999' }}>{log.time.split('T')[1].split('.')[0]}</span>: {log.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ChatComponent;
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
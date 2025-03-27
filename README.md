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

## Streaming de Respostas Token por Token

A API agora suporta streaming avançado token por token (caracter por caracter), permitindo uma experiência de usuário extremamente fluida, semelhante a assistentes de IA populares como ChatGPT.

### Características do Streaming

- **Alta Granularidade**: Cada token (frequentemente apenas uma única letra ou palavra) é transmitido individualmente
- **Experiência Fluida**: Delays mínimos de 0.01 segundos entre tokens criam uma sensação de digitação em tempo real
- **Feedback Instantâneo**: Os usuários veem a resposta começando imediatamente, sem esperar por chunks grandes
- **Metadados Úteis**: Ao final do streaming, são enviados detalhes como tokens usados e ID da interação

### Consumindo o Streaming no Frontend

Usando os Server-Sent Events (SSE), o frontend pode processar cada token à medida que chega:

```javascript
const streamChat = async (userPrompt) => {
  const controller = new AbortController();
  let fullResponse = '';
  let metadata = null;
  
  try {
    // Elemento onde a resposta será exibida
    const responseElement = document.getElementById('response');
    responseElement.innerHTML = ''; // Limpar resposta anterior
    
    // Exibir indicador de digitação
    const typingIndicator = document.createElement('span');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.textContent = '▋'; // Cursor de digitação
    responseElement.appendChild(typingIndicator);
    
    // Configurar a request
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: userPrompt }),
      signal: controller.signal
    });
    
    if (!response.ok) {
      throw new Error(`Erro na API: ${response.status}`);
    }
    
    // Configurar leitor de stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    // Função que processa os eventos no formato SSE
    const processSSEChunk = (chunk) => {
      // Dividir em linhas
      const lines = chunk.split('\n\n');
      
      for (const line of lines) {
        if (!line || !line.startsWith('data: ')) continue;
        
        // Extrair os dados JSON
        const jsonStr = line.replace('data: ', '');
        
        // Verificar se é o marcador de fim
        if (jsonStr === '[DONE]') {
          console.log('Stream concluído');
          return;
        }
        
        try {
          const data = JSON.parse(jsonStr);
          
          if (data.type === 'chunk') {
            // Adicionar o token à resposta completa
            fullResponse += data.content;
            
            // Atualizar a UI com efeito de digitação
            const textNode = document.createTextNode(data.content);
            responseElement.insertBefore(textNode, typingIndicator);
            
            // Scroll para garantir que o conteúdo mais recente esteja visível
            responseElement.scrollTop = responseElement.scrollHeight;
          } 
          else if (data.type === 'complete') {
            // Armazenar metadados
            metadata = {
              tokenUsage: data.token_usage,
              temperature: data.temperature,
              interactionId: data.interaction_id
            };
            
            // Remover o indicador de digitação
            typingIndicator.remove();
            
            // Mostrar metadados, se desejado
            console.log('Metadados da resposta:', metadata);
          }
        } catch (e) {
          console.error('Erro ao processar chunk:', e);
        }
      }
    };
    
    // Iniciar leitura do stream
    while (true) {
      const { value, done } = await reader.read();
      
      if (done) {
        console.log('Stream finalizado pelo servidor');
        break;
      }
      
      // Decodificar e processar o chunk
      const chunk = decoder.decode(value);
      processSSEChunk(chunk);
    }
    
    // Remover o indicador de digitação se ainda estiver presente
    if (typingIndicator.parentNode) {
      typingIndicator.remove();
    }
    
    // Retornar a resposta completa e metadados
    return { response: fullResponse, metadata };
    
  } catch (error) {
    console.error('Erro ao processar streaming:', error);
    
    // Cancelar a requisição se ainda estiver em andamento
    controller.abort();
    
    throw error;
  }
};
```

### Exemplo de Componente React com Animação de Digitação

Abaixo está um exemplo de componente React que implementa uma experiência de usuário refinada, com animação de cursor piscante e processamento token por token:

```jsx
import React, { useState, useRef, useEffect } from 'react';
import './ChatComponent.css'; // Você precisará criar este arquivo CSS

const ChatComponent = () => {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Scroll automático para a mensagem mais recente
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    // Adicionar mensagem do usuário
    const userMessage = { role: 'user', content: prompt };
    setMessages(prev => [...prev, userMessage]);
    
    // Criar uma mensagem vazia para o assistente que será preenchida gradualmente
    const assistantMessageId = Date.now();
    setMessages(prev => [...prev, { role: 'assistant', content: '', id: assistantMessageId, isStreaming: true }]);
    
    setIsLoading(true);
    setPrompt('');
    
    try {
      const controller = new AbortController();
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
        signal: controller.signal
      });
      
      if (!response.ok) {
        throw new Error(`Erro na API: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      
      // Processar o stream
      while (true) {
        const { value, done } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (!line || !line.startsWith('data: ')) continue;
          
          const jsonStr = line.replace('data: ', '');
          
          if (jsonStr === '[DONE]') {
            break;
          }
          
          try {
            const data = JSON.parse(jsonStr);
            
            if (data.type === 'chunk') {
              // Adicionar o token à resposta e atualizar a mensagem
              fullContent += data.content;
              
              // Atualizar a mensagem do assistante token por token
              setMessages(messages => 
                messages.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: fullContent } 
                    : msg
                )
              );
            } 
            else if (data.type === 'complete') {
              // Marcar o streaming como concluído
              setMessages(messages => 
                messages.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, isStreaming: false, metadata: {
                        tokenUsage: data.token_usage,
                        temperature: data.temperature,
                        interactionId: data.interaction_id
                      }} 
                    : msg
                )
              );
            }
          } catch (e) {
            console.error('Erro ao processar chunk:', e);
          }
        }
      }
    } catch (error) {
      console.error('Erro ao processar chat:', error);
      
      // Atualizar a mensagem com o erro
      setMessages(messages => 
        messages.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: 'Erro ao processar sua solicitação. Por favor, tente novamente.', isStreaming: false, isError: true } 
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div 
            key={index} 
            className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
          >
            <div className="message-content">
              {msg.content}
              {msg.isStreaming && <span className="cursor-blink">▋</span>}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Digite sua pergunta..."
          disabled={isLoading}
          className="chat-input"
        />
        <button 
          type="submit" 
          disabled={isLoading || !prompt.trim()} 
          className="send-button"
        >
          {isLoading ? 'Processando...' : 'Enviar'}
        </button>
      </form>
    </div>
  );
};

export default ChatComponent;
```

CSS para o componente acima:

```css
/* ChatComponent.css */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  max-width: 800px;
  margin: 0 auto;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #f9f9f9;
}

.message {
  margin-bottom: 12px;
  max-width: 80%;
  padding: 10px 16px;
  border-radius: 18px;
  line-height: 1.5;
  animation: fadeIn 0.3s ease;
}

.message.user {
  align-self: flex-end;
  margin-left: auto;
  background-color: #2b7ffd;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant {
  align-self: flex-start;
  background-color: #e9e9e9;
  color: #333;
  border-bottom-left-radius: 4px;
}

.message.error {
  background-color: #ffebee;
  color: #c62828;
}

.cursor-blink {
  display: inline-block;
  vertical-align: middle;
  width: 2px;
  height: 16px;
  background-color: #333;
  margin-left: 2px;
  animation: blink 1s infinite;
}

.input-form {
  display: flex;
  padding: 10px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #d1d1d1;
  border-radius: 24px;
  font-size: 16px;
  outline: none;
}

.chat-input:focus {
  border-color: #2b7ffd;
}

.send-button {
  margin-left: 10px;
  padding: 0 20px;
  background-color: #2b7ffd;
  color: white;
  border: none;
  border-radius: 24px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.send-button:hover:not(:disabled) {
  background-color: #0062e6;
}

.send-button:disabled {
  background-color: #b0b0b0;
  cursor: not-allowed;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</css_to_apply> 
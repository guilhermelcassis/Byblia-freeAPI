from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from app.schemas.interaction import ChatRequest, StreamChunk, StreamComplete
from app.services.ai_agent import generate_streaming_response
import logging
import asyncio

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Endpoint para processar perguntas e gerar respostas usando o agente IA.
    Todas as respostas são enviadas como streaming.
    
    Args:
        request: Contém o prompt do usuário
        
    Returns:
        StreamingResponse: Resposta gerada em formato de streaming
    """
    try:
        # Sempre usar streaming
        return StreamingResponse(
            generate_chat_stream(request.prompt),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}")

async def generate_chat_stream(prompt: str):
    """
    Gera um stream de eventos para enviar ao cliente.
    
    Args:
        prompt: A pergunta do usuário
        
    Yields:
        Chunks de texto no formato SSE (Server-Sent Events)
    """
    try:
        # Iniciar o streaming
        temperature = None  # Será gerada aleatoriamente
        
        async for item in generate_streaming_response(prompt, temperature):
            if isinstance(item, str):
                # É um chunk de texto
                chunk = StreamChunk(type="chunk", content=item)
                yield f"data: {json.dumps(chunk.dict())}\n\n"
                await asyncio.sleep(0.01)  # Pequeno delay para controlar a taxa de envio
            else:
                # É o resultado final com metadados
                # Garantir que interaction_id seja sempre um inteiro válido
                interaction_id = item.get("interaction_id", 0)
                if interaction_id is None:
                    interaction_id = 0
                
                complete = StreamComplete(
                    type="complete",
                    token_usage=item.get("token_usage", 0),
                    temperature=item.get("temperature", 0),
                    interaction_id=interaction_id
                )
                yield f"data: {json.dumps(complete.dict())}\n\n"
        
        # Encerrar o stream
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Erro ao gerar streaming: {str(e)}")
        error_json = json.dumps({"error": str(e)})
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n" 
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import json
from app.schemas.interaction import ChatRequest, StreamChunk, StreamComplete
from app.services.ai_agent import generate_streaming_response
import logging
import asyncio
import time

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest, req: Request):
    """
    Endpoint para processar perguntas e gerar respostas usando o agente IA.
    Todas as respostas são enviadas como streaming.
    
    Args:
        request: Contém o prompt do usuário
        
    Returns:
        StreamingResponse: Resposta gerada em formato de streaming
    """
    try:
        # Configuração agressiva para garantir streaming
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desativa buffering em servidores Nginx
            "Transfer-Encoding": "chunked"
        }
        
        return StreamingResponse(
            content=real_time_stream(request.prompt),
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}")

async def real_time_stream(prompt: str):
    """
    Gera um stream de eventos em tempo real com controle fino de fluxo.
    
    Args:
        prompt: A pergunta do usuário
        
    Yields:
        Chunks de texto no formato SSE (Server-Sent Events)
    """
    try:
        logger.info(f"[STREAM_DEBUG] Iniciando stream para prompt: '{prompt[:50]}...'")
        chunk_count = 0
        
        # Enviar comentários iniciais para forçar o início do stream
        logger.info("[STREAM_DEBUG] Enviando comentário inicial")
        await asyncio.sleep(0.05)
        
        # Enviar evento de heartbeat para manter a conexão aberta
        logger.info("[STREAM_DEBUG] Enviando heartbeat")
        await asyncio.sleep(0.05)
        
        # Enviar evento de início
        logger.info("[STREAM_DEBUG] Enviando evento de início")
        start_event = json.dumps({"type": "start"})
        yield f"data: {start_event}\n\n"
        await asyncio.sleep(0.1)
        
        # Enviar mensagem de inicialização para testar a conexão
        logger.info("[STREAM_DEBUG] Enviando chunk de inicialização")
        init_chunk = StreamChunk(type="chunk", content="")
        yield f"data: {json.dumps(init_chunk.dict())}\n\n"
        await asyncio.sleep(0.2)  # Delay maior para este primeiro chunk
        
        # Iniciar o streaming
        logger.info("[STREAM_DEBUG] Começando a transmissão real do conteúdo")
        temperature = None  # Será gerada aleatoriamente
        
        async for item in generate_streaming_response(prompt, temperature):
            if isinstance(item, str):
                # É um chunk de texto
                chunk = StreamChunk(type="chunk", content=item)
                chunk_json = json.dumps(chunk.dict())
                
                # Log do chunk para debug
                chunk_count += 1
                logger.info(f"[STREAM_DEBUG] Enviando chunk #{chunk_count}: '{item[:30]}...' ({len(item)} caracteres)")
                
                # Forçar cada chunk como um evento SSE separado
                yield f"data: {chunk_json}\n\n"
                # Delay para garantir que o navegador processe cada chunk separadamente
                await asyncio.sleep(0.1)
            else:
                # É o resultado final com metadados
                logger.info(f"[STREAM_DEBUG] Enviando metadados finais: {item}")
                
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
                await asyncio.sleep(0.1)
        
        # Encerrar o stream
        logger.info(f"[STREAM_DEBUG] Stream finalizado após {chunk_count} chunks")
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"[STREAM_DEBUG] Erro ao gerar streaming: {str(e)}")
        error_json = json.dumps({"error": str(e)})
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n" 
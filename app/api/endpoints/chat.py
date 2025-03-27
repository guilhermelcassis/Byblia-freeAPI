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
    Otimizado para streaming de alta velocidade similar a sites comerciais de LLM.
    
    Args:
        request: Contém o prompt do usuário
        
    Returns:
        StreamingResponse: Resposta gerada em formato de streaming
    """
    try:
        # Configuração otimizada para streaming de alta performance
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desativa buffering em servidores Nginx
            "Transfer-Encoding": "chunked"
        }
        
        return StreamingResponse(
            content=optimized_token_stream(request.prompt),
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}")

async def optimized_token_stream(prompt: str):
    """
    Gera um stream de eventos em tempo real usando tokens nativos do modelo.
    Otimizado para velocidade máxima sem delays artificiais.
    
    Args:
        prompt: A pergunta do usuário
        
    Yields:
        Tokens no formato SSE (Server-Sent Events)
    """
    try:
        prompt_preview = prompt[:30] + "..." if len(prompt) > 30 else prompt
        logger.info(f"[CHAT] Iniciando stream para: '{prompt_preview}'")
        char_count = 0
        buffer = ""
        max_buffer_size = 3  # Tamanho máximo de buffer para evitar atrasos perceptíveis
        
        # Apenas um pequeno delay inicial para iniciar o streaming
        await asyncio.sleep(0.01)
        
        logger.info("[CHAT] Transmitindo tokens...")
        temperature = None  # Será gerada aleatoriamente
        
        try:
            # Contador para log ocasional
            last_log_time = time.time()
            
            async for item in generate_streaming_response(prompt, temperature):
                if isinstance(item, str):
                    # Recebeu um token do modelo
                    buffer += item
                    char_count += len(item)
                    
                    # Enviar imediatamente se o buffer atingir o tamanho alvo
                    # ou se o token contiver certas características (espaço, pontuação)
                    if len(buffer) >= max_buffer_size or any(c in buffer for c in ' .,!?;\n'):
                        chunk = StreamChunk(type="chunk", content=buffer)
                        chunk_json = json.dumps(chunk.dict())
                        buffer = ""  # Limpar o buffer
                        
                        # Log ocasional
                        current_time = time.time()
                        if current_time - last_log_time > 3.0:
                            logger.info(f"[CHAT] Transmitidos {char_count} caracteres até agora")
                            last_log_time = current_time
                        
                        # Enviar sem delay
                        yield f"data: {chunk_json}\n\n"
                else:
                    # Enviar qualquer texto restante no buffer
                    if buffer:
                        chunk = StreamChunk(type="chunk", content=buffer)
                        chunk_json = json.dumps(chunk.dict())
                        yield f"data: {chunk_json}\n\n"
                        buffer = ""
                    
                    # É o resultado final com metadados
                    logger.info(f"[CHAT] Enviando metadados finais")
                    
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
        except Exception as stream_error:
            logger.error(f"[CHAT] Erro durante streaming: {str(stream_error)}")
            error_chunk = StreamChunk(type="chunk", content=f"\n\nDesculpe, ocorreu um erro. Por favor, tente novamente.")
            yield f"data: {json.dumps(error_chunk.dict())}\n\n"
        
        # Encerrar o stream
        logger.info(f"[CHAT] Stream finalizado: {char_count} caracteres enviados")
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"[CHAT] Erro crítico: {str(e)}")
        error_json = json.dumps({"error": str(e)})
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n" 
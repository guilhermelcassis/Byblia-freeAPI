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
    Todas as respostas são enviadas como streaming caractere por caractere.
    
    Args:
        request: Contém o prompt do usuário
        
    Returns:
        StreamingResponse: Resposta gerada em formato de streaming
    """
    try:
        # Configuração agressiva para garantir streaming em tempo real
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desativa buffering em servidores Nginx
            "Transfer-Encoding": "chunked"
        }
        
        return StreamingResponse(
            content=character_level_stream(request.prompt),
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}")

async def character_level_stream(prompt: str):
    """
    Gera um stream de eventos em tempo real caractere por caractere.
    Cada letra é transmitida individualmente para uma experiência de digitação.
    
    Args:
        prompt: A pergunta do usuário
        
    Yields:
        Caracteres individuais no formato SSE (Server-Sent Events)
    """
    try:
        prompt_preview = prompt[:30] + "..." if len(prompt) > 30 else prompt
        logger.info(f"[CHAT] Iniciando stream para: '{prompt_preview}'")
        char_count = 0
        
        # Enviar eventos iniciais
        yield ": Iniciando resposta caractere por caractere\n\n"
        await asyncio.sleep(0.05)
        
        # Enviar evento de início
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        await asyncio.sleep(0.05)
        
        # Iniciar o streaming caractere por caractere
        logger.info("[CHAT] Transmitindo caracteres...")
        temperature = None  # Será gerada aleatoriamente
        
        try:
            # Contador para log ocasional
            last_log_time = time.time()
            
            async for item in generate_streaming_response(prompt, temperature):
                if isinstance(item, str):
                    # É um caractere individual
                    char_count += 1
                    
                    # Criar um chunk contendo apenas este caractere
                    chunk = StreamChunk(type="chunk", content=item)
                    chunk_json = json.dumps(chunk.dict())
                    
                    # Log ocasional para não sobrecarregar o console
                    current_time = time.time()
                    if current_time - last_log_time > 3.0:  # Log a cada 3 segundos
                        logger.info(f"[CHAT] Transmitidos {char_count} caracteres até agora")
                        last_log_time = current_time
                    
                    # Enviar cada caractere imediatamente como SSE
                    yield f"data: {chunk_json}\n\n"
                    
                    # Não precisamos de delay adicional aqui, o agente já aplica delay
                else:
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
                    await asyncio.sleep(0.05)
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
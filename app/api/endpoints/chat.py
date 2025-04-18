from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
import json
from app.schemas.interaction import ChatRequest, StreamChunk, StreamComplete
from app.services.ai_agent import generate_streaming_response
from app.api.dependencies import verify_referer, check_rate_limit
import logging
import asyncio
import time
from pydantic import ValidationError

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(
    request: ChatRequest, 
    req: Request,
    _: None = Depends(verify_referer),
    __: None = Depends(check_rate_limit)
):
    """
    Endpoint para processar perguntas e gerar respostas usando o agente IA.
    Otimizado para streaming de alta velocidade similar a sites comerciais de LLM.
    Protegido com rate limiting e verificação de origem.
    
    Args:
        request: Contém o prompt do usuário e opcionalmente o histórico de mensagens
        
    Returns:
        StreamingResponse: Resposta gerada em formato de streaming
    """
    try:
        # Log detalhado da requisição para depuração
        body_content = None
        try:
            # Tentar ler o corpo da requisição para depuração
            body_content = await req.body()
            logger.info(f"[DEBUG] Corpo da requisição recebido: {body_content}")
        except Exception as read_error:
            logger.warning(f"[DEBUG] Não foi possível ler o corpo da requisição: {str(read_error)}")
        
        # Log dos headers para depuração
        logger.info(f"[DEBUG] Headers da requisição: {dict(req.headers)}")
        
        # Verificar se o prompt está vazio ou tem apenas espaços
        if not request.is_valid_for_processing():
            logger.warning(f"[DEBUG] Prompt inválido recebido: '{request.prompt}'")
            raise HTTPException(
                status_code=400,
                detail="O prompt está vazio. Por favor, digite uma pergunta."
            )
            
        # Log do prompt válido
        logger.info(f"[DEBUG] Prompt válido recebido: '{request.prompt[:50]}...' ({len(request.prompt)} caracteres)")
        
        # Log do histórico de mensagens se houver
        if request.message_history:
            logger.info(f"[DEBUG] Histórico de mensagens recebido com {len(request.message_history)} mensagens")
        else:
            logger.info("[DEBUG] Sem histórico de mensagens")
            
        # Configuração otimizada para streaming de alta performance
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desativa buffering em servidores Nginx
            "Transfer-Encoding": "chunked"
        }
        
        return StreamingResponse(
            content=optimized_token_stream(request.prompt, message_history=request.message_history),
            media_type="text/event-stream",
            headers=headers
        )
    except HTTPException as http_ex:
        # Re-lançar exceções HTTP já formadas, mas garantindo melhor formatação do erro
        logger.error(f"[DEBUG] Erro HTTP: {http_ex.status_code} - {http_ex.detail}")
        # Retornar um erro SSE formatado para o cliente
        async def error_stream():
            error_json = json.dumps({"error": str(http_ex.detail)})
            yield f"data: {error_json}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            content=error_stream(),
            media_type="text/event-stream",
            headers=headers,
            status_code=http_ex.status_code
        )
    except ValidationError as ve:
        # Capturar erros de validação específicos do Pydantic
        logger.error(f"[DEBUG] Erro de validação Pydantic: {str(ve)}")
        async def validation_error_stream():
            error_json = json.dumps({"error": f"Erro de validação: {str(ve)}"})
            yield f"data: {error_json}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            content=validation_error_stream(),
            media_type="text/event-stream",
            status_code=422
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        logger.exception("[DEBUG] Stacktrace completa:")
        # Retornar o erro como streaming para que o cliente possa processar
        async def general_error_stream():
            error_json = json.dumps({"error": f"Erro ao processar solicitação: {str(e)}"})
            yield f"data: {error_json}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            content=general_error_stream(),
            media_type="text/event-stream",
            status_code=500
        )

async def optimized_token_stream(prompt: str, message_history=None):
    """
    Gera um stream de eventos em tempo real usando tokens nativos do modelo.
    Otimizado para velocidade máxima sem delays artificiais.
    
    Args:
        prompt: A pergunta do usuário
        message_history: Histórico de mensagens anteriores para contextualização
        
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
        temperature = None
        
        try:
            # Contador para log ocasional
            last_log_time = time.time()
            
            async for item in generate_streaming_response(prompt, temperature, message_history):
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
                    
                    # Incluir o novo histórico de mensagens nos metadados finais
                    complete = StreamComplete(
                        type="complete",
                        token_usage=item.get("token_usage", 0),
                        temperature=item.get("temperature", 0),
                        interaction_id=interaction_id,
                        new_messages=item.get("new_messages")
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
from fastapi import APIRouter, HTTPException
from app.schemas.interaction import ChatRequest, ChatResponse
from app.services.ai_agent import process_chat_request
import logging

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(request: ChatRequest):
    """
    Endpoint para processar perguntas e gerar respostas usando o agente IA.
    
    Args:
        request: Contém apenas o prompt do usuário
        
    Returns:
        ChatResponse: Resposta gerada e metadados
    """
    try:
        result = await process_chat_request(
            prompt=request.prompt
        )
        
        # Verificar se o ID da interação está presente
        interaction_id = result.get("interaction_id")
        if interaction_id is None:
            logger.warning("Interação salva sem ID - usando ID temporário")
            interaction_id = 0  # Valor temporário para satisfazer a validação
        
        return ChatResponse(
            message=result["message"],
            token_usage=result["token_usage"],
            temperature=result["temperature"],
            interaction_id=interaction_id
        )
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}") 
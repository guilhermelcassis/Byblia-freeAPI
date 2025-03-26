from fastapi import APIRouter, HTTPException
from app.schemas.interaction import ChatRequest, ChatResponse
from app.services.ai_agent import process_chat_request

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
        
        return ChatResponse(
            message=result["message"],
            token_usage=result["token_usage"],
            temperature=result["temperature"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação: {str(e)}") 
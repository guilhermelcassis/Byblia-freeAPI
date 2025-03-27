from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.interaction import FeedbackRequest, FeedbackResponse
from app.services.supabase_service import InteractionService
from app.api.dependencies import verify_referer, check_rate_limit

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse, status_code=200)
async def submit_feedback(
    request: FeedbackRequest,
    req: Request,
    _: None = Depends(verify_referer),
    __: None = Depends(check_rate_limit)
):
    """
    Endpoint para receber o feedback do usuário sobre uma interação específica.
    Protegido com rate limiting e verificação de origem.
    
    Args:
        request: Contém o ID da interação e o feedback (True/False)
        
    Returns:
        FeedbackResponse: Confirmação de que o feedback foi recebido
    """
    try:
        # Validar entrada
        if request.interaction_id is None:
            raise HTTPException(status_code=400, detail="ID da interação é obrigatório")
            
        # Atualizar o feedback no Supabase
        result = await InteractionService.update_feedback(
            interaction_id=request.interaction_id,
            feedback=request.feedback
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("message", "Erro ao processar feedback"))
            
        return FeedbackResponse(
            success=True,
            message="Feedback recebido com sucesso"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar feedback: {str(e)}") 
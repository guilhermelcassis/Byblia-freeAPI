from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, Union, Literal
import os

# Obter o tamanho máximo do prompt a partir das variáveis de ambiente
# ou usar um valor padrão razoável (2000 caracteres)
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "2000"))

class InteractionBase(BaseModel):
    user_prompt: str
    model: str
    temperature: float
    message: str
    token_usage: int
    interaction_number: int

class InteractionCreate(InteractionBase):
    pass

class Interaction(InteractionBase):
    id: int
    timestamp: datetime
    user_feedback: Optional[bool] = None

class ChatRequest(BaseModel):
    prompt: str = Field(
        ..., 
        min_length=0,  # Permitir strings vazias para debug
        max_length=MAX_PROMPT_LENGTH, 
        description=f"A pergunta do usuário (máximo {MAX_PROMPT_LENGTH} caracteres)",
    )
    
    # Método para checar se o prompt é válido para processamento
    # Mesmo se estiver vazio, não rejeitaremos imediatamente
    def is_valid_for_processing(self) -> bool:
        """Verifica se o prompt tem conteúdo significativo para processamento."""
        return len(self.prompt.strip()) > 0
        
    class Config:
        # Configuração para exibir exemplos e tratamento de erros mais detalhado
        schema_extra = {
            "example": {
                "prompt": "Qual é o significado de João 3:16?"
            }
        }

class StreamChunk(BaseModel):
    """Modelo para um pedaço de streaming da resposta"""
    type: Literal["chunk"]
    content: str

class StreamComplete(BaseModel):
    """Modelo para a conclusão do streaming com metadados"""
    type: Literal["complete"]
    token_usage: int
    temperature: float
    interaction_id: int

class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: bool

class FeedbackResponse(BaseModel):
    success: bool
    message: str 
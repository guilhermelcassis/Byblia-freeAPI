from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, Union, Literal
import os

# Obter o tamanho máximo do prompt a partir das variáveis de ambiente
# ou usar um valor padrão razoável (2000 caracteres)
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "1000"))

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
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH, 
                        description=f"A pergunta do usuário (máximo {MAX_PROMPT_LENGTH} caracteres)")

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
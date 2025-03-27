from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, Union

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
    prompt: str

class ChatResponse(BaseModel):
    message: str
    token_usage: int
    temperature: float
    interaction_id: int

class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: bool

class FeedbackResponse(BaseModel):
    success: bool
    message: str 
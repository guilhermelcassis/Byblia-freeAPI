from fastapi import FastAPI
from app.api.endpoints import chat
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar a aplicação FastAPI
app = FastAPI(
    title="AI Chat API",
    description="API para interação com modelos de IA e armazenamento de histórico no Supabase",
    version="1.0.0"
)

# Incluir rotas da API
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    """Endpoint para verificar se a API está funcionando."""
    return {"status": "online", "message": "API do Chatbot funcionando!"} 
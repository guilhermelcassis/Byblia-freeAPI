from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.endpoints import chat, feedback
import os
import time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Middleware de segurança customizado
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Verificar tamanho do corpo da requisição para evitar ataques de DOS
        content_length = request.headers.get("content-length")
        max_size = 1024 * 100  # 100KB
        
        if content_length and int(content_length) > max_size:
            return HTTPException(
                status_code=413, 
                detail="Payload muito grande. Tamanho máximo permitido: 100KB"
            )
            
        # Bloquear requisições com User-Agent vazio (muitos bots)
        user_agent = request.headers.get("user-agent")
        if not user_agent:
            return HTTPException(
                status_code=403, 
                detail="Requisições sem User-Agent não são permitidas"
            )
            
        # Registrar tempo de resposta para monitoramento
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Adicionar headers de segurança
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response

# Configurar a aplicação FastAPI
app = FastAPI(
    title="AI Chat API",
    description="API para interação com modelos de IA e armazenamento de histórico no Supabase",
    version="1.0.0"
)

# Adicionar middleware de segurança
app.add_middleware(SecurityMiddleware)

# Configurar CORS para permitir apenas origens autorizadas
# Por padrão, apenas o frontend Byblia é permitido
allowed_origins = ["https://byblia.vercel.app"]

# Em ambiente de desenvolvimento, permitir localhost
if os.getenv("ENVIRONMENT", "production").lower() == "development":
    allowed_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ])

# Configuração CORS mais permissiva para debug temporário
if os.getenv("CORS_DEBUG", "false").lower() == "true":
    allowed_origins = ["*"]  # Permitir todas as origens temporariamente

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight por 24 horas
)

# Incluir rotas da API
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])

@app.get("/")
async def root():
    """Endpoint para verificar se a API está funcionando."""
    return {"status": "online", "message": "API do Chatbot funcionando!"} 
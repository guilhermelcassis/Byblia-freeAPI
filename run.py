import uvicorn
import logging
import os
from logging.config import dictConfig
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging otimizada - menos verbosa
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s | %(name)s | %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
    },
    "loggers": {
        # Logger principal da aplicação - nível INFO
        "": {"handlers": ["console"], "level": "INFO"},
        
        # Desativar logs menos relevantes
        "httpcore": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "hpack": {"level": "ERROR"},
        "openai": {"level": "WARNING"},
        "uvicorn": {"level": "WARNING"},
        "uvicorn.error": {"level": "WARNING"},
        "uvicorn.access": {"level": "WARNING"},
        
        # Manter apenas logs importantes da aplicação
        "app.api.endpoints.chat": {"level": "INFO"},
        "app.services.ai_agent": {"level": "INFO"},
    }
}

# Aplicar configuração de logging
dictConfig(logging_config)
logger = logging.getLogger("stream-server")

if __name__ == "__main__":
    # Obter configuração de porta e host das variáveis de ambiente
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Servidor iniciado em {host}:{port} (streaming letra por letra)")
    
    # Uvicorn com configurações otimizadas para streaming em tempo real
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="warning",  # Reduzir para warning em vez de debug
        reload=True,
        timeout_keep_alive=120,
        http="h11",
        loop="asyncio",
        access_log=False,  # Desativar log de acesso para reduzir ruído
        limit_concurrency=50,
        backlog=100,
    ) 
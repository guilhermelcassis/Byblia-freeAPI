import uvicorn
import os
import logging
from dotenv import load_dotenv

if __name__ == "__main__":
    # Configurar logging para debug mais detalhado
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    load_dotenv()
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Iniciando servidor em {host}:{port} com configuração otimizada para streaming...")
    
    # Configuração otimizada para streaming em tempo real
    uvicorn.run(
        "app.main:app", 
        host=host, 
        port=port, 
        reload=True,
        log_level="debug",  # Aumentar para debug para ver mais informações
        timeout_keep_alive=300,  # Aumentar tempo de conexão ativa
        http="h11",  # Usar o protocolo h11 que tem melhor suporte para streaming
        loop="asyncio",  # Garantir o uso do loop asyncio
        access_log=True,  # Mostrar logs de acesso para ajudar no debug
        limit_concurrency=100,  # Limitar concorrência para melhor desempenho
        backlog=100,  # Tamanho da fila de conexões pendentes
    ) 
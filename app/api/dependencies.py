# Este arquivo pode conter dependências comuns que serão injetadas nos endpoints
# Por exemplo, verificação de autenticação, rate limiting, etc. 

from fastapi import Request, HTTPException, Depends
from typing import List, Optional, Dict
import os
import time
from collections import defaultdict
import threading

# Rate limiting - controle simples em memória
# Para aplicações de maior escala, considere Redis ou outro armazenamento distribuído
class RateLimiter:
    def __init__(self):
        self.ip_requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        # Configuração do rate limit
        self.requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
        self.window_seconds = 60  # Janela de tempo em segundos
        
        # Limpeza periódica do contador
        self._schedule_cleanup()
    
    def _schedule_cleanup(self):
        # Agendar limpeza periódica dos contadores antigos
        threading.Timer(300, self._cleanup_old_data).start()  # A cada 5 minutos
    
    def _cleanup_old_data(self):
        current_time = time.time()
        with self.lock:
            for ip, requests in list(self.ip_requests.items()):
                # Remover timestamps mais velhos que a janela de tempo
                self.ip_requests[ip] = [ts for ts in requests if current_time - ts < self.window_seconds]
                # Remover IPs sem requisições recentes
                if not self.ip_requests[ip]:
                    del self.ip_requests[ip]
        # Agendar próxima limpeza
        self._schedule_cleanup()
    
    def is_rate_limited(self, ip: str) -> bool:
        current_time = time.time()
        
        with self.lock:
            # Filtrar requisições apenas dentro da janela de tempo
            self.ip_requests[ip] = [ts for ts in self.ip_requests[ip] 
                                     if current_time - ts < self.window_seconds]
            
            # Verificar se excedeu o limite
            if len(self.ip_requests[ip]) >= self.requests_per_minute:
                return True
            
            # Adicionar nova requisição
            self.ip_requests[ip].append(current_time)
            return False

# Instância global do rate limiter
rate_limiter = RateLimiter()

def verify_referer(
    request: Request,
    allowed_domains: Optional[List[str]] = None
) -> None:
    """
    Dependency que verifica se a requisição vem de uma origem permitida.
    
    Args:
        request: O objeto Request do FastAPI
        allowed_domains: Uma lista de domínios permitidos. Se None, usa apenas byblia.vercel.app
        
    Raises:
        HTTPException: Se o referer não estiver na lista de domínios permitidos
    """
    # Em ambiente de produção, podemos desativar temporariamente para debug
    # Remova essa linha quando tudo estiver funcionando adequadamente
    production_debug = os.getenv("DISABLE_REFERER_CHECK", "false").lower() == "true"
    if production_debug:
        return None
        
    if allowed_domains is None:
        allowed_domains = ["byblia.vercel.app"]
        
    # Em ambiente de desenvolvimento, permitir localhost e ausência de referer
    is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development"
    if is_dev:
        allowed_domains.extend([
            "localhost:3000",
            "127.0.0.1:3000",
            "localhost:5173",
            "127.0.0.1:5173",
            "localhost:8000", # Porta do FastAPI
            "127.0.0.1:8000",
        ])
        # Em dev, permitir ausência de referer para testes com ferramentas como curl, Postman, etc.
        if request.headers.get("referer") is None:
            return None
        
    # Obter o cabeçalho referer (de onde veio a requisição)
    referer = request.headers.get("referer")
    
    # Se não houver referer em produção, verificar se é uma solicitação OPTIONS (preflight CORS)
    if not referer:
        if request.method == "OPTIONS":
            return None
        
        # Em produção, ser mais rigoroso
        if not is_dev:
            raise HTTPException(
                status_code=403,
                detail="Acesso não autorizado: origem desconhecida"
            )
        return None
    
    # Verificar se o referer contém um dos domínios permitidos
    if not any(domain in referer for domain in allowed_domains):
        raise HTTPException(
            status_code=403,
            detail="Acesso não autorizado: origem não permitida"
        )
        
    return None

def check_rate_limit(request: Request) -> None:
    """
    Dependency que limita o número de requisições por IP.
    
    Args:
        request: O objeto Request do FastAPI
        
    Raises:
        HTTPException: Se o limite de requisições for excedido
    """
    # Obter o IP do cliente (considera o X-Forwarded-For se disponível)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    
    # Verificar se o IP excedeu o limite
    if rate_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Muitas requisições. Por favor, tente novamente mais tarde."
        )
        
    return None 
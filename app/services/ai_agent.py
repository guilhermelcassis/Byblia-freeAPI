from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_core import to_jsonable_python
import os
import random
from dotenv import load_dotenv
from app.services.supabase_service import InteractionService
import asyncio
from typing import AsyncGenerator, Union, Dict, Any, Optional
import time
import logging

# Configuração do logger
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Configurações padrão para o agente
DEFAULT_MODEL = os.getenv('COUNSELOR_MODEL')
MIN_TEMPERATURE = 0.2
MAX_TEMPERATURE = 1.0

def get_api_key():
    """Recupera a chave de API do ambiente."""
    api_key = os.getenv('LLM_API_KEY')
    if not api_key:
        raise ValueError("LLM_API_KEY não encontrada nas variáveis de ambiente")
    return api_key

def setup_agent(model_name=DEFAULT_MODEL):
    """
    Configura e retorna um agente para interação com o modelo.
    
    Args:
        model_name: Nome do modelo LLM a ser usado
        
    Returns:
        Tupla com (agent, model)
    """
    # Obter chave de API
    api_key = get_api_key()
        
    # Configurar o modelo e o agente
    model = OpenAIModel(model_name, provider=DeepSeekProvider(api_key=api_key))
    
    agent = Agent(
        model=model,
        instrument=True,
        model_settings={
            # A temperatura será definida dinamicamente em cada chamada
            'temperature': random.uniform(MIN_TEMPERATURE, MAX_TEMPERATURE),
        },
        system_prompt=os.getenv('SYSTEM_PROMPT'),
    )
    
    return agent, model

def get_random_temperature():
    """Gera uma temperatura aleatória dentro dos limites definidos."""
    return random.uniform(MIN_TEMPERATURE, MAX_TEMPERATURE)

async def generate_response(prompt, temperature=None):
    """
    Gera uma resposta do modelo para a pergunta fornecida usando streaming.
    
    Args:
        prompt: Pergunta do usuário
        temperature: Temperatura usada (se None, uma nova será gerada)
        
    Returns:
        Tupla contendo (mensagem_completa, dados_uso, temperatura_usada)
    """
    # Configurar o agente
    agent, model = setup_agent()
    
    # Se a temperatura não for fornecida, gerar uma nova
    if temperature is None:
        temperature = get_random_temperature()
    
    # Atualizar a temperatura do agente para esta pergunta
    agent.model_settings['temperature'] = temperature
    
    # Variável para armazenar a mensagem completa
    full_message = ""
    
    # Usar o agente para gerar a resposta com streaming
    try:
        # Usar streaming para gerar a resposta
        async with agent.run_stream(prompt) as result:
            async for message in result.stream_text(delta=True):
                full_message += message
                
        # Extrair informações de uso
        usage_data = result.usage()
        usage_dict = to_jsonable_python(usage_data)
        total_tokens = usage_dict.get('total_tokens', 0)
        
        return full_message, total_tokens, temperature
        
    except Exception as e:
        # Log do erro
        print(f"Erro ao gerar resposta: {str(e)}")
        
        # Tente novamente com um fallback sem streaming
        try:
            # Resetar o agente com a mesma temperatura
            agent.model_settings['temperature'] = temperature
            
            # Usar o método não-streaming como fallback
            result = await agent.run(prompt)
            
            # Tente obter a resposta de diferentes maneiras possíveis
            if hasattr(result, 'content'):
                full_message = result.content
            elif hasattr(result, 'message'):
                full_message = result.message
            else:
                full_message = str(result)
                
            # Tentar obter informações de uso
            total_tokens = 0
            try:
                if hasattr(result, 'usage'):
                    usage_dict = to_jsonable_python(result.usage)
                    total_tokens = usage_dict.get('total_tokens', 0)
            except:
                pass
                
            return full_message, total_tokens, temperature
            
        except Exception as e2:
            print(f"Erro definitivo ao gerar resposta: {str(e2)}")
            return f"Erro ao processar sua pergunta. Por favor, tente novamente mais tarde.", 0, temperature

# A função process_chat_request foi removida pois se tornou obsoleta.
# Utilize generate_streaming_response para todas as interações com a API.

async def generate_streaming_response(prompt: str, temperature: Optional[float] = None) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
    """
    Gera a resposta do modelo em modo streaming, enviando cada token à medida que é gerado.
    
    Esta função transmite literalmente cada token individual recebido do modelo imediatamente
    para o cliente, criando uma experiência de streaming muito mais refinada e fluida.
    
    Args:
        prompt: A pergunta do usuário
        temperature: A temperatura a ser utilizada pelo modelo (None gera uma aleatória)
        
    Yields:
        União de:
            - str: Cada token individual do texto gerado 
            - Dict: Metadados finais quando a geração é concluída
    """
    full_message = ""
    token_count = 0
    start_time = time.time()
    agent = None
    new_agent = None
    
    try:
        # Inicializar o agente
        agent, model = setup_agent()
        new_agent, new_model = setup_agent()
        
        # Definir a temperatura
        if temperature is None:
            temperature = get_random_temperature()
        
        agent.model_settings['temperature'] = temperature
        
        # Gerar resposta em modo streaming
        try:
            logger.info(f"[AGENT] Iniciando streaming com temperatura {temperature}")
            
            async with agent.run_stream(prompt) as stream:
                # Utilizar stream_text com delta=True para obter tokens individuais
                async for chunk in stream.stream_text(delta=True):
                    # Cada chunk do modelo pode ser vários caracteres - vamos quebrar por caractere
                    if chunk:
                        # Processar cada caractere individualmente para streaming letra por letra
                        for char in chunk:
                            token_count += 1
                            full_message += char
                            
                            # Enviar cada caractere imediatamente, sem buffering
                            yield char
                            
                            # Delay mínimo para criar uma experiência fluida de digitação
                            await asyncio.sleep(0.02)  # Ajustado para simular digitação natural
            
            logger.info(f"[AGENT] Streaming concluído: {token_count} caracteres em {time.time() - start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"[AGENT] Erro durante streaming: {str(e)}")
            # Tentar fallback com temperatura diferente
            try:
                logger.info("[AGENT] Tentando fallback sem streaming")
                new_agent.model_settings['temperature'] = 0.1
                result = await new_agent.run(prompt)
                
                # Extrair a resposta do resultado
                if hasattr(result, 'content'):
                    full_message = result.content
                elif hasattr(result, 'message'):
                    full_message = result.message
                else:
                    full_message = str(result)
                    
                # Simular streaming mesmo no fallback, caractere por caractere
                for char in full_message:
                    token_count += 1
                    yield char
                    await asyncio.sleep(0.02)
            except Exception as e2:
                logger.error(f"[AGENT] Erro no fallback: {str(e2)}")
                raise e
        
        # Extrair dados de uso
        try:
            token_usage = 0
            
            # Tentar obter tokens da sessão de streaming
            try:
                if 'stream' in locals() and stream is not None:
                    usage_data = stream.usage()
                    if usage_data:
                        usage_dict = to_jsonable_python(usage_data)
                        token_usage = usage_dict.get('total_tokens', 0)
                        logger.info(f"[AGENT] Tokens usados: {token_usage}")
            except Exception as e_usage:
                # Silenciar este erro, apenas registrar que não conseguimos obter
                pass
                
            # Se não conseguiu via stream, usar estimativa baseada no comprimento
            if token_usage == 0:
                # Estimativa aproximada: ~4 caracteres por token para línguas latinas
                token_usage = len(full_message) // 4
                logger.info(f"[AGENT] Usando estimativa de tokens: {token_usage}")
                    
            # Salvar interação no Supabase
            interaction_id = None
            try:
                result = await InteractionService.save_interaction(
                    user_prompt=prompt,
                    model=DEFAULT_MODEL,
                    temperature=temperature,
                    message=full_message,
                    token_usage=token_usage
                )
                interaction_id = result.get("interaction_id")
            except Exception as e:
                logger.error(f"[AGENT] Erro ao salvar interação: {str(e)}")
            
            # Enviar metadados
            metadata = {
                "token_usage": token_usage,
                "temperature": temperature,
                "interaction_id": interaction_id
            }
            
            logger.info(f"[AGENT] Resposta completa: {token_usage} tokens, ID: {interaction_id}")
            
            # Enviar metadados no final
            yield metadata
            
        except Exception as e:
            logger.error(f"[AGENT] Erro nos metadados: {str(e)}")
            yield {"token_usage": 0, "temperature": temperature, "interaction_id": None}
    
    except Exception as e:
        logger.error(f"[AGENT] Erro crítico: {str(e)}")
        yield {"token_usage": 0, "temperature": temperature, "interaction_id": None} 
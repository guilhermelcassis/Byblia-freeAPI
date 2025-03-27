from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_core import to_jsonable_python
import os
import random
from dotenv import load_dotenv
from app.services.supabase_service import InteractionService

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

async def generate_streaming_response(prompt: str, temperature=None):
    """
    Gera uma resposta do modelo em streaming, enviando cada parte para o cliente em tempo real.
    
    Args:
        prompt: Pergunta do usuário
        temperature: Temperatura usada (se None, uma nova será gerada)
        
    Yields:
        Chunks de texto ou dicionário final com metadados
    """
    # Configurar o agente
    agent, model = setup_agent()
    
    # Se a temperatura não for fornecida, gerar uma nova
    if temperature is None:
        temperature = get_random_temperature()
    
    # Atualizar a temperatura do agente para esta pergunta
    agent.model_settings['temperature'] = temperature
    
    # Variáveis para armazenar informações
    full_message = ""
    
    try:
        # Usar streaming para gerar a resposta
        async with agent.run_stream(prompt) as result:
            async for chunk in result.stream_text(delta=True):
                # Adicionar chunk à mensagem completa
                full_message += chunk
                # Enviar chunk diretamente para o cliente
                yield chunk
                
        # Extrair informações de uso
        usage_data = result.usage()
        usage_dict = to_jsonable_python(usage_data)
        total_tokens = usage_dict.get('total_tokens', 0)
        
        # Salvar no Supabase
        try:
            supabase_result = await InteractionService.save_interaction(
                user_prompt=prompt,
                model=DEFAULT_MODEL,
                temperature=temperature,
                message=full_message,
                token_usage=total_tokens
            )
            
            # Obter o ID da interação
            interaction_id = supabase_result.get("interaction_id")
            # Garantir que interaction_id seja sempre um inteiro válido
            if interaction_id is None:
                print("Aviso: Não foi possível obter um ID de interação válido do Supabase")
                interaction_id = 0
        except Exception as supabase_error:
            print(f"Erro ao salvar interação no Supabase: {str(supabase_error)}")
            interaction_id = 0  # Valor padrão em caso de erro
        
        # Enviar metadados finais
        yield {
            "token_usage": total_tokens,
            "temperature": temperature,
            "interaction_id": interaction_id
        }
    except Exception as e:
        # Log do erro
        print(f"Erro ao gerar resposta em streaming: {str(e)}")
        
        # Tentar um fallback sem streaming
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
                
            # Enviar a mensagem completa como um único chunk
            yield full_message
            
            # Tentar obter informações de uso
            total_tokens = 0
            try:
                if hasattr(result, 'usage'):
                    usage_dict = to_jsonable_python(result.usage)
                    total_tokens = usage_dict.get('total_tokens', 0)
            except:
                pass
                
            # Salvar no Supabase
            try:
                supabase_result = await InteractionService.save_interaction(
                    user_prompt=prompt,
                    model=DEFAULT_MODEL,
                    temperature=temperature,
                    message=full_message,
                    token_usage=total_tokens
                )
                
                # Obter o ID da interação
                interaction_id = supabase_result.get("interaction_id")
                # Garantir que interaction_id seja sempre um inteiro válido
                if interaction_id is None:
                    print("Aviso: Não foi possível obter um ID de interação válido do Supabase no fallback")
                    interaction_id = 0
            except Exception as supabase_error:
                print(f"Erro ao salvar interação no Supabase (fallback): {str(supabase_error)}")
                interaction_id = 0  # Valor padrão em caso de erro
            
            # Enviar metadados finais
            yield {
                "token_usage": total_tokens,
                "temperature": temperature,
                "interaction_id": interaction_id
            }
        except Exception as e2:
            # Em caso de erro total, enviar mensagem de erro como chunk
            error_message = f"Erro ao processar sua pergunta. Por favor, tente novamente mais tarde."
            yield error_message
            
            # Enviar metadados finais com valores padrão
            yield {
                "token_usage": 0,
                "temperature": temperature,
                "interaction_id": 0
            } 
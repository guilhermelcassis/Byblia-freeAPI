from typing import Dict, Any
from datetime import datetime
from app.database.supabase import get_supabase

class InteractionService:
    """Service for interacting with the Supabase database for chat interactions"""
    
    TABLE_NAME = "interactions"
    
    @staticmethod
    async def save_interaction(
        user_prompt: str,
        model: str,
        temperature: float,
        message: str,
        token_usage: int
    ) -> Dict[str, Any]:
        """
        Saves a chat interaction to Supabase
        
        Args:
            user_prompt: The user's input
            model: The AI model used
            temperature: The temperature setting used
            message: The AI's response
            token_usage: Number of tokens used
            
        Returns:
            The saved interaction record
        """
        try:
            supabase = get_supabase()
            
            # Get current count to determine interaction number
            response = supabase.table(InteractionService.TABLE_NAME).select("id").execute()
            interaction_number = len(response.data) + 1
            
            # Prepare the data
            interaction_data = {
                "user_prompt": user_prompt,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "temperature": temperature,
                "message": message,
                "token_usage": token_usage,
                "interaction_number": interaction_number
            }
            
            # Insert into Supabase using rpc to bypass RLS policies
            result = supabase.rpc(
                "insert_interaction",
                {
                    "p_user_prompt": user_prompt,
                    "p_model": model,
                    "p_timestamp": datetime.now().isoformat(),
                    "p_temperature": temperature,
                    "p_message": message,
                    "p_token_usage": token_usage,
                    "p_interaction_number": interaction_number
                }
            ).execute()
            
            # Debug do resultado recebido do Supabase
            print(f"Resultado Supabase RPC - Tipo de dados: {type(result.data)}")
            print(f"Conteúdo do result.data: {result.data}")
            
            # Obter o ID da interação retornado pela função RPC
            inserted_id = None
            if result.data is not None:
                # Corrigir o problema de "list index out of range"
                if isinstance(result.data, list) and len(result.data) > 0:
                    inserted_id = result.data[0]  # A função RPC retorna o ID diretamente
                    print(f"ID obtido da lista: {inserted_id}")
                elif isinstance(result.data, (int, float)):
                    # Caso o ID seja retornado diretamente como número
                    inserted_id = int(result.data)
                    print(f"ID convertido de número: {inserted_id}")
                else:
                    print(f"Aviso: Resultado inesperado da função RPC: {result.data}")
            
            # Se não conseguir obter o ID através da função RPC, tenta buscar o registro mais recente
            if inserted_id is None:
                print("Tentando obter ID via consulta ao banco de dados...")
                try:
                    # Get the most recent interaction to get its ID
                    recent = supabase.table(InteractionService.TABLE_NAME) \
                        .select("id") \
                        .order("timestamp", desc=True) \
                        .limit(1) \
                        .execute()
                    
                    print(f"Resultado da consulta recente: {recent.data}")
                        
                    if recent.data and len(recent.data) > 0:
                        inserted_id = recent.data[0].get("id")
                        print(f"Obtido ID da interação via consulta: {inserted_id}")
                except Exception as e:
                    print(f"Aviso: Não foi possível obter o ID da interação: {str(e)}")
            
            return {
                "success": True, 
                "interaction_number": interaction_number,
                "interaction_id": inserted_id
            }
        except Exception as e:
            print(f"Erro ao salvar no Supabase: {str(e)}")
            # Retornar um resultado dummy para não quebrar o fluxo
            return {
                "success": False, 
                "error": str(e),
                "interaction_number": 0,
                "interaction_id": None
            }
    
    @staticmethod
    async def update_feedback(interaction_id: int, feedback: bool) -> Dict[str, Any]:
        """
        Updates an interaction with user feedback
        
        Args:
            interaction_id: The ID of the interaction to update
            feedback: True for positive feedback, False for negative
            
        Returns:
            Result of the operation
        """
        try:
            supabase = get_supabase()
            
            # Call the RPC function to update feedback
            result = supabase.rpc(
                "update_interaction_feedback",
                {
                    "p_interaction_id": interaction_id,
                    "p_user_feedback": feedback
                }
            ).execute()
            
            return {
                "success": True,
                "message": "Feedback atualizado com sucesso"
            }
        except Exception as e:
            print(f"Erro ao atualizar feedback: {str(e)}")
            return {
                "success": False,
                "message": f"Erro ao atualizar feedback: {str(e)}"
            }
            
    @staticmethod
    async def get_interactions(limit: int = 10):
        """
        Retrieves recent interactions from Supabase
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of interaction records
        """
        try:
            supabase = get_supabase()
            
            result = (
                supabase.table(InteractionService.TABLE_NAME)
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            
            return result.data
        except Exception as e:
            print(f"Erro ao recuperar interações: {str(e)}")
            return [] 
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
            
            return {"success": True, "interaction_number": interaction_number}
        except Exception as e:
            print(f"Erro ao salvar no Supabase: {str(e)}")
            # Retornar um resultado dummy para não quebrar o fluxo
            return {
                "success": False, 
                "error": str(e),
                "interaction_number": 0
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
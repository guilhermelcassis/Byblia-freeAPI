from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class SupabaseClient:
    """Singleton class to manage Supabase client instance"""
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Returns a Supabase client instance"""
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "Missing required environment variables: SUPABASE_URL and SUPABASE_KEY must be set"
                )
                
            cls._instance = create_client(supabase_url, supabase_key)
            
        return cls._instance

def get_supabase() -> Client:
    """Dependency for getting the Supabase client"""
    return SupabaseClient.get_client() 
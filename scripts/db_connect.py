import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import Client, create_client

# Configurando exibição de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("🎲 Vox - Data Platform")

load_dotenv()

def get_database() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.critical("Erro ao localizar credenciais do Suapabase.")
        print("Erro ao localizar credenciais do Suapabase.")
        return
    logger.info("Conexão com o supabase estabelecia com sucesso.")
    return create_client(url, key)

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY não localizada nas variáveis de ambiente.")
        return
    logger.info("Conexão com o Gemini estabelecia com sucesso.")
    return genai.Client(api_key=api_key)

def get_gemini_embedding(text: str) -> Optional[List[float]]:
    client = get_gemini_client()
    if not client:
        logger.critical("Não foi possível estabelecer uma conexão com o Gemini.")
        return None
    if not text or not text.strip():
        logger.warning("Texto vazio.")
        return None
    
    try:
        response = client.models.embed_content(
            model = "text-embedding-004",
            contents = text,
            config = types.EmbedContentConfig (
                task_type = "RETRIEVAL_DOCUMENT",
                title = "Vox - Knowledge Base"
            )
        )
        
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Erro na API do Gemini: {e}")
        return None
    
if __name__ == "__main__":
    print("Tetando novo SDK google-genai")
    
    vetor = get_gemini_embedding("Trans e travestis")
    
    if vetor:
        print(f"Dimensão do vetor: {len(vetor)}")
        print(f"Primeiros 5 valores: {vetor[:5]}")
    else:
        print("erro")
    
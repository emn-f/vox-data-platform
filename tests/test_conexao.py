import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'...')))

from scripts.db_connect import get_database, get_gemini_embedding


def test_conexao_supabase():
    try:
        client = get_database()
        response = client.table("sessions").select("*").limit(1).execute()
        assert response is not None, "\n✅ Conexão com o Supabase OK"
    except Exception as e:
        pytest.fail(f"🫠 Supabase off: {e}")
        
def test_geracao_embedding():
    txt_test = "Teste da plataforma de Dados do Vox"
    vetor = get_gemini_embedding(txt_test)
    
    assert vetor is not None, "⚠️ Vetor retornou null"
    assert isinstance(vetor, list), "⚠️ O retorno deveria ser uma lista"
    assert len(vetor) == 768, f"⚠️ Tamanho do vetor deve ser 768! Tamanho recebido: {len(vetor)}"
    print("\n✅ Embedding Gemini OK")
    
def test_etl_ingestao():
    assert os.path.exists(os.path.join("data","raw")), "\nPasta origem de busca de arquivos não existe."
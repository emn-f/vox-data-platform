import json
import os
import sys
from pathlib import Path
import httpx
import toml

caminho_raiz = Path(__file__).resolve().parents[2]
secrets_file = caminho_raiz / ".secrets.toml"
secrets = toml.load(secrets_file) if secrets_file.exists() else {}

url = os.getenv("SUPABASE_URL", secrets.get("supabase", {}).get("url", "https://baolyrgupanfceyuzhkj.supabase.co"))
key = os.getenv("SUPABASE_KEY", secrets.get("supabase", {}).get("key", ""))

if not key:
    print("⚠️ SUPABASE_KEY não configurada. Defina em .secrets.toml ou variável de ambiente.")
    sys.exit(1)

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

try:
    # Selecionar os primeiros 44 registros ordenados por kb_id
    response = httpx.get(
        f"{url}/rest/v1/knowledge_base?select=kb_id,topico,eixo_tematico,descricao,referencias,tags,validated&order=kb_id.asc&limit=44",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        with open("scripts/kb_primeiros_44.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Sucesso! Salvo {len(data)} registros em scripts/kb_primeiros_44.json")
    else:
        print(f"Erro na API do Supabase: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Erro ao baixar KB: {e}")

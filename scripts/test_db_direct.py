import os
import sys
from pathlib import Path
import httpx
import toml

caminho_raiz = Path(__file__).resolve().parent.parent
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

# 1. Testar conexão simples
try:
    response = httpx.get(f"{url}/rest/v1/knowledge_base?select=kb_id&limit=5", headers=headers)
    if response.status_code == 200:
        print("Conexão bem sucedida!")
        print("Alguns IDs existentes na KB:")
        for row in response.json():
            print(f" - {row.get('kb_id')}")
    else:
        print(f"Erro na conexão: Código {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Erro ao conectar: {e}")

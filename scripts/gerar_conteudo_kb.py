import os
import sys
import json
from pathlib import Path
import toml
from google.genai import types

# Adiciona a raiz do projeto ao path
caminho_raiz = Path(__file__).resolve().parent.parent
sys.path.append(str(caminho_raiz))

# Carrega chaves do secrets.toml
secrets_path = caminho_raiz / "./.secrets.toml"
try:
    secrets = toml.load(secrets_path)
    os.environ["GEMINI_API_KEY"] = secrets.get("GEMINI_API_KEY", "")
    os.environ["SUPABASE_URL"] = secrets.get("supabase", {}).get("url", "")
    os.environ["SUPABASE_KEY"] = secrets.get("supabase", {}).get("key", "")
except Exception as e:
    print(f"⚠️ Erro ao carregar secrets.toml: {e}")
    sys.exit(1)

from src.core.genai import configurar_api_gemini
from supabase import create_client
from scripts.gerar_embedding import reindexar

EIXOS_DISPONIVEIS = [ "Direitos e Legislação", "Saúde e Bem-estar", "Sociedade e Ativismo", "Educação e Cultura", "Sobre o Vox" ]

def obter_entrada_usuario():
    print("=" * 60)
    print("🏳️‍🌈  Gerador Dinâmico de Conteúdo para KB (Vox AI)  🏳️‍🌈")
    print("=" * 60)

    # 1. Selecionar Eixo Temático
    print("\n1. Escolha o Eixo Temático:")
    for idx, eixo in enumerate(EIXOS_DISPONIVEIS):
        print(f"  [{idx + 1}] {eixo}")
    
    while True:
        try:
            escolha = int(input("Digite o número correspondente: ")) - 1
            if 0 <= escolha < len(EIXOS_DISPONIVEIS):
                eixo_selecionado = EIXOS_DISPONIVEIS[escolha]
                break
            print("Opção inválida. Tente novamente.")
        except ValueError:
            print("Digite apenas números.")

    # 2. Definir Tópico/Tema
    print("\n2. Digite o Tópico ou Tema específico que você quer alimentar:")
    print("  (Exemplo: 'Retificação de Nome para Não-Binários', 'Uso de PrEP sob demanda', 'Centros de acolhimento no Nordeste')")
    topico_selecionado = input("Tema: ").strip()
    while not topico_selecionado:
        print("O tema não pode ser vazio.")
        topico_selecionado = input("Tema: ").strip()

    # 3. Nível de Especificidade
    print("\n3. Escolha o Nível de Especificidade do conteúdo:")
    print("  [1] Geral/Informativo (Foco em clareza simples)")
    print("  [2] Detalhado/Aprofundado (Foco em orientações práticas)")
    print("  [3] Extremamente Específico (Foco em leis, decretos, portarias do SUS e datas reais)")
    
    especificidades = {
        1: "Geral e informativo, focado em clareza simples para leigos.",
        2: "Detalhado e aprofundado, focado em fornecer passos, orientações práticas e detalhes de implementação.",
        3: "Extremamente específico, técnico e rico em detalhes formais: mencione leis específicas, provimentos, números de decretos, portarias do SUS, nomes de instituições reais ou datas históricas."
    }
    
    while True:
        try:
            nivel = int(input("Escolha o nível (1, 2 ou 3): "))
            if nivel in especificidades:
                especificidade_selecionada = especificidades[nivel]
                break
            print("Escolha 1, 2 ou 3.")
        except ValueError:
            print("Digite apenas 1, 2 ou 3.")

    # 4. Quantidade de registros
    print("\n4. Quantos registros (chunks) você deseja gerar para este tópico?")
    while True:
        try:
            quantidade = int(input("Quantidade (Recomendado 3 a 10): "))
            if quantidade > 0:
                break
            print("A quantidade deve ser maior que 0.")
        except ValueError:
            print("Digite um número inteiro válido.")

    # 5. Destino
    print("\n5. Qual o destino do conteúdo gerado?")
    print("  [1] Salvar em um arquivo .sql local")
    print("  [2] Inserir diretamente no banco de dados (Supabase Dev)")
    print("  [3] Ambos (Salvar arquivo e inserir no banco)")
    
    while True:
        try:
            destino = int(input("Escolha o destino (1, 2 ou 3): "))
            if destino in [1, 2, 3]:
                break
            print("Escolha 1, 2 ou 3.")
        except ValueError:
            print("Digite apenas 1, 2 ou 3.")

    return {
        "eixo": eixo_selecionado,
        "topico": topico_selecionado,
        "especificidade": especificidade_selecionada,
        "quantidade": quantidade,
        "destino": destino
    }

def gerar_conteudo_llm(client, params: dict) -> list:
    print("\n🧠 Conectando ao Gemini e gerando conteúdo...")
    
    prompt = f"""
    Você é um Engenheiro de Conhecimento especialista na causa LGBTQIA+ no Brasil.
    Sua tarefa é gerar {params['quantidade']} fragmentos (chunks) de texto de alta qualidade e relevância para nossa base de conhecimento.
    
    Configurações da Geração:
    - Eixo Temático: "{params['eixo']}"
    - Tópico/Tema Principal: "{params['topico']}"
    - Nível de Especificidade Requerido: {params['especificidade']}

    Diretrizes de Conteúdo:
    1. A linguagem deve ser informativa, neutra e sem opiniões pessoais da IA.
    2. Evite repetir as mesmas informações em chunks diferentes. Cada chunk deve focar em um sub-tópico ou detalhe diferente sobre o tema.
    3. As referências devem ser palpáveis, reais e válidas (leis reais, portarias do SUS reais, etc.). Não invente nenhuma legislação.
    4. Crie tags relevantes para indexação semântica.

    Retorne APENAS um JSON contendo uma lista de objetos no seguinte formato:
    [
        {{
            "topico": "Subtópico específico",
            "descricao": "Texto detalhado do chunk (entre 100 e 500 caracteres, autoexplicativo)",
            "referencias": "Nome da lei, órgão ou fonte real",
            "tags": ["tag1", "tag2", "tag3"]
        }}
    ]
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Erro na geração de conteúdo com o Gemini: {e}")
        return []

def salvar_arquivo_sql(chunks: list, eixo: str, topico_original: str):
    filename = f"seed_gerado_{topico_original.lower().replace(' ', '_')}.sql"
    filepath = caminho_raiz / f"supabase/{filename}"
    
    lines = [
        f"-- Arquivo SQL gerado automaticamente para o tema: {topico_original}",
        "-- Sincroniza a sequência antes dos inserts para evitar colisões de ID",
        "SELECT setval('public.kb_id_seq', (SELECT COALESCE(MAX(NULLIF(regexp_replace(kb_id, '\\D', '', 'g'), '')::integer), 0) FROM public.knowledge_base));\n",
        "INSERT INTO \"public\".\"knowledge_base\" (\"topico\", \"eixo_tematico\", \"descricao\", \"referencias\", \"tags\", \"autor\", \"embedding\") VALUES"
    ]
    
    value_lines = []
    for item in chunks:
        # Escapar aspas simples para SQL
        desc = item['descricao'].replace("'", "''")
        ref = item['referencias'].replace("'", "''")
        top = item['topico'].replace("'", "''")
        
        tags_str = ", ".join(f"'{t}'" for t in item['tags'])
        tags_array = f"ARRAY[{tags_str}]"
        
        value_lines.append(f"('{top}', '{eixo}', '{desc}', '{ref}', {tags_array}, 'Gerador Automático Vox', NULL)")
    
    sql_query = "\n" + ",\n".join(value_lines) + "\n;"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + sql_query)
        
    print(f"💾 Arquivo SQL salvo com sucesso em: {filepath.name}")
    return filepath

def inserir_banco_dados(chunks: list, eixo: str):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ Erro: Credenciais do Supabase não configuradas no ambiente.")
        return False
        
    print("🔌 Conectando ao Supabase...")
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"❌ Erro de conexão com o banco: {e}")
        return False
        
    print(f"🚀 Inserindo {len(chunks)} registros no banco de dados...")
    
    dados_inserir = []
    for item in chunks:
        dados_inserir.append({
            "topico": item["topico"],
            "eixo_tematico": eixo,
            "descricao": item["descricao"],
            "referencias": item["referencias"],
            "tags": item["tags"],
            "autor": "Gerador Automático Vox",
            "embedding": None
        })
        
    try:
        res = supabase.table("knowledge_base_etl").insert(dados_inserir).execute()
        print(f"✅ Sucesso! {len(res.data)} registros inseridos no banco.")
        return True
    except Exception as e:
        print(f"❌ Erro ao executar inserção no banco: {e}")
        return False

def configurar_api_gemini() -> genai.Client:
    """
    Configura e inicializa o cliente da API do Google GenAI utilizando a chave armazenada.

    Returns:
        genai.Client: Cliente configurado do Gemini.
    """
    try:
        gem = Client(api_key=GEMINI_API_KEY)
        print("API Gemini configurada com sucesso.")
    except Exception as e:
        print(f"Erro ao configurar a API do Gemini: {e}")

    return gem

def main():
    client = configurar_api_gemini()
    params = obter_entrada_usuario()
    
    chunks = gerar_conteudo_llm(client, params)
    
    if not chunks:
        print("❌ Nenhum conteúdo foi gerado. Abortando.")
        return
        
    print(f"\n✅ {len(chunks)} chunks gerados com sucesso!")
    
    # Executa as ações com base na escolha de destino
    if params["destino"] in [1, 3]:
        salvar_arquivo_sql(chunks, params["eixo"], params["topico"])
        
    if params["destino"] in [2, 3]:
        sucesso_db = inserir_banco_dados(chunks, params["eixo"])
        
        if sucesso_db:
            # Oferece reindexação automática
            print("\n" + "-"*50)
            print("❓ Como os novos itens foram inseridos com embedding NULL, eles não aparecerão nas buscas RAG imediatamente.")
            print("Deseja rodar o script de indexação agora para gerar e salvar os embeddings?")
            print("  [1] Sim (Reindexar agora)")
            print("  [2] Não (Fazer isso manualmente depois)")
            
            while True:
                try:
                    reindex_choice = int(input("Escolha: "))
                    if reindex_choice == 1:
                        reindexar()
                        break
                    elif reindex_choice == 2:
                        print("Ok! Lembre-se de rodar 'python scripts/gerar_embedding.py' antes de testar no chat.")
                        break
                    print("Opção inválida.")
                except ValueError:
                    print("Digite apenas 1 ou 2.")
                    
    print("\n🏁 Processo finalizado!")

if __name__ == "__main__":
    main()

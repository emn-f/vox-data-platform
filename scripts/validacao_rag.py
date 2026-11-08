import os
import sys
import json
import time
from pathlib import Path
import toml
from google.genai import types
from supabase import create_client

# Adiciona o diretório raiz do projeto ao path
caminho_raiz = str(Path(__file__).resolve().parent.parent)
if caminho_raiz not in sys.path:
    sys.path.append(caminho_raiz)

# Carrega configurações e segredos
secrets_path = os.path.join(caminho_raiz, ".secrets.toml")
if not os.path.exists(secrets_path):
    secrets_path = os.path.join(caminho_raiz, ".streamlit/secrets.toml")

try:
    if os.path.exists(secrets_path):
        secrets = toml.load(secrets_path)
        os.environ["GEMINI_API_KEY"] = secrets.get("GEMINI_API_KEY", "")
        os.environ["SUPABASE_URL"] = secrets.get("supabase", {}).get("url", "")
        os.environ["SUPABASE_KEY"] = secrets.get("supabase", {}).get("key", "")
except Exception as e:
    print(f"⚠️ Erro ao carregar secrets.toml: {e}")
    sys.exit(1)

# Importações internas do Vox AI
from src.config import (
    MODELO_SEMANTICO_NOME,
    TAMANHO_VETOR_SEMANTICO,
    GEMINI_MODEL_NAME,
    SEMANTICA_THRESHOLD,
)
from src.core.genai import configurar_api_gemini
from src.core.db.retrieval import recuperar_contexto_inteligente

# Perguntas pré-definidas para teste de cobertura da base de dados
PERGUNTAS_TESTE = [
    {
        "prompt": "Como posso fazer a retificação de nome e gênero?",
        "eixo_esperado": "Direitos e Legislação",
        "topico_esperado": "Família e Adoção" # Ou retificação/cidadania
    },
    {
        "prompt": "Onde posso encontrar um abrigo seguro ou assistência social?",
        "eixo_esperado": "Sociedade e Ativismo",
        "topico_esperado": "Assistência Social"
    },
    {
        "prompt": "Como posso cuidar da minha saúde mental e lidar com ansiedade?",
        "eixo_esperado": "Saúde e Bem-estar",
        "topico_esperado": "Saúde Mental"
    },
    {
        "prompt": "O que é o projeto Vox AI e qual sua missão?",
        "eixo_esperado": "Sobre o Vox",
        "topico_esperado": "O Projeto"
    },
    {
        "prompt": "Qual é a história do ativismo LGBT no Brasil?",
        "eixo_esperado": "Educação e Cultura",
        "topico_esperado": "Cultura e Representatividade"
    }
]

def executar_com_backoff(funcao, *args, max_tentativas=5, **kwargs):
    """
    Executa uma chamada de API com retry e backoff exponencial caso atinja a quota de requisições.
    """
    atraso = 2.0
    for tentativa in range(max_tentativas):
        try:
            return funcao(*args, **kwargs)
        except Exception as e:
            msg_erro = str(e)
            if "ResourceExhausted" in msg_erro or "429" in msg_erro or "Quota" in msg_erro or "quota" in msg_erro.lower():
                print(f"⚠️ Limite de quota atingido. Aguardando {atraso} segundos antes de tentar novamente (Tentativa {tentativa+1}/{max_tentativas})...")
                time.sleep(atraso)
                atraso *= 2.0
            else:
                raise e
    raise Exception("❌ Falha crítica: Excedeu o número máximo de tentativas na API devido a limites de quota.")

def avaliar_resposta_com_llm(client, prompt: str, contexto: str, resposta: str) -> dict:
    """
    Usa o Gemini como juiz para avaliar a qualidade e a fidelidade da resposta gerada.
    """
    prompt_juiz = f"""
    Você é um avaliador especialista em sistemas RAG (Retrieval-Augmented Generation).
    Sua tarefa é avaliar a resposta de um chatbot com base no prompt do usuário e no contexto recuperado da base de conhecimento.

    PROMPT DO USUÁRIO:
    "{prompt}"

    CONTEXTO RECUPERADO:
    "{contexto}"

    RESPOSTA DO CHATBOT:
    "{resposta}"

    Avalie a resposta sob as seguintes métricas (dando notas de 1 a 5, onde 1 é péssimo e 5 é perfeito):

    1. Grounding / Fidelidade (Evitar Alucinações): A resposta se baseia estritamente no contexto fornecido? (Nota 5 = sem alucinações, tudo afirmado está no contexto. Nota 1 = ignorou o contexto e usou conhecimento externo ou inventou dados).
    2. Relevância da Resposta: A resposta realmente sana a dúvida do usuário? (Nota 5 = respondeu perfeitamente. Nota 1 = resposta fora do tema ou vaga).
    3. Empatia e Tom: O tom é acolhedor, inclusivo, respeitoso e livre de julgamentos, apropriado para a comunidade LGBTQIA+? (Nota 5 = excelente tom. Nota 1 = tom frio, inadequado ou preconceituoso).

    Retorne APENAS um JSON válido no seguinte formato:
    {{
        "grounding_score": int,
        "relevance_score": int,
        "tone_score": int,
        "justificativa_grounding": "string curta",
        "justificativa_relevance": "string curta",
        "feedback_melhoria": "string com dicas de como melhorar o RAG ou a base para esta pergunta"
    }}
    """
    try:
        response = executar_com_backoff(
            client.models.generate_content,
            model=GEMINI_MODEL_NAME,
            contents=prompt_juiz,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {
            "error": f"Falha na avaliação: {e}",
            "grounding_score": 0,
            "relevance_score": 0,
            "tone_score": 0,
            "justificativa_grounding": "Erro",
            "justificativa_relevance": "Erro",
            "feedback_melhoria": "N/A"
        }

def testar_pipeline_rag(prompt_dict: dict, client, supabase) -> dict:
    prompt = prompt_dict["prompt"]
    print(f"\n💬 Testando Prompt: '{prompt}'")
    
    # 1. Geração de Embedding
    try:
        embed_result = executar_com_backoff(
            client.models.embed_content,
            model=MODELO_SEMANTICO_NOME,
            contents=prompt,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=TAMANHO_VETOR_SEMANTICO,
            ),
        )
        vetor_prompt = embed_result.embeddings[0].values
    except Exception as e:
        print(f"❌ Erro ao gerar embedding: {e}")
        return {"prompt": prompt, "status": "erro_embedding"}

    # 2. Busca e Recuperação de Contexto Inteligente
    start_time = time.time()
    contexto, fonte_origem, ids_usados = recuperar_contexto_inteligente(vetor_prompt)
    retrieval_time = time.time() - start_time
    
    # Detalhar os chunks recuperados para auditoria
    chunks_encontrados = []
    if ids_usados:
        try:
            ids_list = [item["kb_id"] for item in ids_usados if item.get("kb_id")]
            if ids_list:
                db_res = supabase.table("knowledge_base").select("kb_id, eixo_tematico, topico, descricao").in_("kb_id", ids_list).execute()
                chunks_encontrados = db_res.data if db_res.data else []
        except Exception as e:
            print(f"⚠️ Erro ao detalhar chunks: {e}")

    print(f"🔍 Estratégia de RAG: {fonte_origem} | Chunks recuperados: {len(chunks_encontrados)}")
    print(f"⏱️ Tempo de recuperação: {retrieval_time:.3f}s")

    # 3. Geração da Resposta com o Modelo
    contexto_str = contexto if contexto else "Nenhum contexto encontrado."
    full_prompt = (
        f"Prompt do Usuário: {prompt}\n\n"
        f"Contexto interno da sua base de conhecimento: {contexto_str}\n\n"
        f"Responda à pergunta do usuário com base no contexto fornecido."
    )
    
    # Instrução de sistema simplificada para o teste
    from data.prompts.system_prompt import INSTRUCOES
    sys_config = types.GenerateContentConfig(
        system_instruction=INSTRUCOES,
    )
    
    try:
        chat = executar_com_backoff(
            client.chats.create,
            model=GEMINI_MODEL_NAME,
            config=sys_config,
        )
        # Pequeno atraso para espaçar chamadas
        time.sleep(2)
        resp_result = executar_com_backoff(
            chat.send_message,
            full_prompt
        )
        resposta_gerada = resp_result.text
    except Exception as e:
        print(f"❌ Erro na geração de resposta: {e}")
        return {"prompt": prompt, "status": "erro_geracao"}

    # 4. Avaliação Automática via LLM-as-a-judge
    print("🤖 Avaliando resposta com o LLM-as-a-judge...")
    time.sleep(2)  # Atraso antes do julgamento para evitar rate limit
    avaliacao = avaliar_resposta_com_llm(client, prompt, contexto_str, resposta_gerada)
    
    # Exibir no terminal
    print(f"🌟 Grounding (Fidelidade): {avaliacao.get('grounding_score')}/5 - {avaliacao.get('justificativa_grounding')}")
    print(f"🎯 Relevância: {avaliacao.get('relevance_score')}/5 - {avaliacao.get('justificativa_relevance')}")
    print(f"💡 Sugestão do Juiz: {avaliacao.get('feedback_melhoria')}")
    print("-" * 60)
    
    return {
        "prompt": prompt,
        "eixo_esperado": prompt_dict.get("eixo_esperado"),
        "topico_esperado": prompt_dict.get("topico_esperado"),
        "fonte_origem": fonte_origem,
        "tempo_retomada_s": retrieval_time,
        "contexto_recuperado": contexto_str,
        "resposta_gerada": resposta_gerada,
        "chunks_detalhes": chunks_encontrados,
        "avaliacao": avaliacao
    }

def main():
    print("=" * 60)
    print("🏳️‍🌈  Pipeline de Validação e Diagnóstico do RAG - Vox AI  🏳️‍🌈")
    print("=" * 60)
    
    client = configurar_api_gemini()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    resultados = []
    
    for item in PERGUNTAS_TESTE:
        res = testar_pipeline_rag(item, client, supabase)
        resultados.append(res)
        time.sleep(5)  # Espaçamento entre testes para evitar limite de requisições por minuto (RPM)

    # Salva o relatório consolidado
    relatorio_dir = os.path.join(caminho_raiz, "data")
    os.makedirs(relatorio_dir, exist_ok=True)
    relatorio_path = os.path.join(relatorio_dir, "relatorio_validacao_rag.json")
    
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
        
    print(f"\n📊 Relatório consolidado gerado com sucesso em: \n[relatorio_validacao_rag.json](file://{relatorio_path})")
    
    # Estatísticas Rápidas
    total_testes = len(resultados)
    media_grounding = sum(r["avaliacao"]["grounding_score"] for r in resultados if "avaliacao" in r) / total_testes
    media_relevance = sum(r["avaliacao"]["relevance_score"] for r in resultados if "avaliacao" in r) / total_testes
    media_tone = sum(r["avaliacao"]["tone_score"] for r in resultados if "avaliacao" in r) / total_testes
    
    print("\n📈 Resumo de Desempenho do RAG:")
    print(f"- Média de Fidelidade (Evitar Alucinações): {media_grounding:.2f}/5")
    print(f"- Média de Relevância das Respostas: {media_relevance:.2f}/5")
    print(f"- Média de Acolhimento / Tom: {media_tone:.2f}/5")
    print("=" * 60)

if __name__ == "__main__":
    main()

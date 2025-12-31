import os
import shutil
import sys
import time

from pypdf import PdfReader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.db_connect import get_database, get_gemini_embedding, logger


def extrair_texto_pdf(path_file: str) -> str:
    try:
        reader = PdfReader(path_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"
        return texto
    except Exception as e:
        logger.error(f"Erro ao ler arquivo {path_file}: {e}")
        return ""


def move_indexados(arquivo: str) -> str:
    # Move arquivos indexados para pasta de processados
    dir_destino = os.path.join("data", "processed")
    origem = os.path.join("data", "raw", arquivo)
    destino = os.path.join(dir_destino, arquivo)

    if not os.path.exists(dir_destino):
        os.makedirs(dir_destino)
        logger.info(f"Diretório criado: {dir_destino}")

    try:
        shutil.move(origem, destino)
        logger.info(f"Arquivo movido para: {destino}")
    except Exception as e:
        logger.error(f"Erro ao mover arquivos: {e}")


def processar_arquivos():
    # Verifica conexão com o Supabase
    try:
        client = get_database()
    except Exception as e:
        logger.critical(f"Erro na conexão com o Supabase: {e}")
        return

    # cria pasta se não existir
    dir = os.path.join("data", "raw")
    if not os.path.exists(dir):
        os.mkdir(dir)
        logger.warning(
            f"Pasta {dir} foi criada. Coloque seus arquivos lá e podemos começar."
        )
        return
    arquivos = [f for f in os.listdir(dir) if f.endswith(".pdf")]

    if not arquivos:
        logger.warning("Nenhum PDF localizado na pasta data/raw")
        return

    for arquivo in arquivos:
        caminho = os.path.join(dir, arquivo)
        texto = extrair_texto_pdf(caminho)

        if not texto:
            continue

        vetor = get_gemini_embedding(texto[:2000])

        if vetor:
            dados = {
                "topico": f"Importação automatizada: {arquivo}",
                "descricao": texto[:500],
                "embedding": vetor,
                "autor": "Script ETL Python",
            }
            try:
                client.table("knowledge_base_etl").insert(dados).execute()
                logger.info(f"✅ Arquivo indexado no banco com sucesso! {arquivo}")
                move_indexados(arquivo)

            except Exception as e:
                logger.error(f"Erro no processamento do arquivo {arquivo}: {e}")

        # pausa para não estourar o limite da API
        time.sleep(2)


if __name__ == "__main__":
    processar_arquivos()

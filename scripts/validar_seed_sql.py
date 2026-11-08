import os
import re
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
caminho_raiz = Path(__file__).resolve().parent.parent
sys.path.append(str(caminho_raiz))

SQL_FILE_PATH = caminho_raiz / "supabase/seed_200_kb_items.sql"

EIXOS_VALIDOS = {
    "Direitos e Legislação",
    "Saúde e Bem-estar",
    "Sociedade e Ativismo",
    "Educação e Cultura",
    "Sobre o Vox"
}

def validar_seed():
    if not SQL_FILE_PATH.exists():
        print(f"❌ Erro: Arquivo {SQL_FILE_PATH} não encontrado.")
        return

    print(f"📖 Lendo e validando estaticamente: {SQL_FILE_PATH.name}...")
    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex para capturar os blocos de inserção de valores
    # Captura tudo dentro dos parênteses da tupla de inserção
    # Exemplo: ('Topico', 'Eixo', 'Descricao', 'Ref', ARRAY['tag1', 'tag2'], 'Autor', NULL)
    tuple_pattern = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*(ARRAY\[[^\]]+\])\s*,\s*'([^']+)'\s*,\s*(NULL)\s*\)")
    
    matches = tuple_pattern.findall(content)
    
    total_linhas_arquivo = len(content.splitlines())
    print(f"📊 Linhas analisadas no arquivo SQL: {total_linhas_arquivo}")
    print(f"🎯 Total de registros identificados por padrão sintático: {len(matches)}")
    
    erros = []
    eixos_counts = {}
    topicos_counts = {}
    
    for idx, match in enumerate(matches):
        num_registro = idx + 1
        topico, eixo, descricao, referencias, tags_raw, autor, embedding = match
        
        # 1. Validar Eixo Temático
        if eixo not in EIXOS_VALIDOS:
            erros.append(f"Registro {num_registro}: Eixo temático inválido '{eixo}' (Tópico: {topico})")
        else:
            eixos_counts[eixo] = eixos_counts.get(eixo, 0) + 1
            
        # 2. Validar Descrição
        if not descricao.strip():
            erros.append(f"Registro {num_registro}: Descrição vazia (Tópico: {topico})")
        elif len(descricao) < 30:
            erros.append(f"Registro {num_registro}: Descrição muito curta ({len(descricao)} caracteres) para o RAG")
            
        # 3. Validar Embedding NULL
        if embedding != "NULL":
            erros.append(f"Registro {num_registro}: O campo embedding deve ser explicitamente NULL (Encontrado: {embedding})")
            
        # Contagem de tópicos
        topicos_counts[topico] = topicos_counts.get(topico, 0) + 1

    # Validação estrutural de parênteses na query
    # Procura por potenciais erros de vírgula ou sintaxe
    if "INSERT INTO" in content:
        insert_statements = content.split(";")
        for i, statement in enumerate(insert_statements):
            statement = statement.strip()
            if not statement or statement.startswith("--"):
                continue
            # Verifica parênteses abertos e fechados
            open_p = statement.count("(")
            close_p = statement.count(")")
            if open_p != close_p:
                erros.append(f"Query {i+1}: Desbalanceamento de parênteses. Abertos: {open_p}, Fechados: {close_p}")

    # Apresentação do Relatório
    print("=" * 60)
    print("📋 RESULTADO DA VALIDAÇÃO ESTATÍSTICA")
    print("=" * 60)
    
    if erros:
        print(f"❌ Encontrados {len(erros)} inconsistências:")
        for err in erros[:10]:
            print(f"  - {err}")
        if len(erros) > 10:
            print(f"  ... e mais {len(erros) - 10} erros.")
    else:
        print("✅ Nenhuma inconsistência de estrutura ou dados encontrada no arquivo SQL!")
        
    print("\n📈 Estatísticas de Densidade por Eixo:")
    for eixo, count in sorted(eixos_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {eixo}: {count} itens")
        
    print("\n📈 Principais Tópicos Alimentados (Top 10):")
    for topico, count in sorted(topicos_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {topico}: {count} itens")
    print("=" * 60)

if __name__ == "__main__":
    validar_seed()

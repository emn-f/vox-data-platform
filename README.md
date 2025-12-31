# 🎲 Vox Data Platform

O **Vox Data Platform** é o módulo responsável pela ingestão, processamento e indexação de dados para a base de conhecimento do Vox AI. Ele atua como um pipeline ETL (Extract, Transform, Load) automatizado, convertendo documentos brutos em vetores semânticos prontos para serem utilizados pelo sistema de RAG (Retrieval-Augmented Generation).

## 🚀 Funcionalidades

- **Extração de Texto**: Leitura automatizada de arquivos PDF armazenados localmente.
- **Geração de Embeddings**: Utiliza o modelo `text-embedding-004` do Google Gemini para criar representações vetoriais do conteúdo.
- **Armazenamento Vetorial**: Integração direta com o Supabase para armazenar os textos processados e seus respectivos vetores na tabela `knowledge_base_etl`.
- **Organização Automática**: Move arquivos processados com sucesso da pasta de entrada (`raw`) para a pasta de concluídos (`processed`), mantendo o diretório limpo.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Google GenAI SDK**: Para geração de embeddings.
- **Supabase Client**: Para conexão e operações no banco de dados.
- **PyPDF**: Para extração de texto de PDFs.
- **Python-Dotenv**: Para gerenciamento de variáveis de ambiente.

## ⚙️ Configuração

1. **Clone o repositório** (caso ainda não tenha feito).

2. **Crie um ambiente virtual** (recomendado):
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as Variáveis de Ambiente**:
   Crie um arquivo `.env` na raiz do projeto seguindo o exemplo abaixo:

   ```env
   SUPABASE_URL=sua_url_supabase
   SUPABASE_KEY=sua_chave_supabase
   GEMINI_API_KEY=sua_chave_api_google_gemini
   ```

5. **Configuração do Banco de Dados (Supabase)**:
   
   Você precisará criar uma tabela chamada `knowledge_base_etl` no seu projeto Supabase. Certifique-se de habilitar a extensão `vector` antes. execute o seguinte comando SQL no **SQL Editor** do Supabase:

   ```sql
   -- Habilita a extensão pgvector para trabalhar com embeddings
   create extension if not exists vector;

   -- Cria a tabela para armazenar os dados e vetores
   create table knowledge_base_etl (
     id bigint primary key generated always as identity,
     created_at timestamp with time zone default now(),
     topico text,
     descricao text,
     embedding vector(768), -- 768 dimensões para o modelo text-embedding-004
     autor text
   );
   ```

## 📦 Como Usar

1. **Adicione os arquivos**:
   Coloque os arquivos PDF que deseja processar na pasta:
   ```
   data/raw/
   ```
   *(Se a pasta não existir, o script a criará automaticamente na primeira execução)*

2. **Execute o pipeline de ingestão**:
   ```bash
   python scripts/etl_ingestao.py
   ```

3. **Verifique o resultado**:
   - Os arquivos processados com sucesso serão movidos para `data/processed/`.
   - Os dados e vetores estarão disponíveis na tabela `knowledge_base_etl` do seu projeto Supabase.
   - Logs detalhados serão exibidos no terminal informando o status de cada arquivo.

## 📂 Estrutura do Projeto

```
vox-data-platform/
├── data/
│   ├── raw/          # Local para colocar novos PDFs
│   └── processed/    # Arquivos já processados (movidos automaticamente)
├── scripts/
│   ├── db_connect.py   # Gerencia conexões com Supabase e Gemini
│   └── etl_ingestao.py # Script principal do pipeline ETL
├── tests/            # Testes automatizados (pytest)
├── .env              # Variáveis de ambiente (não versionado)
├── requirements.txt  # Dependências do projeto
└── README.md         # Documentação
```

## 🧪 Testes

Para executar os testes automatizados:

```bash
pytest
```

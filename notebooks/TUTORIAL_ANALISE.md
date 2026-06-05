# 📊 Guia de Análise de Dados: Chat & RAG

Este tutorial serve como um guia passo a passo para construir um Jupyter Notebook dentro do `vox-data-platform` para analisar as interações de chat e o comportamento do mecanismo de RAG (Retrieval-Augmented Generation) do Vox AI.

O objetivo é extrair inteligência sobre as buscas na base de conhecimento utilizando os logs do sistema.

---

## 🔍 1. Entendendo a Origem dos Dados (`chat_atual.sql`)

A análise tem como ponto de partida a query presente no arquivo `vox-ai/supabase/.queries/chat_atual.sql`:

```sql
SELECT
    cl.chat_id,
    cl.prompt,
    cl.response,
    kb.descricao,
    kb.eixo_tematico,
    kb.topico,
    kb.tags,
    s.session_id,
    cl.created_at
FROM
    chat_logs cl
    inner join public.sessions s on cl.session_id = s.session_id
    inner join chat_logs_kb clk on cl.chat_id = clk.chat_id
    inner join knowledge_base kb on clk.kb_id = kb.kb_id
WHERE
    (SELECT id FROM public.sessions ORDER BY id DESC limit 1) = s.id
ORDER BY cl.created_at DESC
```

### O que essa query faz?
1. **Filtra a última sessão ativa**: A cláusula `WHERE` busca a sessão (`sessions`) com o maior ID (a mais recente).
2. **Une perguntas e respostas**: Traz os logs de conversa (`chat_logs`).
3. **Identifica a origem do RAG**: Através da tabela relacional (`chat_logs_kb`), ela descobre qual fragmento da base de conhecimento (`knowledge_base`) foi fornecido como contexto para a IA gerar aquela resposta.

---

## 🛠️ 2. Configurando o Ambiente com `uv`

Antes de abrir o notebook, certifique-se de que todas as dependências estão declaradas no seu `pyproject.toml` ou instaladas no seu ambiente virtual.

```bash
# Adiciona as dependências necessárias para análise de dados
uv add pandas sqlalchemy psycopg2-binary ipykernel matplotlib seaborn jupyterlab
```

Para rodar o ambiente do Jupyter sob o contexto do ambiente virtual do `uv`, execute na raiz de `vox-data-platform`:
```bash
uv run jupyter lab
```

Crie um novo notebook na pasta `notebooks/` chamado `02_analise_conversas.ipynb`.

---

## 📓 3. Estrutura de Células do Notebook

### Célula 1: Configuração do Path e Dependências
Como o notebook está dentro da pasta `notebooks/`, precisamos ensinar o Python a enxergar os scripts que estão na pasta de nível superior.

**Instruções de implementação:**
* Importe `sys` e `os`.
* Adicione o caminho do diretório pai (`".."`) ao `sys.path` usando `sys.path.append(os.path.abspath(".."))`.
* Importe `load_dotenv` da biblioteca `python-dotenv` e a execute passando o caminho do arquivo `.env` (ex: `load_dotenv("../.env")`).
* Importe as funções de conexão que você já possui, como `get_database` de `scripts.db_connect`.

---

### Célula 2: Extraindo os Dados (Escolha a sua Abordagem)

Você tem duas formas principais de carregar a query SQL para um DataFrame do Pandas:

#### Abordagem A: Criando uma View no Supabase (Via API REST)
Esta abordagem é ideal se você quiser continuar usando apenas o SDK do Supabase que já configurou.
1. Vá no painel web do seu Supabase, abra o **SQL Editor** e crie uma View com a query original:
   ```sql
   CREATE OR REPLACE VIEW view_chat_atual AS
   SELECT
       cl.chat_id,
       cl.prompt,
       cl.response,
       kb.descricao,
       kb.eixo_tematico,
       kb.topico,
       kb.tags,
       s.session_id,
       cl.created_at
   FROM
       chat_logs cl
       inner join public.sessions s on cl.session_id = s.session_id
       inner join chat_logs_kb clk on cl.chat_id = clk.chat_id
       inner join knowledge_base kb on clk.kb_id = kb.kb_id
   WHERE
       (SELECT id FROM public.sessions ORDER BY id DESC limit 1) = s.id
   ORDER BY cl.created_at DESC;
   ```
2. No seu notebook, chame o cliente do Supabase para ler a View e carregue os dados em um DataFrame:
   ```python
   # Exemplo conceitual:
   # 1. Obtenha o cliente usando get_database()
   # 2. Faça o select na "view_chat_atual"
   # 3. Converta o resultado (response.data) em um pd.DataFrame
   ```

#### Abordagem B: Conexão Direta Postgres (Via SQLAlchemy)
Esta abordagem é mais comum em análise de dados clássica pois permite rodar qualquer query SQL bruta direto no Python.
1. No seu arquivo `.env`, adicione a string de conexão direta do PostgreSQL fornecida pelo Supabase (ex: `DATABASE_URL=postgresql://postgres.xxx:senha@xxx.supabase.co:5432/postgres`).
2. No notebook, utilize `create_engine` do SQLAlchemy para criar a conexão.
3. Carregue o DataFrame usando:
   ```python
   # Exemplo conceitual:
   # engine = create_engine(os.getenv("DATABASE_URL"))
   # query = "SUA QUERY SQL AQUI"
   # df = pd.read_sql_query(query, engine)
   ```

---

## 📈 4. Ideias de Análises para Implementar

Depois de ter o DataFrame (ex: `df`) carregado com sucesso, explore os seguintes tópicos criando células separadas para cada análise:

### A. Estatística Descritiva e Inspeção
* Veja o cabeçalho dos dados: `df.head()`
* Confira os tipos de colunas e dados nulos: `df.info()`
* Analise estatísticas de colunas textuais ou numéricas: `df.describe()`

### B. Distribuição de Tópicos e Eixos Temáticos
* **Pergunta:** Quais assuntos da base de conhecimento são mais solicitados/recuperados durante as conversas?
* **Implementação:** Use `.value_counts()` na coluna `eixo_tematico` ou `topico`. Plote um gráfico de barras usando o Seaborn:
  ```python
  # Exemplo: sns.countplot(data=df, y='eixo_tematico', order=df['eixo_tematico'].value_counts().index)
  ```

### C. Análise de Comprimento de Texto (Engajamento e Respostas)
* **Pergunta:** As perguntas mais longas exigem contextos maiores? Qual o tamanho médio das respostas geradas?
* **Implementação:** Crie novas colunas com o comprimento dos caracteres de `prompt` e `response` usando `.str.len()`. Em seguida, gere um histograma ou um boxplot para visualizar a distribuição dos tamanhos.

### D. Frequência de Tags da Base de Conhecimento
* **Pergunta:** Quais tags específicas da base estão sendo mais ativadas?
* **Implementação:** Se a coluna `tags` contiver listas ou strings delimitadas por vírgula, use `.str.split(',')` e depois o método `.explode()` do Pandas para separar cada tag em uma linha própria. Isso facilitará rodar um `.value_counts()` sobre a lista total de tags ativadas.

---

## 🚀 Próximos Passos
1. Abra o Jupyter Lab com `uv run jupyter lab`.
2. Crie o notebook `02_analise_conversas.ipynb`.
3. Escreva a primeira célula de configuração de caminho e execute.
4. Escolha se prefere criar a View (Abordagem A) ou usar conexão direta (Abordagem B) e implemente a carga dos dados.

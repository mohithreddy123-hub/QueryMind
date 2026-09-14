<div align="center">

# 🧠 QueryMind
### Conversational Natural Language Interface for Relational Databases

*Query your enterprise MySQL data conversationally using semantic RAG retrieval, Gemini LLMs, and military-grade read-only sandboxing.*

<br/>

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini_3.5_Flash_Lite-4E86F8?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB_1.5.9-FF6F61?style=for-the-badge)](https://www.trychroma.com/)
[![MySQL 8.0](https://img.shields.io/badge/Database-MySQL_8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit_Dark_Canvas-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

<br/>

</div>

---

## ⚡ Why QueryMind is Different

Traditional Text-to-SQL apps send your whole database schema into one prompt and hope the model doesn't hallucinate or leak write operations. **QueryMind treats database querying like an audited information retrieval pipeline:**

| Naive Text-to-SQL | 🧠 QueryMind Architecture |
|---|---|
| Dumps all tables into one huge prompt | **Retrieves only semantically relevant tables** using 3072-dim ChromaDB embeddings |
| Gives the LLM direct database access | **Two-tier security**: Application regex blocklist + MySQL read-only role sandbox |
| Returns raw tabular dumps | **Synthesizes conversational business answers** with currency & metrics formatting |
| Cluttered multi-tab dashboards | **Minimalist ChatGPT / Claude-inspired chat stream** with inspectable query details |

---

## 🔬 How It Works (The 5-Stage RAG Loop)

```
                     ┌────────────────────────────────────────────────────────┐
                     │          User Prompt: "Top 5 selling products"         │
                     └───────────────────────────┬────────────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
│   1. VECTOR RETRIEVAL  │         │   2. SQL SYNTHESIS     │         │   3. APP GUARDRAIL     │
│  ChromaDB Cosine Match │ ──────> │   Google Gemini 3.5    │ ──────> │  Syntax & Keyword Wall │
│  Embed: gemini-emb-001 │         │   Generates ANSI SQL   │         │  Blocks INSERT/DROP/etc│
└────────────────────────┘         └────────────────────────┘         └──────────┬─────────────┘
                                                                                 │
                                                                                 ▼
┌────────────────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
│  5. EXECUTIVE ANSWER   │         │   4. SANDBOX EXECUTION │         │  DATABASE PERMISSION   │
│  Conversational Insight│ <────── │  Read-Only Connector   │ <────── │  `textsql_reader` User │
│  + Data Inspector      │         │  Capped at MAX_ROWS    │         │  Enforces SELECT Only  │
└────────────────────────┘         └────────────────────────┘         └────────────────────────┘
```

<details>
<summary><b>🔍 Click to view step-by-step pipeline details</b></summary>

1. **Schema Retrieval (ChromaDB)**: The user's question is embedded into a 3072-dimensional vector. ChromaDB evaluates cosine similarity against pre-embedded table metadata, selecting only the top-$K$ most relevant tables.
2. **Context-Aware SQL Generation (Gemini 3.5)**: A strict system prompt provides only the retrieved schemas, business domain rules, and requires raw SQL output without hallucinated tables.
3. **Application Guardrail (Validator)**: Regex inspectors verify the statement begins strictly with `SELECT`, preventing destructive statements (`DROP`, `DELETE`, `ALTER`, `GRANT`, `UNION` exfiltration, and stacked queries).
4. **Isolated Execution (Executor)**: Executes through a dedicated MySQL account (`textsql_reader`) with hard database-level SELECT-only grants.
5. **Natural Language Synthesis (Responder)**: Formats returned tabular rows into clear business summaries with proper localization (e.g. ₹ INR currency formatting).
</details>

---

## 🗄️ Database Architecture

The embedded dataset models a production Indian e-commerce ecosystem (`text_to_sql_db`) populated with 23,300 cross-referenced records:

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│    users     │          │    orders    │          │   payments   │
│ (2,000 rows) │ ──1:N──> │ (8,000 rows) │ ──1:1──> │ (8,000 rows) │
└──────────────┘          └──────┬───────┘          └──────────────┘
                                 │
                                N:1
                                 │
                                 ▼
┌──────────────┐          ┌──────────────┐
│   reviews    │          │   products   │
│ (5,000 rows) │ ──N:1──> │  (300 rows)  │
└──────────────┘          └──────────────┘
```

---

## 🛡️ Defense-in-Depth Security

QueryMind implements security across two independent, non-bypassable layers:

```
[ Incoming Query ]
       │
       ▼
 [ Layer 1: Application Validator ]
       ├── Only SELECT queries permitted
       ├── Blocklist: DROP, ALTER, TRUNCATE, DELETE, INSERT, REPLACE, GRANT, EXEC, CALL
       ├── Pattern checks: Stacked queries (;), SQL comment injection (-- or /* */), UNION SELECT
       │
       ▼ (if passed)
 [ Layer 2: MySQL Kernel Permissions ]
       └── User `textsql_reader` has ONLY: GRANT SELECT ON text_to_sql_db.*
           Even zero-day prompt injection cannot modify data at the storage layer.
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.11+**
- **MySQL 8.0+** running locally
- **Google Gemini API Key** ([Get your free key here](https://aistudio.google.com/app/apikey))

### 2. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/mohithreddy123-hub/QueryMind.git
cd QueryMind

# Install dependencies
pip install -r requirements.txt

# Create your local environment file
cp .env.example .env     # On Windows: copy .env.example .env
```

### 3. Configure `.env`
Add your Gemini API Key and MySQL credentials:

```ini
GEMINI_API_KEY=your_gemini_api_key_here

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=textsql_reader
MYSQL_PASSWORD=reader_secure_password
MYSQL_DATABASE=text_to_sql_db

MYSQL_ADMIN_HOST=localhost
MYSQL_ADMIN_PORT=3306
MYSQL_ADMIN_USER=root
MYSQL_ADMIN_PASSWORD=your_root_password
```

### 4. Initialize Database & Vectors

```bash
# 1. Generate tables and 23,300 seed records
python setup/fake_data.py

# 2. Create the read-only MySQL application user
python setup/create_readonly_user.py

# 3. Vectorize schema documents into ChromaDB
python setup/setup_chromadb.py
```

### 5. Launch QueryMind

```bash
streamlit run main.py
```
> The application will open automatically at `http://localhost:8501`.

---

## 💬 Sample Prompts to Try

| Question | Tables Inferred | Query Strategy |
|---|---|---|
| *"Which product sold the most this month?"* | `orders`, `products` | Temporal filter with `SUM(quantity)` and `GROUP BY` |
| *"What is our total revenue from paid orders?"* | `payments` | Aggregation `SUM(amount)` where `status = 'paid'` |
| *"Which cities have the highest customer concentration?"* | `users` | Frequency distribution `COUNT(*)` grouped by `city` |
| *"Show the top 5 products critically low on stock."* | `products` | Boundary condition `stock < 10` sorted ascending |
| *"Which product has the worst average customer rating?"* | `reviews`, `products` | Multi-table join with `AVG(rating)` |

---

## 📂 Repository Topology

```
QueryMind/
├── app/                        # Core Application Engine
│   ├── retriever.py            # ChromaDB vector embedding & cosine search
│   ├── sql_generator.py        # Gemini structured prompt & SQL extractor
│   ├── sql_validator.py        # Application-level AST & keyword firewall
│   ├── sql_executor.py         # MySQL connection & display truncation cap
│   └── responder.py            # Natural language answer synthesis
│
├── config/
│   └── settings.py             # Global constants & model specifications
│
├── setup/                      # Database Initialization
│   ├── fake_data.py            # Faker database generator (23.3k rows)
│   ├── create_readonly_user.py # Grants SELECT privileges to reader user
│   └── setup_chromadb.py       # ChromaDB persistent collection builder
│
├── tests/                      # Verification Suite
│   └── test_pipeline.py        # Unit & end-to-end integration tests
│
├── main.py                     # ChatGPT / Claude style Streamlit interface
├── requirements.txt            # Locked project dependencies
└── README.md                   # System specification
```

---

## 🧪 Testing & Verification

Run the test suite across both isolated unit tests and live pipeline checks:

```bash
# Run unit tests (offline, no database needed)
pytest tests/ -v -m unit

# Run live integration tests (requires MySQL & Gemini key)
pytest tests/ -v -m integration
```

---

<div align="center">
<sub>Built with precision for enterprise conversational database intelligence.</sub>
</div>

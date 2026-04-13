# 🏠 EstatePro — Smart Real Estate Advisory Assistant

A production-ready, AI-powered real estate advisory platform with strict Role-Based Access Control (RBAC) and Retrieval-Augmented Generation (RAG).

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (ChatGPT-like UI) |
| Backend | FastAPI |
| Relational DB | PostgreSQL (`172.25.81.56`) |
| Vector DB | ChromaDB |
| LLM Orchestration | LangChain + OpenAI |
| Auth | JWT + bcrypt |

---

## 👥 Roles & Access

| Role | Access |
|---|---|
| **Admin** | Full access — all documents, both actual & quoted prices |
| **Agent** | Own property listings only — both prices visible |
| **Buyer** | Public listings only — quoted price only |

- Only **buyers** can self-register via the public API.
- **Admin** (1 max) and **Agents** (3 max) are seeded automatically on startup.
- PostgreSQL trigger enforces role limits at the DB level.

---

## ⚙️ Project Structure

```
real-estate-assistant/
├── backend/
│   ├── main.py              # FastAPI entrypoint + lifespan events
│   ├── core/
│   │   ├── config.py        # Settings from .env
│   │   └── security.py      # JWT + bcrypt
│   ├── auth/
│   │   ├── routes.py        # /auth/register, /auth/login, /auth/logout
│   │   ├── schemas.py       # Pydantic models
│   │   └── dependencies.py  # RBAC FastAPI dependencies
│   ├── database/
│   │   ├── session.py       # SQLAlchemy engine + SessionLocal
│   │   ├── models.py        # ORM table definitions
│   │   └── init_db.py       # Table creation, trigger install, seeding
│   ├── chat/
│   │   ├── routes.py        # /chat, /chat/sessions, /chat/sessions/{id}/messages
│   │   └── schemas.py       # Chat Pydantic models
│   └── rag/
│       ├── document_generator.py  # Synthetic property/market/legal docs
│       ├── ingestion.py           # ChromaDB ingestion with role metadata
│       ├── retriever.py           # Role-aware vector retrieval
│       └── tools.py               # 5 LangChain tools
├── frontend/
│   ├── app.py               # Streamlit entry + global CSS
│   ├── auth_page.py         # Login + Buyer registration
│   ├── chat_page.py         # ChatGPT-like interface
│   └── api_client.py        # HTTP wrappers for backend calls
├── docs/                    # Auto-generated on first run
│   ├── admin/
│   ├── agent/
│   └── buyer/
├── .env                     # Environment configuration
├── requirements.txt
├── docker-compose.yml
├── start_backend.sh
└── start_frontend.sh
```

---

## 🚀 Setup & Running Locally

### 1. Prerequisites
- Python 3.11+
- ChromaDB running locally on port `8000`
- Access to PostgreSQL at `172.25.81.56`

### 2. Install Dependencies
```bash
cd real-estate-assistant
pip install -r requirements.txt
```

### 3. Configure Environment
Edit `.env` and set your `OPENAI_API_KEY`:
```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://admin:admin123@172.25.81.56/estatepro
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### 4. Start ChromaDB (local)
```bash
pip install chromadb
chroma run --host localhost --port 8000 --path ./chroma_store
```

### 5. Start Backend (Terminal 1)
```bash
chmod +x start_backend.sh
./start_backend.sh
# OR directly:
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

On startup the backend will automatically:
- Create all PostgreSQL tables
- Install the role-limit trigger
- Seed Admin + 3 Agent accounts
- Generate synthetic documents
- Ingest documents into ChromaDB with role metadata

### 6. Start Frontend (Terminal 2)
```bash
chmod +x start_frontend.sh
./start_frontend.sh
# OR directly:
streamlit run frontend/app.py --server.port 8501
```

Open **http://localhost:8501**

---

## 🔑 Default Credentials (Seeded on First Run)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@realestate.com` | `Admin@123` |
| Agent 1 | `agent1@realestate.com` | `Agent@123` |
| Agent 2 | `agent2@realestate.com` | `Agent@123` |
| Agent 3 | `agent3@realestate.com` | `Agent@123` |

> Buyers must self-register via the **Register** tab.

---

## 🛠️ Available Tools

| Tool | Purpose | Access |
|---|---|---|
| 🏠 Property Retrieval | Fetch listings | All roles |
| 📄 Summarization | Summarize legal/property docs | Admin, Agent |
| 📊 Market Analysis | Market trends & insights | All roles |
| ⚖️ Comparison | Compare multiple properties | All roles |
| 💡 Investment Recommendation | ROI & investment picks | All roles |

---

## 🔒 RBAC Summary

- **API level**: FastAPI `Depends` + JWT validation
- **Vector DB level**: ChromaDB metadata filtering by `role_access` and `agent_id`
- **DB level**: PostgreSQL trigger prevents extra admin/agent creation
- **Price visibility**: Buyer responses strip actual prices at application layer

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Buyer self-registration |
| POST | `/auth/login` | None | Login all roles |
| POST | `/auth/logout` | None | Client-side logout |
| POST | `/auth/admin/create-agent` | Admin only | Create new agent |
| POST | `/chat/` | Required | Chat with tool |
| POST | `/chat/sessions` | Required | Create new session |
| GET | `/chat/sessions/{user_id}` | Required | List user sessions |
| GET | `/chat/sessions/{session_id}/messages` | Required | Get chat history |
| GET | `/health` | None | Health check |

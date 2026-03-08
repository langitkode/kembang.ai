# Kembang AI Backend 🌸

Professional multi-tenant AI chatbot SaaS optimized for UMKM, featuring a **100% Free RAG Pipeline**.

## 🚀 Key Features

- **Local Embeddings**: Uses `SentenceTransformer` (MiniLM-L6) for zero-cost vectorization.
- **Groq Integration**: Lightning-fast LLM responses using Llama 3.1 via LiteLLM.
- **Omnichannel Webhooks**: Unified support for WhatsApp, Telegram, and Custom integrations.
- **Multi-Tenancy**: Isolated knowledge bases and conversation histories per tenant.
- **FastAPI Core**: High-performance asynchronous API with automatic Swagger documentation.

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + pgvector (hosted on Neon)
- **Engine**: SQLAlchemy (Async) + Alembic
- **RAG**: LiteLLM, Sentence-Transformers, PyMuPDF
- **Package Manager**: `uv`

## 📦 Getting Started

### Prerequisites

- Python 3.10+
- `uv` installed (`pip install uv`)
- PostgreSQL with `pgvector` extension

### Installation

1. Clone the repository and navigate to the backend:

   ```bash
   cd backend
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Setup environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your GROQ_API_KEY and DATABASE_URL
   ```

4. Run migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Start the server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## 🔌 API Documentation

Once the server is running, visit:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## 🤖 Omnichannel Setup

Webhooks can be configured at:
`/api/v1/omnichannel/webhook/{tenant_id}/{platform}`

Supported platforms: `whatsapp`, `telegram`, `generic`.

# Kembang AI — Phase 1 Backend Scaffolding

Build the complete backend scaffolding for an agency-first, multi-tenant AI chatbot SaaS platform. This is a greenfield project — no existing code. The goal is to produce a fully runnable FastAPI backend with all modules stubbed out and the core infrastructure (DB, auth, RAG pipeline) implemented end-to-end.

## User Review Required

> [!IMPORTANT]
> **ORM choice**: The context docs list "SQLAlchemy / SQLModel". This plan uses **SQLAlchemy 2.0 async** (`AsyncSession`, `Mapped`, `mapped_column`) for maximum control and mature async support. Let me know if you prefer SQLModel instead.

> [!IMPORTANT]
> **Vector DB**: The plan uses **pgvector** (PostgreSQL extension) to keep infrastructure simple. Qdrant can be swapped later. Does this work for v1?

> [!WARNING]
> **Secrets**: The `.env.example` will contain placeholder values. You will need to provide real API keys (OpenAI, etc.) before the LLM service can make live calls.

---

## Proposed Changes

### Project Setup

#### [NEW] [pyproject.toml](file:///d:/Projects/kembang.ai/backend/pyproject.toml)
Python project metadata and dependencies:
- `fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`, `passlib[bcrypt]`, `pydantic-settings`
- `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pgvector`
- `redis`, `httpx`, `openai`, `tiktoken`
- `rank_bm25`, `sentence-transformers` (for reranker)

#### [NEW] [requirements.txt](file:///d:/Projects/kembang.ai/backend/requirements.txt)
Flat pip requirements for simpler deployment.

#### [NEW] [.env.example](file:///d:/Projects/kembang.ai/backend/.env.example)
All required env vars with safe defaults: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `JWT_SECRET`, etc.

#### [NEW] [Dockerfile](file:///d:/Projects/kembang.ai/backend/Dockerfile)
Multi-stage Python 3.11 image with uvicorn entrypoint.

#### [NEW] [docker-compose.yml](file:///d:/Projects/kembang.ai/backend/docker-compose.yml)
Services: `app` (FastAPI), `db` (PostgreSQL 16 + pgvector), `redis` (Redis 7).

---

### Alembic Migrations

#### [NEW] [alembic.ini](file:///d:/Projects/kembang.ai/backend/alembic.ini)
#### [NEW] [alembic/env.py](file:///d:/Projects/kembang.ai/backend/alembic/env.py)
Configured for async PostgreSQL with the project's `Base.metadata`.

---

### Core Layer (`app/core/`)

#### [NEW] [config.py](file:///d:/Projects/kembang.ai/backend/app/core/config.py)
`pydantic-settings` based `Settings` class reading from env vars. Fields: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES`, `EMBEDDING_MODEL`, `DEFAULT_LLM_MODEL`, `FALLBACK_LLM_MODEL`.

#### [NEW] [security.py](file:///d:/Projects/kembang.ai/backend/app/core/security.py)
- `create_access_token(data)` — JWT creation
- `verify_token(token)` — JWT decode + validation
- `hash_password()` / `verify_password()` — bcrypt via passlib

#### [NEW] [dependencies.py](file:///d:/Projects/kembang.ai/backend/app/core/dependencies.py)
FastAPI dependency functions:
- `get_db()` → yields `AsyncSession`
- `get_current_user(token, db)` → validates JWT, returns User
- `get_tenant(request, user)` → extracts and validates `X-Tenant-ID` header

---

### Database (`app/db/` + `app/models/`)

#### [NEW] [session.py](file:///d:/Projects/kembang.ai/backend/app/db/session.py)
- `create_async_engine` with `postgresql+asyncpg://`
- `async_sessionmaker` factory
- `Base` declarative base class

#### [NEW] [tenant.py](file:///d:/Projects/kembang.ai/backend/app/models/tenant.py)
`Tenant` model: `id`, `name`, `plan`, `created_at`, `updated_at`

#### [NEW] [user.py](file:///d:/Projects/kembang.ai/backend/app/models/user.py)
`User` model: `id`, `tenant_id` (FK), `email`, `password_hash`, `role`, `created_at`, `updated_at`

#### [NEW] [conversation.py](file:///d:/Projects/kembang.ai/backend/app/models/conversation.py)
`Conversation` model: `id`, `tenant_id` (FK), `user_identifier`, `summary`, `created_at`, `updated_at`

#### [NEW] [message.py](file:///d:/Projects/kembang.ai/backend/app/models/message.py)
`Message` model: `id`, `conversation_id` (FK), `role`, `content`, `tokens_used`, `created_at`

#### [NEW] [document.py](file:///d:/Projects/kembang.ai/backend/app/models/document.py)
`KnowledgeBase`: `id`, `tenant_id`, `name`, `created_at`, `updated_at`
`Document`: `id`, `kb_id` (FK), `file_name`, `source_type`, `created_at`
`Chunk`: `id`, `document_id` (FK), `content`, `embedding` (pgvector), `metadata_` (JSON), `created_at`

#### [NEW] [usage_log.py](file:///d:/Projects/kembang.ai/backend/app/models/usage_log.py)
`UsageLog`: `id`, `tenant_id`, `model`, `input_tokens`, `output_tokens`, `cost_estimate`, `timestamp`

---

### Service Layer (`app/services/`)

Each service class is initialized with `AsyncSession` and follows single-responsibility.

#### [NEW] [conversation_service.py](file:///d:/Projects/kembang.ai/backend/app/services/conversation_service.py)
Methods: `create_conversation()`, `get_conversation()`, `add_message()`, `get_recent_messages(limit=6)`, `summarize_history()`

#### [NEW] [rag_service.py](file:///d:/Projects/kembang.ai/backend/app/services/rag_service.py)
Orchestrator. Methods: `retrieve_context()`, `build_prompt()`, `generate_response()`

#### [NEW] [embedding_service.py](file:///d:/Projects/kembang.ai/backend/app/services/embedding_service.py)
Methods: `embed_query()`, `embed_document()` — calls OpenAI `text-embedding-3-small`

#### [NEW] [retrieval_service.py](file:///d:/Projects/kembang.ai/backend/app/services/retrieval_service.py)
Methods: `vector_search()`, `keyword_search()`, `hybrid_search()` — queries pgvector + BM25

#### [NEW] [llm_service.py](file:///d:/Projects/kembang.ai/backend/app/services/llm_service.py)
Methods: `generate()`, `stream_generate()`, `route_model()` — centralized LLM access via OpenAI client

#### [NEW] [usage_service.py](file:///d:/Projects/kembang.ai/backend/app/services/usage_service.py)
Methods: `log_usage()`, `estimate_cost()`, `tenant_usage_summary()`

---

### RAG Pipeline (`app/rag/`)

#### [NEW] [chunking.py](file:///d:/Projects/kembang.ai/backend/app/rag/chunking.py)
`chunk_text(text, chunk_size=400, overlap=80)` — recursive text splitter

#### [NEW] [hybrid_retrieval.py](file:///d:/Projects/kembang.ai/backend/app/rag/hybrid_retrieval.py)
`hybrid_search(query_embedding, query_text, tenant_id)` — merges vector + BM25 results with reciprocal rank fusion

#### [NEW] [reranker.py](file:///d:/Projects/kembang.ai/backend/app/rag/reranker.py)
`rerank(query, chunks, top_k=4)` — cross-encoder reranking (initially using a lightweight model or LLM-based scoring)

#### [NEW] [context_builder.py](file:///d:/Projects/kembang.ai/backend/app/rag/context_builder.py)
`build_context(chunks, max_tokens=1500)` — assembles chunks into a context string under the token limit

---

### API Routes (`app/api/`)

All routes follow the thin-route pattern: validate → call service → return response.

#### [NEW] [routes_auth.py](file:///d:/Projects/kembang.ai/backend/app/api/routes_auth.py)
- `POST /api/v1/auth/login` — returns JWT
- `POST /api/v1/auth/register` — creates user (admin-only for v1)

#### [NEW] [routes_chat.py](file:///d:/Projects/kembang.ai/backend/app/api/routes_chat.py)
- `POST /api/v1/chat/message` — main chat endpoint
- `GET /api/v1/chat/history/{conversation_id}` — retrieve messages

#### [NEW] [routes_kb.py](file:///d:/Projects/kembang.ai/backend/app/api/routes_kb.py)
- `POST /api/v1/kb/upload` — upload document (multipart)
- `GET /api/v1/kb/documents` — list documents

#### [NEW] [routes_admin.py](file:///d:/Projects/kembang.ai/backend/app/api/routes_admin.py)
- `GET /api/v1/admin/usage` — tenant usage summary

---

### Tools & Monitoring

#### [NEW] [tool_router.py](file:///d:/Projects/kembang.ai/backend/app/tools/tool_router.py)
Registry + router for tool execution. Stubbed tools: `product_lookup`, `order_status`.

#### [NEW] [product_lookup.py](file:///d:/Projects/kembang.ai/backend/app/tools/product_lookup.py)
Stub tool returning mock product data.

#### [NEW] [order_status.py](file:///d:/Projects/kembang.ai/backend/app/tools/order_status.py)
Stub tool returning mock order status.

#### [NEW] [usage_logger.py](file:///d:/Projects/kembang.ai/backend/app/monitoring/usage_logger.py)
Async helper that logs every LLM call's metadata to `usage_logs` table.

#### [NEW] [metrics.py](file:///d:/Projects/kembang.ai/backend/app/monitoring/metrics.py)
In-memory request counter + latency tracker (OpenTelemetry-ready stub).

---

### Workers

#### [NEW] [document_ingest_worker.py](file:///d:/Projects/kembang.ai/backend/workers/document_ingest_worker.py)
Background job: extract text → chunk → embed → store in vector DB.

---

### Entry Point

#### [NEW] [main.py](file:///d:/Projects/kembang.ai/backend/app/main.py)
- FastAPI app with `lifespan` context manager (startup/shutdown for DB engine)
- Include all routers with `/api/v1` prefix
- Tenant middleware for `X-Tenant-ID` validation
- CORS middleware
- Health check endpoint: `GET /health`

---

## Verification Plan

### Automated Tests

Since this is a greenfield project, no existing tests. Verification focuses on startup + smoke testing:

1. **Docker Compose up**:
   ```
   cd d:\Projects\kembang.ai\backend
   docker-compose up -d db redis
   ```
   Verify PostgreSQL and Redis containers are healthy.

2. **Install dependencies**:
   ```
   cd d:\Projects\kembang.ai\backend
   pip install -r requirements.txt
   ```

3. **Run Alembic migration**:
   ```
   cd d:\Projects\kembang.ai\backend
   alembic revision --autogenerate -m "initial"
   alembic upgrade head
   ```

4. **Start server**:
   ```
   cd d:\Projects\kembang.ai\backend
   uvicorn app.main:app --reload
   ```
   Verify it starts without import errors.

5. **Health check**:
   ```
   curl http://localhost:8000/health
   ```
   Expect `{"status": "ok"}`.

6. **OpenAPI docs**: Open `http://localhost:8000/docs` in browser — verify all endpoints are listed.

### Manual Verification
- Review the generated code structure matches [folder-structure.md](file:///d:/Projects/kembang.ai/_context/folder-structure.md)
- Confirm all coding rules from [coding-rules.md](file:///d:/Projects/kembang.ai/coding-rules.md) are followed (thin routes, service-layer business logic, tenant_id on all queries, etc.)
- Verify all files import correctly and no circular dependencies exist

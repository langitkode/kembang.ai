# Coding Rules

These rules must be strictly followed when generating backend code.

Goal:

- maintain clean architecture
- avoid business logic in routes
- keep services modular
- ensure multi-tenant safety
- maintain production-ready structure

Language:
Python 3.11+

Framework:
FastAPI

1. General Principles
   Rules:

prefer simple implementations
avoid over-engineering
routes must stay thin
services contain business logic
database logic inside repository or service
strict tenant isolation
avoid global state

2. File Organization Rules

Routes:
app/api/
Services
app/services/
Models
app/models/
Core utilities
app/core/
RAG logic
app/rag/
Tools
app/tools/
Monitoring
app/monitoring/

Never mix responsibilities between folders.

3. FastAPI Route Rules
   Routes must only:
   validate request
   call service
   return response
   Routes must NOT:
   call LLM directly
   implement RAG logic
   query vector database
   contain business logic

Example:

Correct:
route → service → response
Incorrect:
route → vector search → LLM → response

4. Service Layer Rules
   Each service must have a single responsibility.
   Example services:
   ConversationService
   RAGService
   EmbeddingService
   RetrievalService
   LLMService
   UsageService
   Service methods must be small and composable.

Example:
retrieve_context()
build_prompt()
generate_response()
Services should never depend on FastAPI request objects.

5. Multi-Tenant Safety Rules
   Every query must include tenant_id.
   Never allow cross-tenant data access.
   Example:
   Correct:
   SELECT \* FROM conversations
   WHERE tenant_id = :tenant_id
   Incorrect:
   SELECT \* FROM conversations
   Tenant context must be validated in middleware.

6. Database Rules
   Use ORM models.
   Avoid raw SQL unless necessary.
   All tables must include:

id
created_at
updated_at

Tenant-aware tables must include:
tenant_id

7. RAG Rules
   RAG pipeline must follow:
   query
   ↓
   embedding
   ↓
   retrieval
   ↓
   rerank
   ↓
   context build
   ↓
   LLM generation

Never send full documents to LLM.
Always use chunk retrieval.
Max chunks:
4–6

8. LLM Usage Rules
   LLM access must be centralized.
   Only allowed via:
   LLMService
   Never call OpenAI / Anthropic APIs directly from routes or other modules.

Model routing allowed:
simple → small model
complex → large model

9. Logging Rules
   All requests must log:
   tenant_id
   conversation_id
   model_used
   token_usage
   latency

Logs stored in:
usage_logs

10. Error Handling
    Never expose internal errors to user.
    Return standardized response.
    Example:
    {
    "error": "internal_server_error"
    }
    Log full error internally.

11. Async Rules
    Use async for:
    database
    HTTP requests
    LLM calls
    Avoid blocking code inside FastAPI routes.

12. Dependency Injection
    Shared dependencies must live in:
    app/core/dependencies.py
    Examples:
    get_db()
    get_tenant()
    get_current_user() 13. RAG Context Limits
    Maximum context tokens:
    1500 tokens
    Max conversation history:
    last 6 messages
    Older history must be summarized.

13. Tool System Rules
    Tools must follow structure:
    tool input
    tool execution
    tool output

LLM must not execute tools directly.
Tools executed by:
tool_router

15. Monitoring Rules
    Every LLM call must log:
    model
    input_tokens
    output_tokens
    estimated_cost
    tenant_id
    timestamp 16. Code Quality Rules

Avoid:
large functions (>80 lines)
deep nested logic
duplicate logic

Prefer:
small reusable functions
clear naming
modular services

17. Naming Conventions
    Classes: PascalCase
    Functions: snake_case
    Files: snake_case

18. Testing Rules
    Critical services must have tests:
    conversation_service
    rag_service
    retrieval_service
    Tests stored in:
    tests/

19. Performance Rules
    Avoid repeated embedding calls.
    Cache embeddings when possible.
    Use batch operations for:
    document ingestion
    vector insert

20. Security Rules
    Never log:
    API keys
    passwords
    tokens
    Use environment variables for secrets.
    OPENAI_API_KEY
    DATABASE_URL
    REDIS_URL

Final Rule
Always prioritize:
clarity
simplicity
maintainability

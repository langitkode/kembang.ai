# Backend Architecture Audit

Purpose
This document instructs the coding agent to audit the backend implementation
and verify that the system correctly implements:

1. response handling
2. RAG pipeline
3. stateful conversation
4. tenant safety
5. observability

The audit should report:
PASS
FAIL
WARNING

1. Response Handler Audit
   Goal:
   Ensure all responses are generated through the correct pipeline.
   Expected flow:
   route
   ↓
   conversation_service
   ↓
   rag_service
   ↓
   llm_service
   ↓
   response formatter
   Checks

Verify that:
routes do NOT call LLM APIs directly
routes do NOT perform retrieval
response formatting is centralized

Audit tasks:
Search for direct OpenAI / Anthropic calls in routes.
If found → FAIL
Search for vector queries inside routes.
If found → FAIL
Check that chat response goes through LLMService.

Expected structure:
routes_chat.py
→ conversation_service
→ rag_service
→ llm_service

2. RAG Pipeline Audit
   Goal:
   Verify correct Retrieval Augmented Generation implementation.
   Expected pipeline:
   query
   ↓
   embedding
   ↓
   hybrid retrieval
   ↓
   rerank
   ↓
   context builder
   ↓
   LLM generation
   Checks

Verify existence of
embedding_service
retrieval_service
reranker
context_builder
rag_service

Audit tasks:
Ensure vector retrieval uses embeddings.
Ensure retrieved chunks are limited (4–6).
Ensure full documents are NOT sent to LLM.
Ensure prompt contains context section.

Expected prompt pattern:
Context:
{retrieved_chunks}
Question:
{user_query}
Failure conditions:
LLM receives full documents
LLM called without retrieval
No context provided

3. Hybrid Retrieval Audit
   Goal:
   Verify both semantic and keyword retrieval.
   Expected strategy:
   vector search

- keyword search

Audit tasks:
Verify code contains:
vector_search()
keyword_search()
hybrid_search()
Check merging logic:
combined_results = merge(vector_results, keyword_results)
Ensure reranking step exists.

4. Context Builder Audit
   Goal:
   Ensure LLM context size is controlled.
   Expected limits:
   max_chunks = 4–6
   max_context_tokens ≈ 1500
   Audit tasks:

Check context builder truncates large inputs.
Check context builder merges chunks in deterministic order.

Warning conditions:
context > 2000 tokens 5. Stateful Conversation Audit
Goal:
Ensure conversation memory is persistent.

Expected tables:
conversations
messages
Audit tasks:
Verify conversation flow:
user message
↓
load conversation history
↓
RAG
↓
LLM response
↓
store assistant message

Check:
ConversationService.add_message()
ConversationService.get_recent_messages()

Verify conversation history is used in prompts.
Failure conditions:
chat responses ignore conversation history
messages not persisted

6. Conversation Compression Audit
   Goal:
   Prevent token explosion.
   Expected strategy:
   last_k_messages = 6
   older_messages → summarized
   Audit tasks:
   Check existence of:
   summarize_history()
   conversation_summary field
   Warning:
   if full history always sent to LLM

7. Multi-Tenant Isolation Audit
   Goal:
   Prevent cross-tenant data leaks.
   Expected:
   All queries must include:
   tenant*id
   Audit tasks:
   Search for queries missing tenant filter.
   Example failure:
   SELECT * FROM conversations
   Expected:
   SELECT \_ FROM conversations
   WHERE tenant_id = :tenant_id
   Check middleware:
   get_tenant()
   Failure condition:
   any endpoint without tenant validation

8. Token Usage Logging Audit
   Goal:
   Ensure cost monitoring works.
   Verify existence of:
   usage_logs table
   UsageService
   Audit tasks:
   Ensure each LLM call logs:
   tenant_id
   model
   input_tokens
   output_tokens
   estimated_cost
   timestamp
   Failure condition:
   LLM call without logging

9. Monitoring Audit
   Goal:
   Ensure system observability.
   Expected metrics:
   request_count
   latency
   token_usage
   retrieval_latency
   LLM_latency
   Audit tasks:
   Verify monitoring module exists:
   app/monitoring
   Check logging inside:
   rag_service
   llm_service

10. Error Handling Audit
    Goal:
    Ensure production-safe error handling.
    Expected:
    User-facing errors must not expose internals.
    Example response:
    {
    "error": "internal_server_error"
    }
    Audit tasks:
    Search for stack traces returned to user.
    Failure condition:
    traceback returned in API response

11. Performance Audit
    Goal:
    Ensure RAG performance is acceptable.
    Verify:
    embedding caching
    vector index usage
    chunk size limits
    Check:
    pgvector index exists.
    Expected index:
    ivfflat or hnsw
    Warning:
    vector search without index

12. Final Audit Report
    Agent must produce report:

---

### Final Audit Report

- **Response Handler:** PASS (Routes delegate logic to services, no direct LLM or pgvector calls in routes)
- **RAG Pipeline:** PASS (Pipeline correctly flows query → embed → hybrid → rerank → context_builder → llm; limited chunks sent to LLM)
- **Hybrid Retrieval:** PASS (Implements both vector_search and keyword_search, merged using Reciprocal Rank Fusion)
- **Stateful Conversation:** PASS (ConversationService correctly persists messages and retrieves history per conversation)
- **Tenant Isolation:** PASS (All major entity queries are filtered by `tenant_id` at the service layer)
- **Usage Logging:** PASS (Token counts and costs are logged to usage_logs via UsageService after LLM generation)
- **Monitoring:** PASS (Request counts and latencies are tracked via middleware and `RequestMetrics` singleton)

**Specific Warnings & Observations:**

- **Conversation Compression:** WARNING (The `summarize_history` method and `summary` field exist, but automated summarization of older messages is not yet triggered in the RAG loop)
- **Performance:** WARNING (No `ivfflat` or `hnsw` index is defined on the `chunks.embedding` pgvector column. You must create one for production performance scale)

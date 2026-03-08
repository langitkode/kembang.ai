# Service Layer Design

Business logic must live inside services.
Routes must stay thin.

Chat request flow
route_chat.py
↓
conversation_service
↓
rag_service
↓
llm_service
↓
response

ConversationService
responsibility

- create conversation
- store messages
- retrieve history
- summarize history

methods
create_conversation()
get_conversation()
add_message()
get_recent_messages()
summarize_history()

RAGService
responsibility

- orchestrate retrieval
- build context

methods
retrieve_context()
build_prompt()
generate_response()

EmbeddingService
responsibility
generate embeddings.

methods
embed_query()
embed_document()

RetrievalService
responsibility
query vector database.

methods
vector_search()
keyword_search()
hybrid_search()

LLMService
responsibility
communicate with LLM provider.

methods
generate()
stream_generate()
route_model()

UsageService
responsibility
track token usage.

methods
log_usage()
estimate_cost()
tenant_usage_summary()

# Folder Structure

backend/

app/
main.py

    core/
        config.py
        security.py
        dependencies.py

    api/
        routes_auth.py
        routes_chat.py
        routes_kb.py
        routes_admin.py

    models/
        tenant.py
        user.py
        conversation.py
        message.py
        document.py

    services/
        conversation_service.py
        rag_service.py
        embedding_service.py
        retrieval_service.py
        llm_service.py

    rag/
        chunking.py
        hybrid_retrieval.py
        reranker.py
        context_builder.py

    tools/
        tool_router.py
        product_lookup.py
        order_status.py

    monitoring/
        usage_logger.py
        metrics.py

    db/
        session.py
        migrations/

workers/
document_ingest_worker.py

tests/

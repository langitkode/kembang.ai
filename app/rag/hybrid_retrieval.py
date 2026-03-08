"""Hybrid retrieval merging vector + keyword results.

This module is a thin convenience layer; the actual search logic lives in
``app.services.retrieval_service.RetrievalService``.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


async def hybrid_retrieve(
    query: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> list:
    """Convenience function: embed query then run hybrid search."""
    embedding_svc = EmbeddingService()
    retrieval_svc = RetrievalService(db)

    query_embedding = await embedding_svc.embed_query(query)
    return await retrieval_svc.hybrid_search(query_embedding, query, tenant_id)

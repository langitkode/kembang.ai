"""Retrieval service – vector and keyword search over chunks."""

import uuid

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Chunk, Document, KnowledgeBase


class RetrievalService:
    """Hybrid retrieval combining pgvector similarity + BM25 keyword search."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Vector search ─────────────────────────────────────────────────────

    async def vector_search(
        self,
        query_embedding: list[float],
        tenant_id: uuid.UUID,
        top_k: int | None = None,
    ) -> list[Chunk]:
        """Return top-k chunks nearest to *query_embedding* for the tenant."""
        top_k = top_k or settings.VECTOR_TOP_K

        stmt = (
            select(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .where(Chunk.embedding.isnot(None))
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ── Keyword search (BM25) ─────────────────────────────────────────────

    async def keyword_search(
        self,
        query_text: str,
        tenant_id: uuid.UUID,
        top_k: int | None = None,
    ) -> list[Chunk]:
        """In-memory BM25 keyword ranking over tenant chunks."""
        top_k = top_k or settings.KEYWORD_TOP_K

        stmt = (
            select(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .where(KnowledgeBase.tenant_id == tenant_id)
        )
        result = await self._db.execute(stmt)
        all_chunks: list[Chunk] = list(result.scalars().all())

        if not all_chunks:
            return []

        # Tokenize and rank
        tokenized_corpus = [c.content.lower().split() for c in all_chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(query_text.lower().split())

        scored = sorted(
            zip(all_chunks, scores), key=lambda x: x[1], reverse=True
        )
        return [chunk for chunk, _ in scored[:top_k]]

    # ── Hybrid search ─────────────────────────────────────────────────────

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        tenant_id: uuid.UUID,
    ) -> list[Chunk]:
        """Merge vector + keyword results using reciprocal rank fusion."""
        vector_results = await self.vector_search(query_embedding, tenant_id)
        keyword_results = await self.keyword_search(query_text, tenant_id)
        return self._reciprocal_rank_fusion(vector_results, keyword_results)

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _reciprocal_rank_fusion(
        *result_lists: list[Chunk],
        k: int = 60,
    ) -> list[Chunk]:
        """Combine multiple ranked lists via RRF.

        RRF score = Σ 1 / (k + rank) across all lists.
        """
        scores: dict[uuid.UUID, float] = {}
        chunk_map: dict[uuid.UUID, Chunk] = {}

        for result_list in result_lists:
            for rank, chunk in enumerate(result_list, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
                chunk_map[chunk.id] = chunk

        sorted_ids = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
        return [chunk_map[cid] for cid in sorted_ids]

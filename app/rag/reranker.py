"""Chunk reranking using a lightweight scoring approach.

For v1, we use a simple LLM-based relevance scoring.
In production, swap for a cross-encoder model (e.g. bge-reranker).
"""

from app.core.config import settings
from app.models.document import Chunk


async def rerank(
    query: str,
    chunks: list[Chunk],
    top_k: int | None = None,
) -> list[Chunk]:
    """Rerank *chunks* by relevance to *query*.

    v1 implementation: simple keyword-overlap scoring.
    Future: plug in cross-encoder or LLM-based reranker.
    """
    top_k = top_k or settings.RERANK_TOP_K

    if not chunks:
        return []

    # Simple relevance score: count query-term overlaps in chunk content
    query_terms = set(query.lower().split())

    def _score(chunk: Chunk) -> float:
        chunk_terms = set(chunk.content.lower().split())
        overlap = query_terms & chunk_terms
        return len(overlap) / max(len(query_terms), 1)

    scored = sorted(chunks, key=_score, reverse=True)
    return scored[:top_k]

"""Chunk reranking using cross-encoder model for better relevance scoring.

Uses bge-reranker-base (free, local, 109MB) for production-quality reranking.
Fallback to keyword-based scoring if model unavailable.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.models.document import Chunk

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for chunk relevance scoring."""

    MODEL_NAME = "BAAI/bge-reranker-base"
    DEFAULT_THRESHOLD = 0.3

    def __init__(self):
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """Lazy-load reranker model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(
                    self.MODEL_NAME,
                    cache_folder="/tmp/huggingface"
                )
                logger.info("Reranker model loaded: %s", self.MODEL_NAME)
            except Exception as e:
                logger.warning("Failed to load reranker model: %s. Using keyword fallback.", e)
                return False
        return True

    def rerank(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int = 5,
        threshold: float = None,
    ) -> list[Chunk]:
        """Rerank chunks by relevance to query using cross-encoder.

        Args:
            query: Search query
            chunks: List of chunks to rerank
            top_k: Number of top chunks to return
            threshold: Minimum relevance score (0.0-1.0)

        Returns:
            List of reranked chunks
        """
        if not chunks:
            return []

        threshold = threshold or self.DEFAULT_THRESHOLD

        # Try cross-encoder reranking
        if self._load_model():
            try:
                return self._rerank_with_model(query, chunks, top_k, threshold)
            except Exception as e:
                logger.warning("Cross-encoder reranking failed: %s. Using keyword fallback.", e)

        # Fallback to keyword-based scoring
        return self._rerank_with_keywords(query, chunks, top_k)

    def _rerank_with_model(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int,
        threshold: float,
    ) -> list[Chunk]:
        """Rerank using cross-encoder model."""
        # Prepare pairs for model
        pairs = [[query, chunk.content] for chunk in chunks]

        # Get scores
        scores = self._model.predict(pairs)

        # Filter by threshold
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            if score >= threshold:
                scored_chunks.append((chunk, float(score)))

        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Return top_k
        return [chunk for chunk, _ in scored_chunks[:top_k]]

    def _rerank_with_keywords(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int,
        threshold: float,
    ) -> list[Chunk]:
        """Fallback: keyword-based reranking."""
        query_terms = set(query.lower().split())

        def _score(chunk: Chunk) -> float:
            chunk_terms = set(chunk.content.lower().split())
            overlap = query_terms & chunk_terms
            return len(overlap) / max(len(query_terms), 1)

        # Filter by threshold (convert to keyword score equivalent)
        keyword_threshold = threshold * 0.5  # Rough conversion
        scored = [(chunk, _score(chunk)) for chunk in chunks]
        scored = [(c, s) for c, s in scored if s >= keyword_threshold]

        # Sort and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in scored[:top_k]]


# Global instance
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get or create global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker


async def rerank(
    query: str,
    chunks: list[Chunk],
    top_k: int | None = None,
) -> list[Chunk]:
    """Rerank chunks by relevance to query.

    Uses cross-encoder model (bge-reranker-base) for production-quality scoring.
    Falls back to keyword overlap if model unavailable.
    """
    top_k = top_k or settings.RERANK_TOP_K
    reranker = get_reranker()
    return reranker.rerank(query, chunks, top_k)

"""Embedding service – generate vector embeddings via SentenceTransformers locally."""

import logging
import time
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton instance for the model to avoid re-loading on every request
_MODEL_CACHE = {}

def get_model():
    """Load and cache the SentenceTransformer model."""
    if "model" not in _MODEL_CACHE:
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        start = time.perf_counter()
        _MODEL_CACHE["model"] = SentenceTransformer("all-MiniLM-L6-v2")
        elapsed = time.perf_counter() - start
        logger.info("Model loaded in %.2f seconds", elapsed)
    return _MODEL_CACHE["model"]


class EmbeddingService:
    """Wrapper around local HuggingFace sentence-transformers."""

    def __init__(self):
        # Use the singleton model
        self._model = get_model()

    async def embed_query(self, text: str) -> list[float]:
        """Return the embedding vector for a single query string."""
        embedding = self._model.encode(text)
        return embedding.tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        if not texts:
            return []
        embeddings = self._model.encode(texts)
        return embeddings.tolist()

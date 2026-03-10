"""Embedding service – generate vector embeddings via SentenceTransformers locally."""

import logging
import time
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.utils.circuit_breaker import get_embedding_breaker

logger = logging.getLogger(__name__)

# Singleton instance for the model to avoid re-loading on every request
_MODEL_CACHE = {}
_MODEL_LOCK = None

# Use a shared cache directory with proper permissions
if os.name == "posix":  # Linux/Unix (including HF Spaces)
    _CACHE_DIR = Path("/tmp/huggingface")
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["TRANSFORMERS_CACHE"] = str(_CACHE_DIR)
    os.environ["HF_HOME"] = str(_CACHE_DIR)
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(_CACHE_DIR)
else:
    _CACHE_DIR = Path.home() / ".cache" / "huggingface"


def get_model():
    """Load and cache the SentenceTransformer model with file-based locking."""
    global _MODEL_LOCK
    
    # Check in-memory cache first
    if "model" in _MODEL_CACHE:
        return _MODEL_CACHE["model"]
    
    # Use threading lock if available
    if _MODEL_LOCK is None:
        try:
            import threading
            _MODEL_LOCK = threading.Lock()
        except ImportError:
            _MODEL_LOCK = type('FakeLock', (), {'__enter__': lambda s: s, '__exit__': lambda s, *a: None})()
    
    with _MODEL_LOCK:
        # Double-check after acquiring lock
        if "model" in _MODEL_CACHE:
            return _MODEL_CACHE["model"]
        
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        logger.info("Using cache directory: %s", _CACHE_DIR)
        
        start = time.perf_counter()
        
        try:
            # Load model with explicit cache directory
            _MODEL_CACHE["model"] = SentenceTransformer(
                "all-MiniLM-L6-v2",
                cache_folder=str(_CACHE_DIR)
            )
            elapsed = time.perf_counter() - start
            logger.info("Model loaded in %.2f seconds", elapsed)
        except OSError as e:
            if "PermissionError" in str(e) or "permission" in str(e).lower():
                logger.warning(
                    "Permission error loading model. Another worker may be loading it. "
                    "Waiting 2 seconds and retrying..."
                )
                time.sleep(2)
                # Retry once with fresh cache check
                _MODEL_CACHE["model"] = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    cache_folder=str(_CACHE_DIR)
                )
            else:
                raise
        
        return _MODEL_CACHE["model"]


class EmbeddingService:
    """Wrapper around local HuggingFace sentence-transformers."""

    def __init__(self):
        # Use the singleton model
        try:
            self._model = get_model()
            logger.info("EmbeddingService initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize embedding model: %s", e)
            raise
        self._breaker = get_embedding_breaker()

    async def embed_query(self, text: str) -> list[float]:
        """Return the embedding vector for a single query string."""
        return await self._breaker.call(self._embed_query_internal, text)

    def _embed_query_internal(self, text: str) -> list[float]:
        """Internal embedding method (wrapped by circuit breaker)."""
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return [0.0] * 384  # Return zero vector for empty input

            embedding = self._model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error("Embedding query failed: %s (text length: %d)", e, len(text))
            raise

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        if not texts:
            return []
        return await self._breaker.call(self._embed_documents_internal, texts)

    def _embed_documents_internal(self, texts: list[str]) -> list[list[float]]:
        """Internal batch embedding method (wrapped by circuit breaker)."""
        try:
            # Filter empty texts
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                logger.warning("All texts empty for embedding")
                return [[0.0] * 384 for _ in texts]

            embeddings = self._model.encode(valid_texts)

            # Pad with zero vectors for empty texts
            result = []
            valid_idx = 0
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[valid_idx].tolist())
                    valid_idx += 1
                else:
                    result.append([0.0] * 384)

            return result
        except Exception as e:
            logger.error("Embedding documents failed: %s (batch size: %d)", e, len(texts))
            raise

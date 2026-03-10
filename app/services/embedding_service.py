"""Embedding service – generate vector embeddings via SentenceTransformers locally."""

import logging
import time
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

from app.core.config import settings

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

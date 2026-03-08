"""Response cache for LLM responses.

Caches responses for repeated queries to avoid unnecessary LLM calls.
Uses TTL-based caching with configurable expiration.
"""

import hashlib
import logging
from typing import Optional
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class ResponseCache:
    """Cache for LLM responses with TTL support."""

    def __init__(
        self,
        maxsize: int = 1000,
        ttl: int = 7200,  # 2 hours default
    ):
        """Initialize response cache.
        
        Args:
            maxsize: Maximum number of cached responses
            ttl: Time-to-live in seconds (default: 2 hours)
        """
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, tenant_id: str, query: str, context_hash: str) -> str:
        """Create cache key from tenant, query, and context."""
        key_data = f"{tenant_id}:{query}:{context_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(
        self,
        tenant_id: str,
        query: str,
        context_hash: str = "default",
    ) -> Optional[dict]:
        """Get cached response if available.
        
        Args:
            tenant_id: Tenant identifier
            query: User query
            context_hash: Hash of context used (to ensure same context)
        
        Returns:
            Cached response dict or None
        """
        key = self._make_key(tenant_id, query.lower().strip(), context_hash)
        result = self._cache.get(key)
        
        if result is not None:
            self._hits += 1
            logger.info(
                "Cache HIT for query: %s (hit rate: %.1f%%)",
                query[:50],
                self.hit_rate
            )
        else:
            self._misses += 1
            logger.debug("Cache MISS for query: %s", query[:50])
        
        return result
    
    def set(
        self,
        tenant_id: str,
        query: str,
        response: dict,
        context_hash: str = "default",
    ):
        """Cache a response.
        
        Args:
            tenant_id: Tenant identifier
            query: User query
            response: Response dict to cache
            context_hash: Hash of context used
        """
        key = self._make_key(tenant_id, query.lower().strip(), context_hash)
        self._cache[key] = response
        logger.debug("Cached response for query: %s", query[:50])
    
    def clear(self):
        """Clear all cached responses."""
        self._cache.clear()
        logger.info("Response cache cleared")
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return (self._hits / total) * 100
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "maxsize": self._cache.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


# Global cache instance
_default_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Get or create global response cache."""
    global _default_cache
    if _default_cache is None:
        _default_cache = ResponseCache(
            maxsize=1000,  # Cache up to 1000 responses
            ttl=7200,      # Expire after 2 hours
        )
        logger.info("Response cache initialized (maxsize=1000, ttl=2h)")
    return _default_cache

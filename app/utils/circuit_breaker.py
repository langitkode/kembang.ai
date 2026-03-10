"""Circuit breaker pattern for fault-tolerant service calls."""

import logging
import time
import asyncio
from functools import wraps
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker with exponential backoff retry logic.

    Usage:
        breaker = CircuitBreaker(max_failures=3, timeout=60)

        async def call_service():
            return await breaker.call(expensive_service_func, arg1, arg2)

        # Or use decorator:
        @breaker
        async def my_func():
            ...
    """

    def __init__(
        self,
        max_failures: int = 3,
        timeout: int = 60,
        exponential_base: int = 2,
        max_delay: int = 30,
    ):
        """
        Args:
            max_failures: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (half-open)
            exponential_base: Base for exponential backoff
            max_delay: Maximum delay between retries in seconds
        """
        self.max_failures = max_failures
        self.timeout = timeout
        self.exponential_base = exponential_base
        self.max_delay = max_delay

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        async with self._lock:
            if not self._can_execute():
                logger.warning(
                    "Circuit breaker OPEN - rejecting call to %s",
                    func.__name__
                )
                raise CircuitBreakerError(
                    f"Circuit breaker is open for {func.__name__}"
                )

        # Try call with exponential backoff retry
        last_exception = None
        for attempt in range(self.max_failures):
            try:
                result = await func(*args, **kwargs)

                # Success - reset circuit
                async with self._lock:
                    self._on_success()

                return result

            except Exception as e:
                last_exception = e
                async with self._lock:
                    self._on_failure()

                if attempt < self.max_failures - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        "Attempt %d failed for %s: %s. Retrying in %ds...",
                        attempt + 1,
                        func.__name__,
                        str(e),
                        delay
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "All %d attempts failed for %s: %s",
                        self.max_failures,
                        func.__name__,
                        str(e)
                    )

        # All attempts failed
        raise last_exception

    def _can_execute(self) -> bool:
        """Check if circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time is None:
                return True

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.timeout:
                # Transition to half-open
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker HALF-OPEN - testing recovery")
                return True

            return False

        # HALF_OPEN - allow one test call
        return True

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.max_failures:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit breaker OPEN after %d failures",
                self.failure_count
            )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.exponential_base ** attempt,
            self.max_delay
        )
        # Add jitter (±10%)
        jitter = delay * 0.1
        return delay + (jitter if attempt % 2 == 0 else -jitter)

    def __call__(self, func: Callable) -> Callable:
        """Decorator usage."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper

    def reset(self):
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


# Global circuit breakers for services
_llm_breaker: Optional[CircuitBreaker] = None
_embedding_breaker: Optional[CircuitBreaker] = None
_retrieval_breaker: Optional[CircuitBreaker] = None


def get_llm_breaker() -> CircuitBreaker:
    """Get or create LLM service circuit breaker."""
    global _llm_breaker
    if _llm_breaker is None:
        _llm_breaker = CircuitBreaker(
            max_failures=5,      # Increased from 3 for tolerance
            timeout=90,          # Increased from 60 for slow recovery
            max_delay=15         # Increased from 10
        )
    return _llm_breaker


def get_embedding_breaker() -> CircuitBreaker:
    """Get or create embedding service circuit breaker."""
    global _embedding_breaker
    if _embedding_breaker is None:
        _embedding_breaker = CircuitBreaker(
            max_failures=5,      # Increased from 3 for tolerance
            timeout=120,         # Increased from 30 for slow model load
            max_delay=30         # Increased from 5 for cold start
        )
    return _embedding_breaker


def get_retrieval_breaker() -> CircuitBreaker:
    """Get or create retrieval service circuit breaker."""
    global _retrieval_breaker
    if _retrieval_breaker is None:
        _retrieval_breaker = CircuitBreaker(
            max_failures=5,      # Increased from 3 for tolerance
            timeout=60,          # Standard timeout
            max_delay=10         # Standard max delay
        )
    return _retrieval_breaker

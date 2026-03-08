"""Request metrics – in-memory counters (OpenTelemetry-ready stub)."""

import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RequestMetrics:
    """Simple in-memory request counter and latency tracker.

    This is a lightweight placeholder. In production, replace with
    OpenTelemetry-based instrumentation.
    """

    def __init__(self):
        self._request_count: int = 0
        self._latencies: list[float] = []
        self._errors: int = 0
        self._endpoint_counts: dict[str, int] = defaultdict(int)

    def record_request(self, endpoint: str, latency_ms: float, error: bool = False):
        """Record a single request."""
        self._request_count += 1
        self._latencies.append(latency_ms)
        self._endpoint_counts[endpoint] += 1
        if error:
            self._errors += 1

    def summary(self) -> dict:
        """Return a snapshot of current metrics."""
        avg_latency = (
            sum(self._latencies) / len(self._latencies) if self._latencies else 0
        )
        return {
            "total_requests": self._request_count,
            "total_errors": self._errors,
            "avg_latency_ms": round(avg_latency, 2),
            "endpoints": dict(self._endpoint_counts),
        }


# Module-level singleton
metrics = RequestMetrics()

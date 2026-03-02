"""Thread-safe in-memory cache for chart data with TTL.

Stores chart configurations temporarily so that the Reflex chart
route can retrieve data by chart_id.
"""

import logging
import threading
import time
import uuid

from appkit_mcpapp.models.schemas import ChartConfig

logger = logging.getLogger(__name__)

# Default TTL: 10 minutes
_DEFAULT_TTL_SECONDS = 600


class ChartCache:
    """Thread-safe in-memory cache for chart configurations."""

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self._cache: dict[str, tuple[ChartConfig, float]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def store(self, config: ChartConfig) -> str:
        """Store a chart configuration and return its ID.

        Args:
            config: The chart configuration to store.

        Returns:
            The chart_id used as the cache key.
        """
        chart_id = config.chart_id or str(uuid.uuid4())
        config.chart_id = chart_id
        with self._lock:
            self._cache[chart_id] = (config, time.time())
            self._cleanup_expired()
        logger.debug("Stored chart config: %s", chart_id)
        return chart_id

    def get(self, chart_id: str) -> ChartConfig | None:
        """Retrieve a chart configuration by ID.

        Args:
            chart_id: The chart ID to look up.

        Returns:
            The chart configuration, or None if not found or expired.
        """
        with self._lock:
            entry = self._cache.get(chart_id)
            if entry is None:
                logger.debug("Chart not found in cache: %s", chart_id)
                return None
            config, stored_at = entry
            if time.time() - stored_at > self._ttl:
                logger.debug("Chart expired: %s", chart_id)
                del self._cache[chart_id]
                return None
            return config

    def remove(self, chart_id: str) -> None:
        """Remove a chart configuration from cache.

        Args:
            chart_id: The chart ID to remove.
        """
        with self._lock:
            self._cache.pop(chart_id, None)

    def _cleanup_expired(self) -> None:
        """Remove expired entries. Must be called with lock held."""
        now = time.time()
        expired = [
            k
            for k, (_, stored_at) in self._cache.items()
            if now - stored_at > self._ttl
        ]
        for key in expired:
            del self._cache[key]
        if expired:
            logger.debug("Cleaned up %d expired chart entries", len(expired))


# Module-level singleton
_chart_cache: ChartCache = ChartCache()


def get_chart_cache() -> ChartCache:
    """Get the global chart cache singleton.

    Returns:
        The shared ChartCache instance.
    """
    return _chart_cache

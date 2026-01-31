import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Final, Self

from appkit_assistant.backend.database.repositories import system_prompt_repo
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)

# Cache TTL in seconds (default: 5 minutes)
CACHE_TTL_SECONDS: Final[int] = 300


class SystemPromptCache:
    """Singleton cache for system prompt with TTL-based invalidation.

    Features:
    - Lazy loading on first access
    - Automatic cache invalidation after TTL expires
    - Thread-safe with asyncio lock
    - Manual invalidation support for immediate updates
    """

    _instance: "SystemPromptCache | None" = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> Self:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # noqa: SLF001
        return cls._instance

    def __init__(self) -> None:
        """Initialize cache state (only once due to singleton)."""
        if self._initialized:
            return

        self._cached_prompt: str | None = None
        self._cached_version: int | None = None
        self._cache_timestamp: datetime | None = None
        self._ttl_seconds: int = CACHE_TTL_SECONDS
        self._initialized = True

        logger.debug(
            "SystemPromptCache initialized with TTL=%d seconds",
            self._ttl_seconds,
        )

    def _is_cache_valid(self) -> bool:
        """Check if cached prompt is still valid based on TTL."""
        if self._cached_prompt is None or self._cache_timestamp is None:
            return False

        elapsed = datetime.now(UTC) - self._cache_timestamp
        is_valid = elapsed < timedelta(seconds=self._ttl_seconds)

        if not is_valid:
            logger.debug("Cache expired after %s seconds", elapsed.total_seconds())

        return is_valid

    async def get_prompt(self) -> str:
        """Get the latest system prompt (from cache or database).

        Returns:
            The current system prompt text.

        Raises:
            ValueError: If no system prompt exists in database.
        """
        async with self._lock:
            if self._is_cache_valid():
                logger.debug(
                    "Cache hit: version=%d, age=%s seconds",
                    self._cached_version,
                    (datetime.now(UTC) - self._cache_timestamp).total_seconds(),
                )
                return self._cached_prompt

            # Cache miss or expired - fetch from database
            logger.debug("Cache miss - fetching latest prompt from database")

            async with get_asyncdb_session() as session:
                latest_prompt = await system_prompt_repo.find_latest(session)

                if latest_prompt is None:
                    # Raise inside to exit or handle outside
                    pass
                else:
                    # Capture values while attached
                    prompt_text = latest_prompt.prompt
                    prompt_version = latest_prompt.version

            if latest_prompt is None:
                msg = "No system prompt found in database"
                logger.error(msg)
                raise ValueError(msg)

            self._cached_prompt = prompt_text
            self._cached_version = prompt_version
            self._cache_timestamp = datetime.now(UTC)

            logger.debug(
                "Cached prompt version %d (%d characters)",
                self._cached_version,
                len(self._cached_prompt),
            )

            return self._cached_prompt

    async def invalidate(self) -> None:
        """Manually invalidate the cache.

        Use this when a new prompt version is created to force
        immediate reload on next access.
        """
        async with self._lock:
            if self._cached_prompt is not None:
                logger.debug(
                    "Cache invalidated (was version %d)",
                    self._cached_version,
                )
                self._cached_prompt = None
                self._cached_version = None
                self._cache_timestamp = None
            else:
                logger.debug("Cache invalidation called but cache was empty")

    def set_ttl(self, seconds: int) -> None:
        """Update cache TTL.

        Args:
            seconds: New TTL in seconds.
        """
        self._ttl_seconds = seconds
        logger.debug("Cache TTL updated to %d seconds", seconds)

    @property
    def is_cached(self) -> bool:
        """Check if prompt is currently cached and valid."""
        return self._is_cache_valid()

    @property
    def cached_version(self) -> int | None:
        """Get the currently cached prompt version (if any)."""
        return self._cached_version if self._is_cache_valid() else None


# Global cache instance
_prompt_cache = SystemPromptCache()


async def get_system_prompt() -> str:
    """Convenience function to get the current system prompt.

    Returns:
        The current system prompt text.
    """
    return await _prompt_cache.get_prompt()


async def invalidate_prompt_cache() -> None:
    """Convenience function to invalidate the prompt cache."""
    await _prompt_cache.invalidate()


def get_cache_instance() -> SystemPromptCache:
    """Get the global cache instance for advanced usage."""
    return _prompt_cache

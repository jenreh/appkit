"""Tests for SystemPromptCache.

Covers caching, TTL-based invalidation, manual invalidation,
and error handling when no prompt exists.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.system_prompt_cache import (
    CACHE_TTL_SECONDS,
    SystemPromptCache,
)


@pytest.fixture
def fresh_cache() -> SystemPromptCache:
    """Create a fresh cache instance by resetting the singleton."""
    SystemPromptCache._instance = None
    return SystemPromptCache()


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton after each test."""
    yield
    SystemPromptCache._instance = None


class TestCacheInit:
    def test_singleton(self) -> None:
        SystemPromptCache._instance = None
        c1 = SystemPromptCache()
        c2 = SystemPromptCache()
        assert c1 is c2

    def test_defaults(self, fresh_cache: SystemPromptCache) -> None:
        assert fresh_cache.is_cached is False
        assert fresh_cache.cached_version is None
        assert fresh_cache._ttl_seconds == CACHE_TTL_SECONDS


class TestCacheValidity:
    def test_empty_cache_invalid(self, fresh_cache: SystemPromptCache) -> None:
        assert fresh_cache._is_cache_valid() is False

    def test_valid_cache(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 1
        fresh_cache._cache_timestamp = datetime.now(UTC)
        assert fresh_cache._is_cache_valid() is True

    def test_expired_cache(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 1
        fresh_cache._cache_timestamp = datetime.now(UTC) - timedelta(
            seconds=CACHE_TTL_SECONDS + 10
        )
        assert fresh_cache._is_cache_valid() is False


class TestGetPrompt:
    @pytest.mark.asyncio
    async def test_cache_hit(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache._cached_prompt = "cached prompt"
        fresh_cache._cached_version = 1
        fresh_cache._cache_timestamp = datetime.now(UTC)

        result = await fresh_cache.get_prompt()
        assert result == "cached prompt"

    @pytest.mark.asyncio
    async def test_cache_miss_loads_from_db(
        self, fresh_cache: SystemPromptCache
    ) -> None:
        mock_prompt = MagicMock()
        mock_prompt.prompt = "db prompt"
        mock_prompt.version = 2

        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.find_latest = AsyncMock(return_value=mock_prompt)

        with (
            patch(
                "appkit_assistant.backend.system_prompt_cache.get_asyncdb_session"
            ) as mock_ctx,
            patch(
                "appkit_assistant.backend.system_prompt_cache.system_prompt_repo",
                mock_repo,
            ),
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fresh_cache.get_prompt()
            assert result == "db prompt"
            assert fresh_cache._cached_version == 2
            assert fresh_cache._cached_prompt == "db prompt"

    @pytest.mark.asyncio
    async def test_no_prompt_raises(self, fresh_cache: SystemPromptCache) -> None:
        mock_repo = MagicMock()
        mock_repo.find_latest = AsyncMock(return_value=None)

        with (
            patch(
                "appkit_assistant.backend.system_prompt_cache.get_asyncdb_session"
            ) as mock_ctx,
            patch(
                "appkit_assistant.backend.system_prompt_cache.system_prompt_repo",
                mock_repo,
            ),
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="No system prompt found"):
                await fresh_cache.get_prompt()


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_clears_cache(
        self, fresh_cache: SystemPromptCache
    ) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 1
        fresh_cache._cache_timestamp = datetime.now(UTC)

        await fresh_cache.invalidate()
        assert fresh_cache._cached_prompt is None
        assert fresh_cache._cached_version is None
        assert fresh_cache._cache_timestamp is None

    @pytest.mark.asyncio
    async def test_invalidate_empty_cache_no_error(
        self, fresh_cache: SystemPromptCache
    ) -> None:
        await fresh_cache.invalidate()  # Should not raise


class TestSetTtl:
    def test_set_ttl(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache.set_ttl(60)
        assert fresh_cache._ttl_seconds == 60


class TestProperties:
    def test_is_cached_false_when_empty(self, fresh_cache: SystemPromptCache) -> None:
        assert fresh_cache.is_cached is False

    def test_is_cached_true_when_valid(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 1
        fresh_cache._cache_timestamp = datetime.now(UTC)
        assert fresh_cache.is_cached is True

    def test_cached_version_when_valid(self, fresh_cache: SystemPromptCache) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 5
        fresh_cache._cache_timestamp = datetime.now(UTC)
        assert fresh_cache.cached_version == 5

    def test_cached_version_none_when_expired(
        self, fresh_cache: SystemPromptCache
    ) -> None:
        fresh_cache._cached_prompt = "test"
        fresh_cache._cached_version = 5
        fresh_cache._cache_timestamp = datetime.now(UTC) - timedelta(
            seconds=CACHE_TTL_SECONDS + 10
        )
        assert fresh_cache.cached_version is None

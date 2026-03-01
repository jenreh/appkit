"""Tests for chart cache service."""

import time

import pytest

from appkit_mcpapp.models.schemas import ChartConfig
from appkit_mcpapp.services.chart_cache import ChartCache, get_chart_cache


@pytest.fixture
def cache() -> ChartCache:
    """Create a fresh chart cache with short TTL for testing."""
    return ChartCache(ttl_seconds=2)


@pytest.fixture
def chart_config() -> ChartConfig:
    """Create a sample chart configuration."""
    return ChartConfig(
        chart_id="test-123",
        data=[
            {"role": "admin", "count": 5},
            {"role": "user", "count": 15},
        ],
        x_axis="role",
        y_axes=["count"],
        chart_title="Test Chart",
    )


class TestChartCache:
    """Tests for ChartCache class."""

    def test_store_and_retrieve(
        self, cache: ChartCache, chart_config: ChartConfig
    ) -> None:
        chart_id = cache.store(chart_config)
        result = cache.get(chart_id)

        assert result is not None
        assert result.chart_id == chart_id
        assert result.x_axis == "role"
        assert result.y_axes == ["count"]
        assert len(result.data) == 2

    def test_store_assigns_chart_id(self, cache: ChartCache) -> None:
        config = ChartConfig(
            chart_id="",
            data=[{"a": 1}],
            x_axis="a",
            y_axes=["a"],
        )
        chart_id = cache.store(config)
        assert chart_id != ""
        assert config.chart_id == chart_id

    def test_store_preserves_existing_chart_id(
        self, cache: ChartCache, chart_config: ChartConfig
    ) -> None:
        chart_id = cache.store(chart_config)
        assert chart_id == "test-123"

    def test_get_nonexistent_returns_none(self, cache: ChartCache) -> None:
        assert cache.get("nonexistent") is None

    def test_get_expired_returns_none(
        self, cache: ChartCache, chart_config: ChartConfig
    ) -> None:
        cache.store(chart_config)
        time.sleep(2.1)
        assert cache.get("test-123") is None

    def test_remove(self, cache: ChartCache, chart_config: ChartConfig) -> None:
        cache.store(chart_config)
        cache.remove("test-123")
        assert cache.get("test-123") is None

    def test_remove_nonexistent_no_error(self, cache: ChartCache) -> None:
        cache.remove("nonexistent")

    def test_multiple_entries(self, cache: ChartCache) -> None:
        config1 = ChartConfig(
            chart_id="c1",
            data=[{"x": 1}],
            x_axis="x",
            y_axes=["x"],
        )
        config2 = ChartConfig(
            chart_id="c2",
            data=[{"y": 2}],
            x_axis="y",
            y_axes=["y"],
        )

        cache.store(config1)
        cache.store(config2)

        assert cache.get("c1") is not None
        assert cache.get("c2") is not None

    def test_cleanup_expired_on_store(self, cache: ChartCache) -> None:
        old = ChartConfig(
            chart_id="old",
            data=[{"a": 1}],
            x_axis="a",
            y_axes=["a"],
        )
        cache.store(old)
        time.sleep(2.1)

        new = ChartConfig(
            chart_id="new",
            data=[{"b": 2}],
            x_axis="b",
            y_axes=["b"],
        )
        cache.store(new)

        assert cache.get("old") is None
        assert cache.get("new") is not None


class TestGetChartCache:
    """Tests for get_chart_cache singleton."""

    def test_returns_instance(self) -> None:
        cache = get_chart_cache()
        assert isinstance(cache, ChartCache)

    def test_returns_same_instance(self) -> None:
        cache1 = get_chart_cache()
        cache2 = get_chart_cache()
        assert cache1 is cache2

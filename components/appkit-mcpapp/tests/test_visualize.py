"""Tests for visualize tool."""

import pytest

from appkit_mcpapp.services.chart_cache import get_chart_cache
from appkit_mcpapp.tools.visualize import visualize_users_as_barchart


@pytest.fixture
def sample_data() -> list[dict[str, object]]:
    """Sample tabular data for chart tests."""
    return [
        {"role": "admin", "count": 5},
        {"role": "user", "count": 15},
        {"role": "editor", "count": 8},
    ]


@pytest.fixture
def multi_series_data() -> list[dict[str, object]]:
    """Sample data with multiple numeric columns."""
    return [
        {"role": "admin", "count": 5, "active": 3, "pending": 2},
        {"role": "user", "count": 15, "active": 10, "pending": 5},
        {"role": "editor", "count": 8, "active": 6, "pending": 2},
    ]


class TestVisualizeUsersAsBarchart:
    """Tests for visualize_users_as_barchart tool."""

    @pytest.mark.asyncio
    async def test_successful_visualization(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            chart_title="Users by Role",
        )

        assert result.success is True
        assert result.chart_id != ""
        assert result.html != ""
        assert result.preview_url != ""
        assert "Plotly.newPlot" in result.html
        assert "Users by Role" in result.html

    @pytest.mark.asyncio
    async def test_empty_data_returns_error(self) -> None:
        result = await visualize_users_as_barchart(
            [],
            x_axis="role",
            y_axes=["count"],
        )

        assert result.success is False
        assert result.error is not None
        assert "No data" in result.error

    @pytest.mark.asyncio
    async def test_invalid_x_axis(self, sample_data: list[dict[str, object]]) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="nonexistent",
            y_axes=["count"],
        )

        assert result.success is False
        assert "nonexistent" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invalid_y_axis(self, sample_data: list[dict[str, object]]) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["nonexistent"],
        )

        assert result.success is False
        assert "nonexistent" in (result.error or "")

    @pytest.mark.asyncio
    async def test_chart_stored_in_cache(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
        )

        assert result.success is True
        cache = get_chart_cache()
        config = cache.get(result.chart_id)
        assert config is not None
        assert config.x_axis == "role"
        assert config.y_axes == ["count"]
        assert config.bar_mode == "group"

    @pytest.mark.asyncio
    async def test_custom_base_url(self, sample_data: list[dict[str, object]]) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            base_url="https://example.com",
        )

        assert result.success is True
        assert "https://example.com" in result.preview_url

    @pytest.mark.asyncio
    async def test_html_contains_chart_elements(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            chart_title="Test Title",
        )

        assert result.success is True
        assert "plotly-graph-div" in result.html
        assert "Plotly.newPlot" in result.html
        assert "Test Title" in result.html

    @pytest.mark.asyncio
    async def test_preview_url_contains_chart_id(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
        )

        assert result.success is True
        assert result.chart_id in result.preview_url


class TestMultiSeriesBarchart:
    """Tests for multi-series barchart support."""

    @pytest.mark.asyncio
    async def test_multiple_y_axes(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active", "pending"],
            chart_title="Multi-Series Chart",
        )

        assert result.success is True
        assert "count" in result.html
        assert "active" in result.html
        assert "pending" in result.html

    @pytest.mark.asyncio
    async def test_grouped_bar_mode(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="group",
        )

        assert result.success is True
        cache = get_chart_cache()
        config = cache.get(result.chart_id)
        assert config is not None
        assert config.bar_mode == "group"
        assert "group" in result.html.lower()

    @pytest.mark.asyncio
    async def test_stacked_bar_mode(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="stack",
        )

        assert result.success is True
        cache = get_chart_cache()
        config = cache.get(result.chart_id)
        assert config is not None
        assert config.bar_mode == "stack"
        assert "stack" in result.html.lower()

    @pytest.mark.asyncio
    async def test_percent_bar_mode(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="percent",
        )

        assert result.success is True
        cache = get_chart_cache()
        config = cache.get(result.chart_id)
        assert config is not None
        assert config.bar_mode == "percent"
        assert "percent" in result.html.lower()

    @pytest.mark.asyncio
    async def test_invalid_bar_mode(self, sample_data: list[dict[str, object]]) -> None:
        result = await visualize_users_as_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            bar_mode="invalid",
        )

        assert result.success is False
        assert "Invalid bar_mode" in (result.error or "")
        assert "group" in (result.error or "")
        assert "stack" in (result.error or "")
        assert "percent" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invalid_y_axis_in_multi_series(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "nonexistent"],
        )

        assert result.success is False
        assert "nonexistent" in (result.error or "")

    @pytest.mark.asyncio
    async def test_cache_stores_multiple_y_axes(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await visualize_users_as_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active", "pending"],
        )

        assert result.success is True
        cache = get_chart_cache()
        config = cache.get(result.chart_id)
        assert config is not None
        assert config.y_axes == ["count", "active", "pending"]

"""Tests for visualize tool."""

import pytest

from appkit_mcpapp.tools.visualize import generate_barchart


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


class TestGenerateBarchart:
    """Tests for generate_barchart tool."""

    @pytest.mark.asyncio
    async def test_successful_visualization(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            chart_title="Users by Role",
        )

        assert result.success is True
        assert result.html != ""
        assert "Plotly.newPlot" in result.html
        assert "Users by Role" in result.html

    @pytest.mark.asyncio
    async def test_empty_data_returns_error(self) -> None:
        result = await generate_barchart(
            [],
            x_axis="role",
            y_axes=["count"],
        )

        assert result.success is False
        assert result.error is not None
        assert "No data provided" in result.error

    @pytest.mark.asyncio
    async def test_invalid_x_axis(self, sample_data: list[dict[str, object]]) -> None:
        result = await generate_barchart(
            sample_data,
            x_axis="nonexistent",
            y_axes=["count"],
        )

        assert result.success is False
        assert result.error is not None
        assert "Column 'nonexistent' not found" in result.error

    @pytest.mark.asyncio
    async def test_invalid_y_axis(self, sample_data: list[dict[str, object]]) -> None:
        result = await generate_barchart(
            sample_data,
            x_axis="role",
            y_axes=["nonexistent"],
        )

        assert result.success is False
        assert result.error is not None
        assert "Column 'nonexistent' not found" in result.error

    @pytest.mark.asyncio
    async def test_html_contains_chart_elements(
        self, sample_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            chart_title="Test Title",
        )

        assert result.success is True
        assert "plotly-graph-div" in result.html
        assert "Plotly.newPlot" in result.html
        assert "Test Title" in result.html


class TestMultiSeriesBarchart:
    """Tests for multi-series barchart support."""

    @pytest.mark.asyncio
    async def test_multiple_y_axes(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
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
        result = await generate_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="group",
        )

        assert result.success is True
        assert "group" in result.html.lower()

    @pytest.mark.asyncio
    async def test_stacked_bar_mode(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="stack",
        )

        assert result.success is True
        assert "stack" in result.html.lower()

    @pytest.mark.asyncio
    async def test_percent_bar_mode(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "active"],
            bar_mode="percent",
        )

        assert result.success is True
        assert "percent" in result.html.lower()

    @pytest.mark.asyncio
    async def test_invalid_bar_mode(self, sample_data: list[dict[str, object]]) -> None:
        result = await generate_barchart(
            sample_data,
            x_axis="role",
            y_axes=["count"],
            bar_mode="invalid",
        )

        assert result.success is False
        assert result.error is not None
        # The exact error message depends on implementation details I don't see fully
        # But expecting something about invalid bar_mode
        assert "bar_mode" in result.error

    @pytest.mark.asyncio
    async def test_invalid_y_axis_in_multi_series(
        self, multi_series_data: list[dict[str, object]]
    ) -> None:
        result = await generate_barchart(
            multi_series_data,
            x_axis="role",
            y_axes=["count", "nonexistent"],
        )

        assert result.success is False
        assert result.error is not None
        assert "Column 'nonexistent' not found" in result.error

import pytest

from appkit_mcp_charts.tools.visualize import BarChartGenerator


def test_bar_chart_generator_init() -> None:
    """Test generator initialization."""
    generator = BarChartGenerator()
    assert generator.chart_type == "barchart"


@pytest.mark.asyncio
async def test_bar_chart_generator_success() -> None:
    """Test successful bar chart generation."""
    generator = BarChartGenerator()
    data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
    ]

    result = await generator.generate(
        data=data,
        x_axis="category",
        y_axes=["value"],
        chart_title="Test Chart",
        bar_mode="group",
    )

    assert result.success is True
    assert result.html is not None
    assert 'class="plotly-graph-div"' in result.html


@pytest.mark.asyncio
async def test_bar_chart_generator_validation_error() -> None:
    """Test validation failure (missing columns)."""
    generator = BarChartGenerator()
    data = [{"category": "A"}]  # Missing "value"

    result = await generator.generate(data=data, x_axis="category", y_axes=["value"])

    assert result.success is False
    assert result.error is not None
    assert "Column 'value' not found" in result.error


@pytest.mark.asyncio
async def test_bar_chart_generator_invalid_mode() -> None:
    """Test invalid bar mode."""
    generator = BarChartGenerator()
    data = [{"category": "A", "value": 10}]

    result = await generator.generate(
        data=data, x_axis="category", y_axes=["value"], bar_mode="invalid_mode"
    )

    assert result.success is False
    assert "Invalid bar_mode" in (result.error or "")

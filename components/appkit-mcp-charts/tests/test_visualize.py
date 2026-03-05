import pytest

from appkit_mcp_charts.tools.visualize import (
    BarChartGenerator,
    BubbleChartGenerator,
    HorizontalBarChartGenerator,
    LineChartGenerator,
    PieChartGenerator,
)


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


# -- Empty data validation --


@pytest.mark.asyncio
async def test_bar_chart_empty_data() -> None:
    gen = BarChartGenerator()
    result = await gen.generate(data=[], x_axis="x", y_axes=["y"])
    assert result.success is False
    assert "No data" in (result.error or "")


# -- Bar chart percent mode --


@pytest.mark.asyncio
async def test_bar_chart_percent_mode() -> None:
    gen = BarChartGenerator()
    data = [
        {"cat": "A", "v1": 10, "v2": 20},
        {"cat": "B", "v1": 30, "v2": 40},
    ]
    result = await gen.generate(
        data=data,
        x_axis="cat",
        y_axes=["v1", "v2"],
        bar_mode="percent",
    )
    assert result.success is True


# -- Pie chart tests --


class TestPieChartGenerator:
    def test_init(self) -> None:
        gen = PieChartGenerator()
        assert gen.chart_type == "piechart"

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = PieChartGenerator()
        data = [
            {"label": "A", "count": 10},
            {"label": "B", "count": 20},
        ]
        result = await gen.generate(
            data=data,
            labels_column="label",
            values_column="count",
        )
        assert result.success is True
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_donut(self) -> None:
        gen = PieChartGenerator()
        data = [
            {"label": "A", "count": 10},
        ]
        result = await gen.generate(
            data=data,
            labels_column="label",
            values_column="count",
            donut=True,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_missing_column(self) -> None:
        gen = PieChartGenerator()
        data = [{"label": "A"}]
        result = await gen.generate(
            data=data,
            labels_column="label",
            values_column="count",
        )
        assert result.success is False
        assert "Column 'count' not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_non_numeric_values(self) -> None:
        gen = PieChartGenerator()
        data = [{"label": "A", "count": "not_a_number"}]
        result = await gen.generate(
            data=data,
            labels_column="label",
            values_column="count",
        )
        assert result.success is False
        assert "numeric" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_empty_data(self) -> None:
        gen = PieChartGenerator()
        result = await gen.generate(
            data=[],
            labels_column="label",
            values_column="count",
        )
        assert result.success is False


# -- Line chart tests --


class TestLineChartGenerator:
    def test_init(self) -> None:
        gen = LineChartGenerator()
        assert gen.chart_type == "linechart"

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = LineChartGenerator()
        data = [
            {"month": "Jan", "sales": 100},
            {"month": "Feb", "sales": 150},
        ]
        result = await gen.generate(
            data=data,
            x_axis="month",
            y_axes=["sales"],
        )
        assert result.success is True
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_markers_mode(self) -> None:
        gen = LineChartGenerator()
        data = [{"x": 1, "y": 2}]
        result = await gen.generate(
            data=data,
            x_axis="x",
            y_axes=["y"],
            line_mode="markers",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_invalid_mode(self) -> None:
        gen = LineChartGenerator()
        data = [{"x": 1, "y": 2}]
        result = await gen.generate(
            data=data,
            x_axis="x",
            y_axes=["y"],
            line_mode="bad",
        )
        assert result.success is False
        assert "Invalid line_mode" in (result.error or "")

    @pytest.mark.asyncio
    async def test_missing_column(self) -> None:
        gen = LineChartGenerator()
        data = [{"x": 1}]
        result = await gen.generate(data=data, x_axis="x", y_axes=["y"])
        assert result.success is False

    @pytest.mark.asyncio
    async def test_multiple_series(self) -> None:
        gen = LineChartGenerator()
        data = [
            {"x": 1, "a": 10, "b": 20},
            {"x": 2, "a": 15, "b": 25},
        ]
        result = await gen.generate(
            data=data,
            x_axis="x",
            y_axes=["a", "b"],
            line_mode="lines+markers",
        )
        assert result.success is True


# -- Bubble chart tests --


class TestBubbleChartGenerator:
    def test_init(self) -> None:
        gen = BubbleChartGenerator()
        assert gen.chart_type == "bubblechart"

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = BubbleChartGenerator()
        data = [
            {"x": "A", "y": 10, "size": 5},
            {"x": "B", "y": 20, "size": 15},
        ]
        result = await gen.generate(
            data=data,
            x_column="x",
            y_column="y",
            size_column="size",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_with_labels(self) -> None:
        gen = BubbleChartGenerator()
        data = [
            {"x": "A", "y": 10, "size": 5, "name": "p1"},
        ]
        result = await gen.generate(
            data=data,
            x_column="x",
            y_column="y",
            size_column="size",
            label_column="name",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_missing_column(self) -> None:
        gen = BubbleChartGenerator()
        data = [{"x": "A", "y": 10}]
        result = await gen.generate(
            data=data,
            x_column="x",
            y_column="y",
            size_column="size",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_non_numeric_size(self) -> None:
        gen = BubbleChartGenerator()
        data = [{"x": "A", "y": "text", "size": "big"}]
        result = await gen.generate(
            data=data,
            x_column="x",
            y_column="y",
            size_column="size",
        )
        assert result.success is False
        assert "numeric" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_zero_max_size(self) -> None:
        gen = BubbleChartGenerator()
        data = [{"x": "A", "y": 1, "size": 0}]
        result = await gen.generate(
            data=data,
            x_column="x",
            y_column="y",
            size_column="size",
        )
        assert result.success is True


# -- Horizontal bar chart tests --


class TestHorizontalBarChartGenerator:
    def test_init(self) -> None:
        gen = HorizontalBarChartGenerator()
        assert gen.chart_type == "horizontal_barchart"

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = HorizontalBarChartGenerator()
        data = [
            {"cat": "A", "val": 10},
            {"cat": "B", "val": 20},
        ]
        result = await gen.generate(
            data=data,
            y_axis="cat",
            x_axes=["val"],
        )
        assert result.success is True
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_invalid_bar_mode(self) -> None:
        gen = HorizontalBarChartGenerator()
        data = [{"cat": "A", "val": 10}]
        result = await gen.generate(
            data=data,
            y_axis="cat",
            x_axes=["val"],
            bar_mode="wrong",
        )
        assert result.success is False
        assert "Invalid bar_mode" in (result.error or "")

    @pytest.mark.asyncio
    async def test_stack_mode(self) -> None:
        gen = HorizontalBarChartGenerator()
        data = [{"cat": "A", "v1": 10, "v2": 5}]
        result = await gen.generate(
            data=data,
            y_axis="cat",
            x_axes=["v1", "v2"],
            bar_mode="stack",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_percent_mode(self) -> None:
        gen = HorizontalBarChartGenerator()
        data = [{"cat": "A", "v1": 10, "v2": 5}]
        result = await gen.generate(
            data=data,
            y_axis="cat",
            x_axes=["v1", "v2"],
            bar_mode="percent",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_missing_column(self) -> None:
        gen = HorizontalBarChartGenerator()
        data = [{"cat": "A"}]
        result = await gen.generate(
            data=data,
            y_axis="cat",
            x_axes=["val"],
        )
        assert result.success is False

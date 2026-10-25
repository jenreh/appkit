"""Mantine charts components."""

from typing import Any, Literal

from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineComponentBase

MANTINE_CHARTS_LIBRARY = f"@mantine/charts@{MANTINE_VERSION}"
RECHARTS_LIBRARY = "recharts@3.8.1"
# es-toolkit is no longer declared here: reflex>=0.9.4 pins es-toolkit@1.46.1
# globally as a vite/recharts-compatible override, so an explicit lib_dependency
# entry would be redundant. recharts still needs the pin above.

MantineCurveType = Literal[
    "linear",
    "natural",
    "monotone",
    "step",
    "stepBefore",
    "stepAfter",
    "bumpX",
    "bumpY",
]


class MantineChartComponentBase(MantineComponentBase):
    """Base class for Mantine charts components."""

    library = MANTINE_CHARTS_LIBRARY
    lib_dependencies: list[str] = [
        RECHARTS_LIBRARY,
    ]

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';"""


class CategoricalChartBase(MantineChartComponentBase):
    """Base class for categorical charts (Area, Bar, Line)."""

    data: Var[list[dict[str, Any]]]
    data_key: Var[str]
    series: Var[list[dict[str, Any]]]

    # Appearance
    with_legend: Var[bool]
    legend_props: Var[dict[str, Any]]
    with_tooltip: Var[bool]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    # Axes
    grid_axis: Var[Literal["none", "x", "y", "xy"]]
    tick_line: Var[Literal["none", "x", "y", "xy"]]
    stroke_dasharray: Var[str | int]

    # Colors
    grid_color: Var[str]
    text_color: Var[str]

    # Axis Configuration
    with_x_axis: Var[bool]
    x_axis_props: Var[dict[str, Any]]
    x_axis_label: Var[str]

    with_y_axis: Var[bool]
    y_axis_props: Var[dict[str, Any]]
    y_axis_label: Var[str]
    unit: Var[str]

    # Additional Axis
    with_right_y_axis: Var[bool]
    right_y_axis_label: Var[str]
    right_y_axis_props: Var[dict[str, Any]]

    # Annotations
    reference_lines: Var[list[dict[str, Any]]]
    """Reference lines: [{x | y, color?, label?, labelPosition?}]."""

    reference_areas: Var[list[dict[str, Any]]]
    """Highlighted regions: [{x1?, x2?, y1?, y2?, color?, label?}]. Omit one
    pair to span the full opposite axis (Mantine 9.6+)."""

    reference_dots: Var[list[dict[str, Any]]]
    """Marked points: [{x, y, r?, color?, label?}], painted on top of the
    series (Mantine 9.6+)."""

    # Dimensions
    h: Var[str | int]
    w: Var[str | int]
    m: Var[str | int]  # Margin
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]
    p: Var[str | int]  # Padding
    pt: Var[str | int]
    pb: Var[str | int]
    pl: Var[str | int]
    pr: Var[str | int]
    px: Var[str | int]
    py: Var[str | int]


class AreaChart(CategoricalChartBase):
    """Mantine AreaChart component."""

    tag = "AreaChart"

    chart_type: Var[Literal["default", "stacked", "percent", "split", "stream"]] = None  # type: ignore
    """``"stream"`` renders a streamgraph with a floating baseline; the y axis
    is hidden by default for it (Mantine 9.6+)."""
    _rename_props = {
        "chartType": "type",
    }

    curve_type: Var[MantineCurveType]
    connect_nulls: Var[bool]
    fill_opacity: Var[float]
    split_colors: Var[list[str]]
    split_offset: Var[float]
    with_dots: Var[bool]
    with_gradient: Var[bool]
    dot_props: Var[dict[str, Any]]
    active_dot_props: Var[dict[str, Any]]
    stroke_width: Var[float]
    with_point_labels: Var[bool]

    with_brush: Var[bool]
    """Displays a brush (range selector) under the chart (Mantine 9.5+)."""

    brush_props: Var[dict[str, Any]]
    """Props passed down to the underlying recharts Brush (Mantine 9.5+)."""


class BarChart(CategoricalChartBase):
    """Mantine BarChart component."""

    tag = "BarChart"

    chart_type: Var[Literal["default", "stacked", "percent", "waterfall"]] = None  # type: ignore
    _rename_props = {
        "chartType": "type",
    }

    cursor_fill: Var[str]
    bar_label_color: Var[str]
    fill_opacity: Var[float]
    max_bar_width: Var[int]
    min_bar_size: Var[int]
    orientation: Var[Literal["horizontal", "vertical"]]
    with_bar_value_label: Var[bool]

    with_brush: Var[bool]
    """Displays a brush (range selector) under the chart (Mantine 9.5+)."""

    brush_props: Var[dict[str, Any]]
    """Props passed down to the underlying recharts Brush (Mantine 9.5+)."""


class LineChart(CategoricalChartBase):
    """Mantine LineChart component."""

    tag = "LineChart"

    curve_type: Var[MantineCurveType]
    connect_nulls: Var[bool]
    stroke_width: Var[float]
    with_dots: Var[bool]
    dot_props: Var[dict[str, Any]]
    active_dot_props: Var[dict[str, Any]]
    orientation: Var[Literal["horizontal", "vertical"]]

    with_brush: Var[bool]
    """Displays a brush (range selector) under the chart (Mantine 9.5+)."""

    brush_props: Var[dict[str, Any]]
    """Props passed down to the underlying recharts Brush (Mantine 9.5+)."""


class CompositeChart(CategoricalChartBase):
    """Mantine CompositeChart component."""

    tag = "CompositeChart"

    curve_type: Var[MantineCurveType]
    connect_nulls: Var[bool]
    max_bar_width: Var[int]
    min_bar_size: Var[int]
    stroke_width: Var[float]
    with_dots: Var[bool]
    dot_props: Var[dict[str, Any]]
    active_dot_props: Var[dict[str, Any]]

    with_brush: Var[bool]
    """Displays a brush (range selector) under the chart (Mantine 9.5+)."""

    brush_props: Var[dict[str, Any]]
    """Props passed down to the underlying recharts Brush (Mantine 9.5+)."""


class DonutChart(MantineChartComponentBase):
    """Mantine DonutChart component."""

    tag = "DonutChart"

    data: Var[list[dict[str, Any]]]
    size: Var[int]
    thickness: Var[int]
    padding_angle: Var[int]
    with_labels: Var[bool]
    with_labels_line: Var[bool]
    with_tooltip: Var[bool]
    tooltip_data_source: Var[Literal["all", "segment"]]
    chart_label: Var[str | int]
    start_angle: Var[int]
    end_angle: Var[int]
    stroke_width: Var[int]
    stroke_color: Var[str]
    label_color: Var[str]
    labels_type: Var[Literal["value", "percent", "name"]]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    pie_props: Var[dict[str, Any]]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    # Layout props
    h: Var[str | int]
    w: Var[str | int]
    m: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]


class PieChart(MantineChartComponentBase):
    """Mantine PieChart component."""

    tag = "PieChart"

    data: Var[list[dict[str, Any]]]
    size: Var[int]
    thickness: Var[int]
    with_labels: Var[bool]
    with_labels_line: Var[bool]
    padding_angle: Var[int]
    start_angle: Var[int]
    end_angle: Var[int]
    stroke_width: Var[int]
    stroke_color: Var[str]
    label_color: Var[str]
    with_tooltip: Var[bool]
    tooltip_data_source: Var[Literal["all", "segment"]]
    labels_type: Var[Literal["value", "percent", "name"]]
    chart_label: Var[str | int]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    pie_props: Var[dict[str, Any]]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    # Layout props
    h: Var[str | int]
    w: Var[str | int]
    m: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]


class RadarChart(MantineChartComponentBase):
    """Mantine RadarChart component."""

    tag = "RadarChart"

    data: Var[list[dict[str, Any]]]
    data_key: Var[str]
    series: Var[list[dict[str, Any]]]
    with_polar_grid: Var[bool]
    with_polar_angle_axis: Var[bool]
    with_polar_radius_axis: Var[bool]
    polar_radius_axis_props: Var[dict[str, Any]]
    polar_angle_axis_props: Var[dict[str, Any]]
    polar_grid_props: Var[dict[str, Any]]
    grid_color: Var[str]
    with_legend: Var[bool]
    legend_props: Var[dict[str, Any]]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    # Layout props
    h: Var[str | int]
    w: Var[str | int]
    m: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]


class ScatterChart(CategoricalChartBase):
    """Mantine ScatterChart component.

    Supports a second y axis (Mantine 9.5+) via the inherited
    ``with_right_y_axis`` / ``right_y_axis_label`` / ``right_y_axis_props``
    props; bind a series to it with ``yAxisId: "right"`` in the ``data``
    object.
    """

    tag = "ScatterChart"

    data: Var[list[dict[str, Any]]]
    # Note: Scatter uses object for dataKey {x: 'ug', y: 'pg'}
    data_key: Var[dict[str, Any]]
    labels: Var[dict[str, Any]]  # {x: 'label', y: 'label'}


class BubbleChart(MantineChartComponentBase):
    """Mantine BubbleChart component."""

    tag = "BubbleChart"

    data: Var[list[dict[str, Any]]]
    data_key: Var[dict[str, Any]]  # {x: 'cx', y: 'cy', z: 'cz'}
    label: Var[str]  # Label for z axis in tooltip
    range: Var[list[int]]  # Range for bubble sizes [min, max]
    color: Var[str]  # Single color for all bubbles
    grid_color: Var[str]
    text_color: Var[str]
    with_legend: Var[bool]
    legend_props: Var[dict[str, Any]]
    with_tooltip: Var[bool]
    tooltip_props: Var[dict[str, Any]]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    # Layout props
    h: Var[str | int]
    w: Var[str | int]


class Sparkline(MantineChartComponentBase):
    """Mantine Sparkline component."""

    tag = "Sparkline"

    data: Var[list[int | float | dict]]
    w: Var[int | str]
    h: Var[int | str]
    color: Var[str]
    fill_opacity: Var[float]
    curve_type: Var[MantineCurveType]
    stroke_width: Var[float]
    # {positive: 'color', negative: 'color', neutral: 'color'}
    trend_colors: Var[dict[str, Any]]
    with_gradient: Var[bool]


class FunnelChart(MantineChartComponentBase):
    """Mantine FunnelChart component."""

    tag = "FunnelChart"

    data: Var[list[dict[str, Any]]]
    width: Var[int]
    height: Var[int]
    size: Var[int]
    stroke_width: Var[int]
    stroke_color: Var[str]
    label_color: Var[str]
    with_tooltip: Var[bool]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    with_labels: Var[bool]

    accessibility_layer: Var[bool]
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""


class Heatmap(MantineChartComponentBase):
    """Mantine Heatmap component."""

    tag = "Heatmap"

    data: Var[list[dict[str, Any]] | dict[str, Any]]

    with_legend: Var[bool] = None
    """Displays a color legend below the chart (Mantine 9.1+)."""

    legend_labels: Var[list[str]] = None
    """Labels for the color legend (default: ['Less', 'More'])."""

    month_labels_position: Var[Literal["top", "bottom"]] = None
    """Position of month labels, 'top' by default (Mantine 9.5+)."""

    start_date: Var[str]
    end_date: Var[str]
    min: Var[float]
    max: Var[float]
    color_scale: Var[list[str]]  # Function not supported yet via generic prop
    value_label: Var[str]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    enable_labels: Var[bool]

    w: Var[str | int]
    h: Var[str | int]


class Treemap(MantineChartComponentBase):
    """Mantine Treemap component."""

    tag = "Treemap"

    data: Var[list[dict[str, Any]]]
    """Hierarchical data to display."""

    w: Var[str | int]
    h: Var[str | int]


class RadialBarChart(MantineChartComponentBase):
    """Mantine RadialBarChart component.

    https://mantine.dev/charts/radial-bar-chart/
    """

    tag = "RadialBarChart"

    data: Var[list[dict[str, Any]]] = None
    data_key: Var[str] = None
    bar_size: Var[int] = None
    empty_background_color: Var[str] = None
    end_angle: Var[int] = None
    start_angle: Var[int] = None
    with_background: Var[bool] = None
    with_labels: Var[bool] = None
    with_legend: Var[bool] = None
    with_tooltip: Var[bool] = None
    legend_props: Var[dict] = None
    tooltip_props: Var[dict] = None

    accessibility_layer: Var[bool] = None
    """Keyboard navigation via the recharts accessibility layer,
    True by default (Mantine 9.5+)."""

    h: Var[str | int] = None
    w: Var[str | int] = None


class BarsList(MantineChartComponentBase):
    """Mantine BarsList component — simple horizontal bars list.

    https://mantine.dev/charts/bars-list/
    """

    tag = "BarsList"

    data: Var[list[dict[str, Any]]] = None
    bar_color: Var[str] = None
    bar_gap: Var[str | int] = None
    bar_height: Var[str | int] = None
    bar_text_color: Var[str] = None
    bars_label: Var[str] = None
    min_bar_size: Var[str | int] = None
    value_label: Var[str] = None
    auto_contrast: Var[bool] = None


class SankeyChart(MantineChartComponentBase):
    """Mantine SankeyChart component — Sankey flow diagram.

    https://mantine.dev/charts/sankey-chart/
    """

    tag = "SankeyChart"

    data: Var[dict[str, Any]] = None
    """SankeyChartData: {nodes: [{name: str}],
    links: [{source: int, target: int, value: int}]}"""

    height: Var[int] = None
    colors: Var[list[str]] = None
    iterations: Var[int] = None
    link_color: Var[str] = None
    link_curvature: Var[float] = None
    link_opacity: Var[float] = None
    node_color: Var[str] = None
    node_padding: Var[int] = None
    node_width: Var[int] = None
    text_color: Var[str] = None
    with_tooltip: Var[bool] = None
    tooltip_animation_duration: Var[int] = None
    tooltip_props: Var[dict] = None

    w: Var[str | int] = None
    h: Var[str | int] = None


class SunburstChart(MantineChartComponentBase):
    """Mantine SunburstChart component — hierarchical data as concentric
    rings, similar to a treemap plotted in polar coordinates.

    Added in Mantine 9.5.

    https://mantine.dev/charts/sunburst-chart/
    """

    tag = "SunburstChart"

    data: Var[list[dict[str, Any]]] = None
    """Hierarchical data: [{name, color, value | children: [...]}].
    Leaf nodes need `value`; parent nodes have a `children` list."""

    data_key: Var[str] = None
    end_angle: Var[int] = None
    gap: Var[int] = None
    inner_radius: Var[int] = None
    size: Var[int] = None
    start_angle: Var[int] = None
    stroke_color: Var[str] = None
    sunburst_chart_props: Var[dict] = None
    tooltip_animation_duration: Var[int] = None
    tooltip_props: Var[dict] = None
    with_labels: Var[bool] = None
    with_tooltip: Var[bool] = None

    w: Var[str | int] = None
    h: Var[str | int] = None


class BulletChart(MantineChartComponentBase):
    """Mantine BulletChart component — compact KPI chart displaying a value
    against a target and qualitative ranges.

    Added in Mantine 9.5.

    https://mantine.dev/charts/bullet-chart/
    """

    tag = "BulletChart"

    value: Var[int | float] = None
    """Current value displayed as the main bar (required)."""

    ranges: Var[list[dict[str, Any]]] = None
    """Qualitative range bands: [{value, color, label?}] (required)."""

    target: Var[int | float] = None
    label: Var[str] = None
    orientation: Var[Literal["horizontal", "vertical"]] = None
    size: Var[str | int] = None
    bar_size: Var[str | int] = None
    bar_color: Var[str] = None
    target_color: Var[str] = None
    target_ratio: Var[float] = None
    target_size: Var[str | int] = None
    with_tooltip: Var[bool] = None

    w: Var[str | int] = None
    h: Var[str | int] = None


class ChartBrush(MantineChartComponentBase):
    """Mantine ChartBrush component — themed recharts Brush.

    Render as a child of AreaChart, BarChart, LineChart or CompositeChart
    for full control over the brush instead of `with_brush`.

    Added in Mantine 9.5.

    https://mantine.dev/charts/area-chart/
    """

    tag = "ChartBrush"

    data_key: Var[str] = None
    start_index: Var[int] = None
    end_index: Var[int] = None
    height: Var[int] = None


class GaugeChart(MantineChartComponentBase):
    """Mantine GaugeChart — radial gauge for KPI and status display.

    Added in Mantine 9.6.

    https://mantine.dev/charts/gauge-chart/
    """

    tag = "GaugeChart"

    value: Var[int | float] = None
    """Current value (required)."""

    min: Var[int | float] = None
    max: Var[int | float] = None
    target: Var[int | float] = None
    """Value marked with a target needle."""

    sections: Var[list[dict[str, Any]]] = None
    """Threshold sections: [{value, color}]."""

    thickness: Var[int] = None
    size: Var[int] = None
    start_angle: Var[int] = None
    end_angle: Var[int] = None
    label: Var[Any] = None
    value_formatter: Var[Any] = None
    track_color: Var[str] = None
    filled_color: Var[str] = None
    target_color: Var[str] = None
    target_size: Var[int] = None
    round_caps: Var[bool] = None


class WaffleChart(MantineChartComponentBase):
    """Mantine WaffleChart — part-to-whole grid of colored cells.

    Added in Mantine 9.6.

    https://mantine.dev/charts/waffle-chart/
    """

    tag = "WaffleChart"

    data: Var[list[dict[str, Any]]] = None
    """Cells: [{name, value, color}]."""

    rows: Var[int] = None
    columns: Var[int] = None
    total: Var[int | float] = None
    gap: Var[int] = None
    cell_radius: Var[int] = None
    empty_color: Var[str] = None
    with_tooltip: Var[bool] = None
    get_tooltip_label: Var[Any] = None
    with_legend: Var[bool] = None
    legend_position: Var[Literal["top", "bottom", "left", "right"]] = None
    fill_direction: Var[
        Literal["left-to-right", "right-to-left", "top-to-bottom", "bottom-to-top"]
    ] = None
    size: Var[int] = None


class MatrixChart(MantineChartComponentBase):
    """Mantine MatrixChart — x/y heatmap with categorical axes.

    Added in Mantine 9.6.

    https://mantine.dev/charts/matrix-chart/
    """

    tag = "MatrixChart"

    data: Var[list[dict[str, Any]]] = None
    """Cells: [{x, y, value}], ``value`` may be ``None``."""

    x_labels: Var[list[str]] = None
    y_labels: Var[list[str]] = None
    domain: Var[list[int | float]] = None
    colors: Var[list[str]] = None
    cell_size: Var[int] = None
    gap: Var[int] = None
    cell_radius: Var[int] = None
    with_tooltip: Var[bool] = None
    get_tooltip_label: Var[Any] = None
    tooltip_props: Var[dict[str, Any]] = None
    get_cell_props: Var[Any] = None
    y_labels_width: Var[int] = None
    x_labels_height: Var[int] = None
    x_labels_position: Var[Literal["top", "bottom"]] = None
    font_size: Var[int] = None
    empty_color: Var[str] = None
    with_legend: Var[bool] = None
    legend_labels: Var[list[str]] = None
    with_x_labels: Var[bool] = None
    with_y_labels: Var[bool] = None
    x_labels_rotation: Var[int] = None


class CandlestickChart(MantineChartComponentBase):
    """Mantine CandlestickChart — financial OHLC chart.

    Added in Mantine 9.6.

    https://mantine.dev/charts/candlestick-chart/
    """

    tag = "CandlestickChart"

    data: Var[list[dict[str, Any]]] = None
    data_key: Var[str] = None
    data_keys: Var[dict[str, str]] = None
    """Keys of the OHLC values: {open, high, low, close}."""

    labels: Var[dict[str, str]] = None
    """Tooltip labels: {open, high, low, close}."""

    up_color: Var[str] = None
    down_color: Var[str] = None
    max_candle_width: Var[int] = None
    candle_stroke_width: Var[int] = None
    composed_chart_props: Var[dict[str, Any]] = None

    with_x_axis: Var[bool] = None
    with_y_axis: Var[bool] = None
    x_axis_props: Var[dict[str, Any]] = None
    y_axis_props: Var[dict[str, Any]] = None
    x_axis_label: Var[str] = None
    y_axis_label: Var[str] = None
    grid_props: Var[dict[str, Any]] = None
    grid_axis: Var[Literal["none", "x", "y", "xy"]] = None
    tick_line: Var[Literal["none", "x", "y", "xy"]] = None
    stroke_dasharray: Var[str | int] = None
    grid_color: Var[str] = None
    text_color: Var[str] = None
    unit: Var[str] = None
    value_formatter: Var[Any] = None
    with_tooltip: Var[bool] = None
    tooltip_animation_duration: Var[int] = None
    tooltip_props: Var[dict[str, Any]] = None
    reference_lines: Var[list[dict[str, Any]]] = None
    reference_areas: Var[list[dict[str, Any]]] = None
    reference_dots: Var[list[dict[str, Any]]] = None
    accessibility_layer: Var[bool] = None

    w: Var[str | int] = None
    h: Var[str | int] = None


area_chart = AreaChart.create
bar_chart = BarChart.create
line_chart = LineChart.create
composite_chart = CompositeChart.create
donut_chart = DonutChart.create
pie_chart = PieChart.create
radar_chart = RadarChart.create
scatter_chart = ScatterChart.create
bubble_chart = BubbleChart.create
sparkline = Sparkline.create
funnel_chart = FunnelChart.create
heatmap = Heatmap.create
treemap = Treemap.create
radial_bar_chart = RadialBarChart.create
bars_list = BarsList.create
sankey_chart = SankeyChart.create
sunburst_chart = SunburstChart.create
bullet_chart = BulletChart.create
chart_brush = ChartBrush.create
gauge_chart = GaugeChart.create
waffle_chart = WaffleChart.create
matrix_chart = MatrixChart.create
candlestick_chart = CandlestickChart.create

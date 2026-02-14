"""Mantine charts components."""

from typing import Any, Literal

from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase

MANTINE_CHARTS_LIBRARY = "@mantine/charts@8.3.10"
RECHARTS_LIBRARY = "recharts@^2.13.3"

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
    lib_dependencies: list[str] = [RECHARTS_LIBRARY]

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

    chart_type: Var[Literal["default", "stacked", "percent", "split"]] = None  # type: ignore
    _rename_props = {"chartType": "type"}

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


class BarChart(CategoricalChartBase):
    """Mantine BarChart component."""

    tag = "BarChart"

    chart_type: Var[Literal["default", "stacked", "percent", "waterfall"]] = None  # type: ignore
    _rename_props = {"chartType": "type"}

    cursor_fill: Var[str]
    bar_label_color: Var[str]
    fill_opacity: Var[float]
    max_bar_width: Var[int]
    min_bar_size: Var[int]
    orientation: Var[Literal["horizontal", "vertical"]]
    with_bar_value_label: Var[bool]


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
    labels_type: Var[Literal["value", "percent"]]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    pie_props: Var[dict[str, Any]]

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
    labels_type: Var[Literal["value", "percent"]]
    chart_label: Var[str | int]
    tooltip_animation_duration: Var[int]
    tooltip_props: Var[dict[str, Any]]
    pie_props: Var[dict[str, Any]]

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
    """Mantine ScatterChart component."""

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


class Heatmap(MantineChartComponentBase):
    """Mantine Heatmap component."""

    tag = "Heatmap"

    data: Var[list[dict[str, Any]] | dict[str, Any]]

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

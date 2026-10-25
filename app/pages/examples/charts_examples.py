"""Charts example page."""

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

# Sample Data
DATA = [
    {"name": "Jan", "uv": 4000, "pv": 2400, "amt": 2400},
    {"name": "Feb", "uv": 3000, "pv": 1398, "amt": 2210},
    {"name": "Mar", "uv": 2000, "pv": 9800, "amt": 2290},
    {"name": "Apr", "uv": 2780, "pv": 3908, "amt": 2000},
    {"name": "May", "uv": 1890, "pv": 4800, "amt": 2181},
    {"name": "Jun", "uv": 2390, "pv": 3800, "amt": 2500},
    {"name": "Jul", "uv": 3490, "pv": 4300, "amt": 2100},
]

DONUT_DATA = [
    {"name": "USA", "value": 400, "color": "indigo.6"},
    {"name": "India", "value": 300, "color": "yellow.6"},
    {"name": "Japan", "value": 100, "color": "teal.6"},
    {"name": "Other", "value": 200, "color": "gray.6"},
]

SPARKLINE_DATA = [10, 20, 40, 20, 40, 10, 50, 20, 90, 30]

RADAR_DATA = [
    {"product": "Apples", "sales": 120},
    {"product": "Oranges", "sales": 98},
    {"product": "Tomatoes", "sales": 86},
    {"product": "Grapes", "sales": 99},
    {"product": "Bananas", "sales": 85},
    {"product": "Lemons", "sales": 65},
]

SCATTER_DATA = [
    {
        "color": "blue.5",
        "name": "Group 1",
        "data": [
            {"x": 100, "y": 200},
            {"x": 120, "y": 100},
            {"x": 170, "y": 300},
            {"x": 140, "y": 250},
            {"x": 150, "y": 400},
            {"x": 110, "y": 280},
        ],
    },
    {
        "color": "green.5",
        "name": "Group 2",
        "data": [
            {"x": 200, "y": 260},
            {"x": 220, "y": 280},
            {"x": 240, "y": 290},
            {"x": 280, "y": 180},
        ],
    },
]

BUBBLE_DATA = [
    {"hour": 0, "index": 1, "value": 170},
    {"hour": 1, "index": 1, "value": 180},
    {"hour": 2, "index": 1, "value": 150},
    {"hour": 3, "index": 1, "value": 120},
    {"hour": 4, "index": 1, "value": 200},
    {"hour": 5, "index": 1, "value": 300},
    {"hour": 6, "index": 1, "value": 400},
    {"hour": 7, "index": 1, "value": 200},
    {"hour": 8, "index": 1, "value": 100},
    {"hour": 9, "index": 1, "value": 150},
    {"hour": 10, "index": 1, "value": 205},
    {"hour": 11, "index": 1, "value": 310},
]

FUNNEL_DATA = [
    {"name": "Cluster", "value": 1000, "color": "indigo.6"},
    {"name": "Zone", "value": 850, "color": "blue.6"},
    {"name": "Region", "value": 400, "color": "cyan.6"},
    {"name": "Block", "value": 120, "color": "teal.6"},
]


TREEMAP_DATA = [
    {
        "name": "Frontend",
        "color": "blue.8",
        "children": [
            {"name": "React", "value": 400},
            {"name": "Vue", "value": 200},
            {"name": "Angular", "value": 150},
        ],
    },
    {
        "name": "Backend",
        "color": "teal.8",
        "children": [
            {"name": "Node", "value": 300},
            {"name": "Python", "value": 250},
            {"name": "Go", "value": 100},
        ],
    },
]

HEATMAP_DATA = {
    "2024-01-02": 2,
    "2024-01-03": 5,
    "2024-01-04": 10,
    "2024-01-05": 15,
    "2024-01-07": 8,
    "2024-01-08": 3,
    "2024-01-09": 12,
    "2024-01-10": 18,
    "2024-01-11": 22,
    "2024-01-12": 5,
}

RADIAL_BAR_DATA = [
    {"name": "Planning", "value": 84, "color": "blue.6"},
    {"name": "Build", "value": 72, "color": "teal.6"},
    {"name": "Review", "value": 58, "color": "orange.6"},
]

BARS_LIST_DATA = [
    {"name": "Python", "value": 92, "color": "blue.6"},
    {"name": "TypeScript", "value": 76, "color": "grape.6"},
    {"name": "SQL", "value": 54, "color": "teal.6"},
]

SANKEY_DATA = {
    "nodes": [
        {"name": "Visits"},
        {"name": "Docs"},
        {"name": "Examples"},
        {"name": "Install"},
    ],
    "links": [
        {"source": 0, "target": 1, "value": 12},
        {"source": 0, "target": 2, "value": 8},
        {"source": 1, "target": 3, "value": 6},
        {"source": 2, "target": 3, "value": 5},
    ],
}

SUNBURST_DATA = [
    {
        "name": "Frontend",
        "color": "blue.6",
        "children": [
            {"name": "React", "value": 400},
            {"name": "Vue", "value": 200},
            {"name": "Angular", "value": 150},
        ],
    },
    {
        "name": "Backend",
        "color": "teal.6",
        "children": [
            {"name": "Node", "value": 300},
            {"name": "Python", "value": 250},
        ],
    },
]

BULLET_RANGES = [
    {"value": 150, "color": "red.8", "label": "Low"},
    {"value": 225, "color": "yellow.8", "label": "Medium"},
    {"value": 300, "color": "teal.8", "label": "High"},
]

WAFFLE_DATA = [
    {"name": "Chrome", "value": 65, "color": "blue"},
    {"name": "Safari", "value": 19, "color": "teal"},
    {"name": "Firefox", "value": 10, "color": "orange"},
    {"name": "Other", "value": 6, "color": "gray"},
]

GAUGE_SECTIONS = [
    {"value": 40, "color": "red.6"},
    {"value": 70, "color": "yellow.6"},
    {"value": 100, "color": "teal.6"},
]

MATRIX_PEOPLE = ["James", "Mary", "Robert", "Linda", "Michael"]
MATRIX_DATA = [
    {
        "x": str(day),
        "y": person,
        "value": None if (day * (row + 3)) % 7 == 0 else (day * (row + 5)) % 11,
    }
    for row, person in enumerate(MATRIX_PEOPLE)
    for day in range(1, 11)
]

CANDLESTICK_DATA = [
    {"date": "Mar 01", "open": 136, "high": 142, "low": 133, "close": 140},
    {"date": "Mar 02", "open": 140, "high": 145, "low": 138, "close": 139},
    {"date": "Mar 03", "open": 139, "high": 141, "low": 129, "close": 131},
    {"date": "Mar 04", "open": 131, "high": 134, "low": 124, "close": 125},
    {"date": "Mar 05", "open": 125, "high": 133, "low": 124, "close": 132},
    {"date": "Mar 06", "open": 132, "high": 138, "low": 131, "close": 137},
    {"date": "Mar 07", "open": 137, "high": 137, "low": 128, "close": 129},
    {"date": "Mar 08", "open": 129, "high": 135, "low": 127, "close": 134},
    {"date": "Mar 09", "open": 134, "high": 148, "low": 133, "close": 146},
    {"date": "Mar 10", "open": 146, "high": 152, "low": 144, "close": 151},
    {"date": "Mar 11", "open": 151, "high": 154, "low": 143, "close": 145},
    {"date": "Mar 12", "open": 145, "high": 149, "low": 142, "close": 148},
    {"date": "Mar 13", "open": 148, "high": 156, "low": 147, "close": 155},
    {"date": "Mar 14", "open": 155, "high": 158, "low": 150, "close": 152},
]

STREAM_DATA = [
    {"month": "Jan", "Apples": 220, "Oranges": 140, "Tomatoes": 90, "Grapes": 60},
    {"month": "Feb", "Apples": 260, "Oranges": 180, "Tomatoes": 120, "Grapes": 90},
    {"month": "Mar", "Apples": 300, "Oranges": 240, "Tomatoes": 180, "Grapes": 140},
    {"month": "Apr", "Apples": 340, "Oranges": 320, "Tomatoes": 260, "Grapes": 200},
    {"month": "May", "Apples": 380, "Oranges": 420, "Tomatoes": 360, "Grapes": 280},
    {"month": "Jun", "Apples": 420, "Oranges": 520, "Tomatoes": 460, "Grapes": 360},
    {"month": "Jul", "Apples": 400, "Oranges": 560, "Tomatoes": 520, "Grapes": 420},
    {"month": "Aug", "Apples": 360, "Oranges": 520, "Tomatoes": 560, "Grapes": 460},
    {"month": "Sep", "Apples": 300, "Oranges": 440, "Tomatoes": 520, "Grapes": 420},
    {"month": "Oct", "Apples": 260, "Oranges": 340, "Tomatoes": 440, "Grapes": 360},
]


@navbar_layout(
    route="/examples/charts",
    title="Charts Examples",
    navbar=app_navbar(),
    with_header=False,
)
def charts_examples() -> rx.Component:
    """Charts example page."""
    return mn.container(
        mn.stack(
            mn.title("Charts", order=1),
            mn.text(
                "Mantine Charts wrappers based on Recharts.",
                size="md",
                c="dimmed",
            ),
            mn.simple_grid(
                # Area Chart
                example_box(
                    "Area Chart",
                    mn.area_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "indigo.6"},
                            {"name": "pv", "color": "teal.6"},
                        ],
                        curve_type="monotone",
                        with_legend=True,
                        with_x_axis=True,
                        with_y_axis=True,
                    ),
                ),
                # Bar Chart
                example_box(
                    "Bar Chart",
                    mn.bar_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "blue.6"},
                            {"name": "pv", "color": "gray.6"},
                        ],
                        tick_line="y",
                        with_legend=True,
                        with_x_axis=True,
                        with_y_axis=True,
                    ),
                ),
                # Line Chart
                example_box(
                    "Line Chart",
                    mn.line_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "pink.6"},
                            {"name": "pv", "color": "cyan.6"},
                        ],
                        curve_type="linear",
                        with_legend=True,
                        with_dots=True,
                    ),
                ),
                # Donut Chart
                example_box(
                    "Donut Chart",
                    mn.center(
                        mn.donut_chart(
                            data=DONUT_DATA,
                            with_labels_line=True,
                            with_labels=True,
                            size=200,
                            thickness=20,
                        ),
                    ),
                ),
                # Pie Chart
                example_box(
                    "Pie Chart",
                    mn.center(
                        mn.pie_chart(
                            data=DONUT_DATA,
                            with_labels_line=True,
                            with_labels=True,
                            size=200,
                        ),
                    ),
                ),
                # Radar Chart
                example_box(
                    "Radar Chart",
                    mn.radar_chart(
                        h=300,
                        data=RADAR_DATA,
                        data_key="product",
                        series=[
                            {
                                "name": "sales",
                                "color": "blue.4",
                            }
                        ],
                        with_polar_grid=True,
                        with_polar_angle_axis=True,
                    ),
                ),
                # Sparkline
                example_box(
                    "Sparkline",
                    mn.stack(
                        mn.sparkline(
                            w="100%",
                            h=60,
                            data=SPARKLINE_DATA,
                            curve_type="linear",
                        ),
                        mn.sparkline(
                            w="100%",
                            h=60,
                            data=SPARKLINE_DATA,
                            curve_type="monotone",
                            color="red.5",
                            fill_opacity=0.2,
                            trend_colors={
                                "positive": "teal.6",
                                "negative": "red.6",
                                "neutral": "gray.5",
                            },
                        ),
                    ),
                ),
                # Composite Chart
                example_box(
                    "Composite Chart",
                    mn.composite_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "indigo.6", "type": "bar"},
                            {"name": "pv", "color": "teal.6", "type": "area"},
                            {"name": "amt", "color": "red.6", "type": "line"},
                        ],
                        curve_type="monotone",
                        with_legend=True,
                    ),
                ),
                # Scatter Chart
                example_box(
                    "Scatter Chart",
                    mn.scatter_chart(
                        h=300,
                        data=SCATTER_DATA,
                        data_key={"x": "x", "y": "y"},
                        with_legend=True,
                    ),
                ),
                # Bubble Chart
                example_box(
                    "Bubble Chart",
                    mn.bubble_chart(
                        h=300,
                        data=BUBBLE_DATA,
                        range=[16, 225],
                        label="Sales/Hour",
                        color="lime.6",
                        data_key={"x": "hour", "y": "index", "z": "value"},
                    ),
                ),
                # Funnel Chart
                example_box(
                    "Funnel Chart",
                    mn.center(
                        mn.funnel_chart(
                            data=FUNNEL_DATA,
                            width=300,
                            height=300,
                        ),
                    ),
                ),
                # Treemap
                example_box(
                    "Treemap",
                    mn.treemap(
                        h=300,
                        data=TREEMAP_DATA,
                    ),
                ),
                # Heatmap
                example_box(
                    "Heatmap",
                    mn.heatmap(
                        h=300,
                        data=HEATMAP_DATA,
                        start_date="2024-01-01",
                        end_date="2024-03-01",
                    ),
                ),
                # Radial Bar Chart
                example_box(
                    "Radial Bar Chart",
                    mn.radial_bar_chart(
                        h=300,
                        data=RADIAL_BAR_DATA,
                        data_key="value",
                        with_labels=True,
                        with_legend=True,
                    ),
                ),
                # Bars List
                example_box(
                    "Bars List",
                    mn.bars_list(
                        data=BARS_LIST_DATA,
                        bar_height=24,
                        bar_gap="sm",
                        value_label="Usage",
                    ),
                ),
                # Sankey Chart
                example_box(
                    "Sankey Chart",
                    mn.sankey_chart(
                        height=300,
                        data=SANKEY_DATA,
                        node_width=14,
                        node_padding=18,
                        with_tooltip=True,
                    ),
                ),
                # Sunburst Chart
                example_box(
                    "Sunburst Chart",
                    mn.center(
                        mn.sunburst_chart(
                            data=SUNBURST_DATA,
                            size=260,
                            with_labels=True,
                            with_tooltip=True,
                        ),
                    ),
                ),
                # Bullet Chart
                example_box(
                    "Bullet Chart",
                    mn.bullet_chart(
                        value=230,
                        target=250,
                        ranges=BULLET_RANGES,
                        label="Revenue",
                        bar_color="blue.6",
                        with_tooltip=True,
                    ),
                ),
                # Line Chart with Brush
                example_box(
                    "Line Chart with Brush",
                    mn.line_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "indigo.6"},
                            {"name": "pv", "color": "teal.6"},
                        ],
                        curve_type="monotone",
                        with_brush=True,
                        brush_props={"startIndex": 1, "endIndex": 5},
                    ),
                ),
                # Area Chart with ChartBrush child
                example_box(
                    "Area Chart with ChartBrush",
                    mn.area_chart(
                        mn.chart_brush(
                            data_key="name",
                            height=24,
                            start_index=0,
                            end_index=4,
                        ),
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[{"name": "uv", "color": "grape.6"}],
                        curve_type="monotone",
                        with_gradient=True,
                    ),
                ),
                # Gauge Chart (Mantine 9.6)
                example_box(
                    "Gauge Chart",
                    mn.center(
                        mn.gauge_chart(
                            value=72,
                            target=85,
                            sections=GAUGE_SECTIONS,
                            size=220,
                            thickness=14,
                            label="72% uptime",
                            round_caps=True,
                        ),
                    ),
                ),
                # Waffle Chart (Mantine 9.6)
                example_box(
                    "Waffle Chart",
                    mn.center(
                        mn.waffle_chart(
                            data=WAFFLE_DATA,
                            with_tooltip=True,
                            with_legend=True,
                            legend_position="right",
                        ),
                    ),
                ),
                # Matrix Chart (Mantine 9.6)
                example_box(
                    "Matrix Chart",
                    mn.matrix_chart(
                        data=MATRIX_DATA,
                        y_labels=MATRIX_PEOPLE,
                        with_y_labels=True,
                        with_x_labels=True,
                        with_tooltip=True,
                        with_legend=True,
                        cell_size=14,
                        y_labels_width=56,
                    ),
                ),
                # Candlestick Chart (Mantine 9.6)
                example_box(
                    "Candlestick Chart",
                    mn.candlestick_chart(
                        h=300,
                        data=CANDLESTICK_DATA,
                        data_key="date",
                        grid_axis="x",
                        tick_line="y",
                        with_tooltip=True,
                        reference_lines=[
                            {"y": 140, "label": "Support", "color": "gray.6"}
                        ],
                    ),
                ),
                # Reference areas and dots (Mantine 9.6)
                example_box(
                    "Reference Areas & Dots",
                    mn.area_chart(
                        h=300,
                        data=DATA,
                        data_key="name",
                        series=[
                            {"name": "uv", "color": "indigo.6"},
                            {"name": "pv", "color": "teal.6"},
                        ],
                        curve_type="monotone",
                        reference_areas=[
                            {
                                "x1": "Mar",
                                "x2": "Apr",
                                "color": "red.6",
                                "label": "Promo",
                            }
                        ],
                        reference_dots=[
                            {"x": "Mar", "y": 9800, "color": "red.6", "label": "Peak"}
                        ],
                    ),
                ),
                # Streamgraph (Mantine 9.6)
                example_box(
                    "Area Chart Streamgraph",
                    mn.area_chart(
                        h=300,
                        data=STREAM_DATA,
                        data_key="month",
                        chart_type="stream",
                        curve_type="monotone",
                        series=[
                            {"name": "Apples", "color": "indigo.6"},
                            {"name": "Oranges", "color": "blue.6"},
                            {"name": "Tomatoes", "color": "teal.6"},
                            {"name": "Grapes", "color": "grape.6"},
                        ],
                    ),
                ),
                cols=2,
                spacing="lg",
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )

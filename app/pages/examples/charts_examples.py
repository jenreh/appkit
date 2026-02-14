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


@navbar_layout(
    route="/charts",
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

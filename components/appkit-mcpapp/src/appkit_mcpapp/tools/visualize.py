"""MCP tool: generate_barchart.

Accepts tabular data and generates an interactive barchart
visualization, returning an iframe-loadable HTML resource.
"""

import logging

import plotly.graph_objects as go

from appkit_mcpapp.models.schemas import VisualizationResult

logger = logging.getLogger(__name__)

VALID_BAR_MODES = ("group", "stack", "percent")

SERIES_COLORS = [
    "#228be6",
    "#fa5252",
    "#40c057",
    "#fab005",
    "#7950f2",
    "#fd7e14",
]

_PLOTLY_CONFIG = {
    "displayModeBar": True,
    "scrollZoom": True,  # enables scroll-wheel zoom
    "modeBarButtonsToAdd": [
        "v1hovermode",  # adds compare hover toggle button
        "toggleSpikeLines",  # adds spike line toggle button
    ],
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",  # remove less useful selection tools
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "my_chart",
        "width": 1200,
        "height": 600,
        "scale": 2,  # retina quality
    },
}


async def generate_barchart(
    data: list[dict[str, object]],
    x_axis: str,
    y_axes: list[str],
    chart_title: str = "User Analytics",
    bar_mode: str = "group",
) -> VisualizationResult:
    """Generate a barchart visualization from tabular data.

    Returns an HTML iframe tag pointing to the Reflex chart rendering route.

    Args:
        data: List of row dicts from the query tool.
        x_axis: Column name to use as X-axis.
        y_axes: Column names to use as Y-axis data series.
        chart_title: Title for the chart.
        bar_mode: Display mode — ``"group"`` (side by side),
            ``"stack"``, or ``"percent"`` (stacked to 100 %).

    Returns:
        VisualizationResult with iframe HTML and preview URL.
    """
    if not data:
        return VisualizationResult(
            success=False,
            error="No data provided for visualization",
        )

    if bar_mode not in VALID_BAR_MODES:
        return VisualizationResult(
            success=False,
            error=(
                "Invalid bar_mode '{}'. Must be one of: {}".format(
                    bar_mode, ", ".join(VALID_BAR_MODES)
                )
            ),
        )

    # Validate that x_axis and y_axes columns exist in data
    first_row = data[0]
    available_columns = list(first_row.keys())

    if x_axis not in first_row:
        return VisualizationResult(
            success=False,
            error=(
                f"Column '{x_axis}' not found in data. Available: {available_columns}"
            ),
        )

    for col in y_axes:
        if col not in first_row:
            return VisualizationResult(
                success=False,
                error=(
                    f"Column '{col}' not found in data. Available: {available_columns}"
                ),
            )

    # Build embeddable HTML fragment (no full page, no bundled Plotly.js)
    html = _build_chart_html(data, x_axis, y_axes, chart_title, bar_mode)

    logger.info(
        "Created barchart visualization: rows=%d",
        len(data),
    )

    return VisualizationResult(
        success=True,
        html=html,
    )


def _build_chart_html(
    data: list[dict[str, object]],
    x_axis: str,
    y_axes: list[str],
    title: str,
    bar_mode: str = "group",
) -> str:
    """Build an embeddable Plotly chart HTML fragment.

    Uses ``fig.to_html(full_html=False)`` to produce a ``<div>``
    with an inline script calling ``Plotly.newPlot()``.  The host
    page must load ``plotly.js`` separately (e.g. via CDN).

    Args:
        data: Chart data rows.
        x_axis: X-axis column name.
        y_axes: Y-axis column names (one trace per column).
        title: Chart title.
        bar_mode: Display mode (``"group"``, ``"stack"``,
            or ``"percent"``).

    Returns:
        HTML ``<div>`` fragment string.
    """
    x_values = [str(row.get(x_axis, "")) for row in data]

    traces = []
    for idx, col in enumerate(y_axes):
        y_values = [row.get(col, 0) for row in data]
        color = SERIES_COLORS[idx % len(SERIES_COLORS)]
        traces.append(
            go.Bar(
                x=x_values,
                y=y_values,
                name=col,
                marker_color=color,
            )
        )

    fig = go.Figure(data=traces)

    # Map user-facing bar_mode to Plotly layout params
    plotly_barmode = "stack" if bar_mode == "percent" else bar_mode
    barnorm = "percent" if bar_mode == "percent" else ""

    fig.update_layout(
        title_text=title,
        xaxis_title=x_axis,
        hovermode="x unified",  # shows all traces at the hovered x position
        barmode=plotly_barmode,
        barnorm=barnorm if barnorm else None,
        width=816,
        height=480,
        margin={"t": 50, "r": 60, "b": 80, "l": 60},
        autosize=True,
        modebar={
            "orientation": "v",
            "bgcolor": "rgba(0,0,0,0.05)",
            "color": "rgba(0,0,0,0.5)",
            "activecolor": "rgba(0,0,0,0.9)",
        },
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=_PLOTLY_CONFIG,
    )

"""FastMCP server for charts and visualization.

Exposes MCP tools:
- generate_barchart: Interactive vertical bar chart
- generate_pie_chart: Pie / donut chart
- generate_line_chart: Line / scatter chart
- generate_bubble_chart: Bubble (sized scatter) chart
- generate_horizontal_bar_chart: Horizontal bar chart
"""

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP

from appkit_mcp_charts.resources.chart_view import CHART_HTML, VIEW_URI
from appkit_mcp_charts.tools.visualize import (
    BarChartGenerator,
    BubbleChartGenerator,
    HorizontalBarChartGenerator,
    LineChartGenerator,
    PieChartGenerator,
)

logger = logging.getLogger(__name__)


def create_charts_mcp_server(
    *,
    name: str = "appkit-charts-analytics",
) -> FastMCP:
    """Create and configure the FastMCP server for charts.

    Args:
        name: Server name for MCP registration.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(name)

    @mcp.resource(
        VIEW_URI,
        app=AppConfig(
            csp=ResourceCSP(
                resource_domains=["https://cdn.plot.ly"],
            ),
            prefers_border=False,
        ),
    )
    def chart_view() -> str:
        """Plotly chart view shared by all visualization tools.

        Receives the tool result via ``ui/notifications/tool-result``
        and renders the pre-built Plotly HTML inside the iframe.
        """
        return CHART_HTML

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_barchart(
        x_axis: str,
        y_axes: list[str],
        chart_title: str = "User Analytics",
        bar_mode: str = "group",
        data: list[dict[str, Any]] | None = None,
    ) -> str:
        """Visualize tabular data as an interactive vertical bar chart using Plotly.

        Args:
            x_axis: Column name for the X-axis (e.g. "role").
            y_axes: Column names for Y-axis data series.
            chart_title: Optional title for the chart.
            bar_mode: "group", "stack", or "percent".
            data: Row dicts from query_users.

        Returns:
            JSON with ``{success, html, error}``.
        """
        return await _run_chart(
            "generate_barchart",
            BarChartGenerator(),
            data,
            x_axis=x_axis,
            y_axes=y_axes,
            chart_title=chart_title,
            bar_mode=bar_mode,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_pie_chart(
        labels_column: str,
        values_column: str,
        chart_title: str = "Distribution",
        donut: bool = False,
        data: list[dict[str, Any]] | None = None,
    ) -> str:
        """Visualize tabular data as a pie or donut chart using Plotly.

        Args:
            labels_column: Column for slice labels.
            values_column: Column for slice values (numeric).
            chart_title: Optional chart title.
            donut: If True, render as a donut chart.
            data: Row dicts from query_users.

        Returns:
            JSON with ``{success, html, error}``.
        """
        return await _run_chart(
            "generate_pie_chart",
            PieChartGenerator(),
            data,
            labels_column=labels_column,
            values_column=values_column,
            chart_title=chart_title,
            donut=donut,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_line_chart(
        x_axis: str,
        y_axes: list[str],
        chart_title: str = "Trend",
        line_mode: str = "lines",
        data: list[dict[str, Any]] | None = None,
    ) -> str:
        """Visualize tabular data as a line or scatter chart using Plotly.

        Args:
            x_axis: Column for the X-axis.
            y_axes: Columns for Y-axis series.
            chart_title: Optional chart title.
            line_mode: "lines", "markers", or "lines+markers".
            data: Row dicts from query_users.

        Returns:
            JSON with ``{success, html, error}``.
        """
        return await _run_chart(
            "generate_line_chart",
            LineChartGenerator(),
            data,
            x_axis=x_axis,
            y_axes=y_axes,
            chart_title=chart_title,
            line_mode=line_mode,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_bubble_chart(
        x_column: str,
        y_column: str,
        size_column: str,
        chart_title: str = "Bubble Chart",
        label_column: str | None = None,
        data: list[dict[str, Any]] | None = None,
    ) -> str:
        """Visualize tabular data as a bubble chart using Plotly.

        Args:
            x_column: Column for X-axis.
            y_column: Column for Y-axis (numeric).
            size_column: Column for bubble size (numeric).
            chart_title: Optional chart title.
            label_column: Optional column for bubble labels.
            data: Row dicts from query_users.

        Returns:
            JSON with ``{success, html, error}``.
        """
        return await _run_chart(
            "generate_bubble_chart",
            BubbleChartGenerator(),
            data,
            x_column=x_column,
            y_column=y_column,
            size_column=size_column,
            chart_title=chart_title,
            label_column=label_column,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_horizontal_bar_chart(
        y_axis: str,
        x_axes: list[str],
        chart_title: str = "Comparison",
        bar_mode: str = "group",
        data: list[dict[str, Any]] | None = None,
    ) -> str:
        """Visualize tabular data as a horizontal bar chart.

        Args:
            y_axis: Column for the Y-axis (categories).
            x_axes: Columns for X-axis data series (numeric).
            chart_title: Optional chart title.
            bar_mode: "group", "stack", or "percent".
            data: Row dicts from query_users.

        Returns:
            JSON with ``{success, html, error}``.
        """
        return await _run_chart(
            "generate_horizontal_bar_chart",
            HorizontalBarChartGenerator(),
            data,
            y_axis=y_axis,
            x_axes=x_axes,
            chart_title=chart_title,
            bar_mode=bar_mode,
        )

    return mcp


async def _run_chart(
    tool_name: str,
    generator: Any,
    data: list[dict[str, Any]] | None,
    **kwargs: Any,
) -> str:
    """Shared helper that validates data and runs a generator."""
    if not data:
        return json.dumps(
            {
                "success": False,
                "html": None,
                "error": (
                    "Missing required 'data' parameter. "
                    "Call query_users first to obtain the data, "
                    "then pass the 'data' field from its response "
                    "to the chart tool."
                ),
            }
        )

    logger.info("Tool %s called", tool_name)
    result = await generator.generate(data, **kwargs)
    return json.dumps(
        {
            "success": result.success,
            "html": result.html,
            "error": result.error,
        },
        default=str,
    )

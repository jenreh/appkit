"""Chart generators for MCP visualization tools.

Provides a ``BaseChartGenerator`` abstract class and concrete subclasses
for bar, pie, line, bubble, and horizontal-bar charts.  Each generator
validates incoming data and produces an embeddable Plotly HTML fragment.
"""

import abc
import logging
from typing import Any

import plotly.graph_objects as go
from pydantic import Field

from appkit_mcp_commons.models import BaseResult

logger = logging.getLogger(__name__)

SERIES_COLORS = [
    "#228be6",
    "#fa5252",
    "#40c057",
    "#fab005",
    "#7950f2",
    "#fd7e14",
]

_PLOTLY_CONFIG: dict[str, Any] = {
    "displayModeBar": True,
    "scrollZoom": True,
    "modeBarButtonsToAdd": [
        "v1hovermode",
        "toggleSpikeLines",
    ],
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "my_chart",
        "width": 1200,
        "height": 600,
        "scale": 2,
    },
}


class VisualizationResult(BaseResult):
    """Result of a visualization operation."""

    html: str | None = Field(
        default=None,
        description="HTML representation of the visualization",
    )


class BaseChartGenerator(abc.ABC):
    """Abstract base class for Plotly chart generators.

    Subclasses implement :meth:`build_figure` to create chart-specific
    traces and layout.  Common validation and HTML rendering is handled
    by the base class.
    """

    chart_type: str = "chart"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> VisualizationResult:
        """Validate *data*, build a Plotly figure, and return HTML.

        Args:
            data: List of row dicts from the query tool.
            **kwargs: Chart-specific parameters forwarded to
                :meth:`build_figure`.

        Returns:
            VisualizationResult with success flag and HTML or error.
        """
        error = self._validate(data, **kwargs)
        if error:
            return VisualizationResult(success=False, error=error)

        fig = self.build_figure(data, **kwargs)
        self._apply_common_layout(fig, kwargs.get("chart_title", "Chart"))
        html = self._render_html(fig)

        logger.info(
            "Created %s visualization: rows=%d",
            self.chart_type,
            len(data),
        )
        return VisualizationResult(success=True, html=html)

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        """Create and return the Plotly ``Figure``."""

    # ------------------------------------------------------------------
    # Shared validation helpers
    # ------------------------------------------------------------------

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,  # noqa: ARG002
    ) -> str | None:
        """Run common validations.  Return an error string or ``None``."""
        if not data:
            return "No data provided for visualization"
        return None

    @staticmethod
    def _validate_columns_exist(
        data: list[dict[str, object]],
        columns: list[str],
    ) -> str | None:
        """Check that all *columns* exist in the first row of *data*."""
        if not data:
            return "No data provided"
        first_row = data[0]
        # Skip validation if generic dict without fixed schema, but chart needs keys
        available = list(first_row.keys())
        for col in columns:
            if col not in first_row:
                return f"Column '{col}' not found in data. Available: {available}"
        return None

    @staticmethod
    def _validate_numeric(
        data: list[dict[str, object]],
        columns: list[str],
    ) -> str | None:
        """Check that *columns* contain numeric data in at least one row."""
        for col in columns:
            has_numeric = False
            for row in data:
                val = row.get(col)
                if isinstance(val, int | float):
                    has_numeric = True
                    break
            if not has_numeric:
                return f"Column '{col}' does not contain numeric data"
        return None

    # ------------------------------------------------------------------
    # Shared layout / rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_common_layout(fig: go.Figure, title: str) -> None:
        """Apply shared layout settings to *fig*."""
        fig.update_layout(
            title_text=title,
            hovermode="x unified",
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

    @staticmethod
    def _render_html(fig: go.Figure) -> str:
        """Return an embeddable ``<div>`` HTML fragment."""
        return fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config=_PLOTLY_CONFIG,
        )


# ======================================================================
# Concrete generators
# ======================================================================

VALID_BAR_MODES = ("group", "stack", "percent")


class BarChartGenerator(BaseChartGenerator):
    """Vertical bar chart generator."""

    chart_type = "barchart"

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> str | None:
        base = super()._validate(data, **kwargs)
        if base:
            return base

        bar_mode: str = kwargs.get("bar_mode", "group")
        if bar_mode not in VALID_BAR_MODES:
            return "Invalid bar_mode '{}'. Must be one of: {}".format(
                bar_mode, ", ".join(VALID_BAR_MODES)
            )

        x_axis: str = kwargs.get("x_axis", "")
        y_axes: list[str] = kwargs.get("y_axes", [])

        col_err = self._validate_columns_exist(data, [x_axis, *y_axes])
        if col_err:
            return col_err
        return None

    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        x_axis: str = kwargs["x_axis"]
        y_axes: list[str] = kwargs["y_axes"]
        bar_mode: str = kwargs.get("bar_mode", "group")

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

        plotly_barmode = "stack" if bar_mode == "percent" else bar_mode
        barnorm = "percent" if bar_mode == "percent" else ""

        fig.update_layout(
            xaxis_title=x_axis,
            barmode=plotly_barmode,
            barnorm=barnorm if barnorm else None,
        )
        return fig


class PieChartGenerator(BaseChartGenerator):
    """Pie / donut chart generator."""

    chart_type = "piechart"

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> str | None:
        base = super()._validate(data, **kwargs)
        if base:
            return base

        labels_col: str = kwargs.get("labels_column", "")
        values_col: str = kwargs.get("values_column", "")

        col_err = self._validate_columns_exist(data, [labels_col, values_col])
        if col_err:
            return col_err

        num_err = self._validate_numeric(data, [values_col])
        if num_err:
            return num_err
        return None

    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        labels_col: str = kwargs["labels_column"]
        values_col: str = kwargs["values_column"]
        donut: bool = kwargs.get("donut", False)

        labels = [str(row.get(labels_col, "")) for row in data]
        values = [row.get(values_col, 0) for row in data]
        hole = 0.4 if donut else 0

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=hole,
                    marker={"colors": SERIES_COLORS[: len(labels)]},
                )
            ]
        )
        fig.update_layout(hovermode="closest")
        return fig

    @staticmethod
    def _apply_common_layout(fig: go.Figure, title: str) -> None:
        """Pie charts use ``closest`` hovermode."""
        fig.update_layout(
            title_text=title,
            hovermode="closest",
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


VALID_LINE_MODES = ("lines", "markers", "lines+markers")


class LineChartGenerator(BaseChartGenerator):
    """Line chart generator (supports multiple series)."""

    chart_type = "linechart"

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> str | None:
        base = super()._validate(data, **kwargs)
        if base:
            return base

        line_mode: str = kwargs.get("line_mode", "lines")
        if line_mode not in VALID_LINE_MODES:
            return "Invalid line_mode '{}'. Must be one of: {}".format(
                line_mode, ", ".join(VALID_LINE_MODES)
            )

        x_axis: str = kwargs.get("x_axis", "")
        y_axes: list[str] = kwargs.get("y_axes", [])

        col_err = self._validate_columns_exist(data, [x_axis, *y_axes])
        if col_err:
            return col_err
        return None

    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        x_axis: str = kwargs["x_axis"]
        y_axes: list[str] = kwargs["y_axes"]
        line_mode: str = kwargs.get("line_mode", "lines")

        x_values = [str(row.get(x_axis, "")) for row in data]
        traces = []
        for idx, col in enumerate(y_axes):
            y_values = [row.get(col, 0) for row in data]
            color = SERIES_COLORS[idx % len(SERIES_COLORS)]
            traces.append(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode=line_mode,
                    name=col,
                    line={"color": color},
                    marker={"color": color},
                )
            )

        fig = go.Figure(data=traces)
        fig.update_layout(xaxis_title=x_axis)
        return fig


class BubbleChartGenerator(BaseChartGenerator):
    """Bubble chart generator (scatter with sized markers)."""

    chart_type = "bubblechart"

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> str | None:
        base = super()._validate(data, **kwargs)
        if base:
            return base

        x_col: str = kwargs.get("x_column", "")
        y_col: str = kwargs.get("y_column", "")
        size_col: str = kwargs.get("size_column", "")

        cols = [x_col, y_col, size_col]
        label_col: str | None = kwargs.get("label_column")
        if label_col:
            cols.append(label_col)

        col_err = self._validate_columns_exist(data, cols)
        if col_err:
            return col_err

        num_err = self._validate_numeric(data, [y_col, size_col])
        if num_err:
            return num_err
        return None

    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        x_col: str = kwargs["x_column"]
        y_col: str = kwargs["y_column"]
        size_col: str = kwargs["size_column"]
        label_col: str | None = kwargs.get("label_column")

        x_values = [row.get(x_col, "") for row in data]
        y_values = [row.get(y_col, 0) for row in data]
        sizes_raw = [row.get(size_col, 0) for row in data]

        # Normalize sizes to a reasonable marker range (10-60 px)
        max_size = max(
            (s for s in sizes_raw if isinstance(s, int | float)),
            default=1,
        )
        if max_size == 0:
            max_size = 1
        sizes = [
            max(10, int(50 * (s / max_size))) if isinstance(s, int | float) else 10
            for s in sizes_raw
        ]

        text = [str(row.get(label_col, "")) for row in data] if label_col else None

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers+text" if text else "markers",
                    marker={
                        "size": sizes,
                        "color": y_values,
                        "colorscale": "Viridis",
                        "showscale": True,
                    },
                    text=text,
                    textposition="top center",
                )
            ]
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
        )
        return fig


class HorizontalBarChartGenerator(BaseChartGenerator):
    """Horizontal bar chart generator."""

    chart_type = "horizontal_barchart"

    def _validate(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> str | None:
        base = super()._validate(data, **kwargs)
        if base:
            return base

        bar_mode: str = kwargs.get("bar_mode", "group")
        if bar_mode not in VALID_BAR_MODES:
            return "Invalid bar_mode '{}'. Must be one of: {}".format(
                bar_mode, ", ".join(VALID_BAR_MODES)
            )

        y_axis: str = kwargs.get("y_axis", "")
        x_axes: list[str] = kwargs.get("x_axes", [])

        col_err = self._validate_columns_exist(data, [y_axis, *x_axes])
        if col_err:
            return col_err
        return None

    def build_figure(
        self,
        data: list[dict[str, object]],
        **kwargs: Any,
    ) -> go.Figure:
        y_axis: str = kwargs["y_axis"]
        x_axes: list[str] = kwargs["x_axes"]
        bar_mode: str = kwargs.get("bar_mode", "group")

        y_values = [str(row.get(y_axis, "")) for row in data]
        traces = []
        for idx, col in enumerate(x_axes):
            x_values = [row.get(col, 0) for row in data]
            color = SERIES_COLORS[idx % len(SERIES_COLORS)]
            traces.append(
                go.Bar(
                    x=x_values,
                    y=y_values,
                    name=col,
                    orientation="h",
                    marker_color=color,
                )
            )

        fig = go.Figure(data=traces)

        plotly_barmode = "stack" if bar_mode == "percent" else bar_mode
        barnorm = "percent" if bar_mode == "percent" else ""

        fig.update_layout(
            yaxis_title=y_axis,
            barmode=plotly_barmode,
            barnorm=barnorm if barnorm else None,
        )
        return fig

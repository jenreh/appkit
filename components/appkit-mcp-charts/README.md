# AppKit MCP Charts Server

FastMCP server for generating interactive data visualizations powered by Plotly.

## Features

- **5 chart types**: Vertical bar, horizontal bar, pie/donut, line/scatter, and bubble charts
- **MCP App views**: Each tool is backed by a shared `chart_view` resource rendered as an interactive iframe — no separate frontend needed
- **Plotly 6**: Full interactivity (zoom, pan, export to PNG) via CDN-hosted Plotly JS
- **Unauthenticated tools**: Visualization tools require no credentials, suitable for public assistant access
- **Structured generators**: `BaseChartGenerator` ABC with per-chart subclasses — easy to extend

## Tools

| Tool | Description |
| ---- | ----------- |
| `generate_barchart` | Vertical grouped/stacked bar chart |
| `generate_horizontal_bar_chart` | Horizontal grouped/stacked bar chart |
| `generate_pie_chart` | Pie or donut chart |
| `generate_line_chart` | Line, scatter, or lines+markers chart |
| `generate_bubble_chart` | Bubble (size-encoded scatter) chart |

All tools accept a `data` parameter — a list of row dicts — and return `{success, html, error}` JSON.

## Installation

```bash
uv add appkit-mcp-charts
```

## Usage

```python
from appkit_mcp_charts.server import create_charts_mcp_server

mcp = create_charts_mcp_server(name="my-charts")
```

## Dependencies

- `plotly >= 6.5.2`
- `appkit-mcp-commons`
- `appkit-commons`

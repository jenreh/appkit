"""FastMCP 3.0 server for user analytics.

Exposes two MCP tools:
- query_users_table: Dynamic SQL generation and execution
- visualize_users_as_barchart: Interactive chart generation
"""

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig
from starlette.requests import Request

from appkit_commons.registry import service_registry
from appkit_mcpapp.configuration import McpAppConfig
from appkit_mcpapp.models.schemas import UserContext
from appkit_mcpapp.services.auth_service import (
    AuthenticationError,
    authenticate_user,
)
from appkit_mcpapp.tools.query_users import query_users_table
from appkit_mcpapp.tools.visualize import visualize_users_as_barchart

logger = logging.getLogger(__name__)

VIEW_URI = "ui://appkit/chart_view.html"

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-latest.min.js"

_BAR_CHART_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Chart View</title>
<script src="{_PLOTLY_CDN}"></script>
<style>
html, body {{ margin:0; padding:0; width:100%; height:100%; }}
#chart {{ width:100%; height:100%; }}
</style>
</head>
<body>
<div id="chart"><p>Waiting for chart data&hellip;</p></div>
<script>
(function () {{
  var CHART = document.getElementById("chart");

  // Send ui/initialize handshake to host
  window.parent.postMessage({{
    jsonrpc: "2.0", method: "ui/initialize", id: 1,
    params: {{
      protocolVersion: "2025-01-26",
      clientInfo: {{ name: "chart-view", version: "1.0.0" }},
      capabilities: {{}}
    }}
  }}, "*");

  window.addEventListener("message", function (event) {{
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.method === "ping" && msg.id != null) {{
      window.parent.postMessage({{ jsonrpc: "2.0", id: msg.id, result: {{}} }}, "*");
    }}
  }});

  function handleToolResult(result) {{
    try {{
      var text = result && result.content && result.content[0]
                 && result.content[0].text;
      if (!text) {{ CHART.innerHTML = "<p>No chart data.</p>"; return; }}
      var payload = JSON.parse(text);
      if (!payload.success || !payload.html) {{
        CHART.innerHTML = "<p>" + (payload.error || "Unknown error") + "</p>";
        return;
      }}
      // Insert the Plotly <div> fragment and execute its inline scripts
      CHART.innerHTML = payload.html;
      CHART.querySelectorAll("script").forEach(function (old) {{
        var s = document.createElement("script");
        s.textContent = old.textContent;
        old.parentNode.replaceChild(s, old);
      }});
      reportSize();
    }} catch (e) {{
      CHART.innerHTML = "<p>Error: " + e.message + "</p>";
    }}
  }}

  function reportSize() {{
    window.parent.postMessage({{
      jsonrpc: "2.0", method: "ui/notifications/resize",
      params: {{ height: Math.max(CHART.scrollHeight, 400) }}
    }}, "*");
  }}
  new ResizeObserver(function () {{ reportSize(); }}).observe(CHART);
}})();
</script>
</body>
</html>
"""


def create_mcp_server(
    *,
    name: str = "user-analytics",
    base_url: str = "http://localhost:3000",
) -> FastMCP:
    """Create and configure the FastMCP server for user analytics.

    Args:
        name: Server name for MCP registration.
        base_url: Base URL of the Reflex app for chart URLs.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(name)

    @mcp.resource(VIEW_URI)
    def bar_chart_view() -> str:
        """Displays a Plotly barchart.

        Receives the tool result via ``ontoolresult``, and renders the pre-built
        Plotly HTML inside an embedded iframe.
        """
        return _BAR_CHART_HTML

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def generate_barchart(
        x_axis: str,
        y_axes: list[str],
        chart_title: str = "User Analytics",
        bar_mode: str = "group",
        data: list[dict[str, Any]] | None = None,
        ctx: Any = None,
    ) -> str:
        """Visualize tabular data as an interactive barchart using Plotly.

        Args:
            x_axis: Column name for the X-axis (e.g. "role").
            y_axes: List of column names for the Y-axis data series.
            chart_title: Optional title for the chart.
            bar_mode: Display mode — "group" (side by side),
                "stack", or "percent" (stacked to 100%).
            data: List of row dicts in a format for Plotly.
            ctx: MCP context (injected by FastMCP).

        Returns:
            JSON string with visualization result including HTML content.
        """
        if not data:
            return json.dumps(
                {
                    "success": False,
                    "html": None,
                    "error": (
                        "Missing required 'data' parameter. "
                        "Call query_users first to obtain the data, "
                        "then pass the 'data' field from its response "
                        "to generate_barchart."
                    ),
                }
            )
        user_ctx = _get_user_context(ctx)

        logger.info(
            "Tool visualize_as_barchart called by user %d",
            user_ctx.user_id,
        )

        result = await visualize_users_as_barchart(
            data,
            x_axis,
            y_axes,
            chart_title,
            bar_mode,
            base_url=base_url,
        )

        return json.dumps(
            {
                "success": result.success,
                "html": result.html,
                "error": result.error,
            },
            default=str,
        )

    @mcp.tool()
    async def query_users(
        question: str,
        ctx: Any = None,
    ) -> str:
        """Query the Appkit users table with a natural language question.

        Dynamically generates a SQL query from the question,
        validates it for safety, and executes it against the
        auth_users table. Returns structured results.

        Args:
            question: Natural language question about users,
                e.g. "How many active users are there?" or
                "Show me users grouped by role".
            ctx: MCP context (injected by FastMCP).

        Returns:
            JSON string with query results.
        """
        user_ctx = _get_user_context(ctx)
        openai_client = _get_openai_client()
        config = service_registry().get(McpAppConfig)

        logger.info(
            "Tool query_users_table called by user %d: %.200s",
            user_ctx.user_id,
            question,
        )

        result = await query_users_table(
            question,
            user_ctx,
            openai_client=openai_client,
            model=config.openai_model,
        )

        return json.dumps(
            {
                "success": result.success,
                "data": result.data,
                "columns": result.columns,
                "row_count": result.row_count,
                "error": result.error,
            },
            default=str,
        )

    return mcp


def _get_user_context(ctx: Any) -> UserContext:
    """Extract user context from MCP request context.

    Attempts to authenticate via reflex_session cookie.
    Falls back to a default unauthenticated context if no
    session is available.

    Args:
        ctx: FastMCP context object.

    Returns:
        UserContext for the authenticated user or default.
    """
    session_id = _extract_session_id(ctx)

    if not session_id:
        logger.debug("No session cookie, using default user context")
        return UserContext(user_id=0, is_admin=False, roles=[])

    try:
        return authenticate_user(session_id)
    except AuthenticationError as e:
        logger.warning("Authentication failed: %s", e)
        return UserContext(user_id=0, is_admin=False, roles=[])


def _extract_session_id(ctx: Any) -> str | None:
    """Extract reflex_session cookie from context.

    Args:
        ctx: FastMCP context or request object.

    Returns:
        Session ID string or None.
    """
    if ctx is None:
        return None

    # Try to get request from context
    request: Request | None = None
    if hasattr(ctx, "request"):
        request = ctx.request
    elif isinstance(ctx, Request):
        request = ctx

    if request and hasattr(request, "cookies"):
        return request.cookies.get("reflex_session")

    return None


def _get_openai_client() -> Any:
    """Get the OpenAI client from the service registry.

    Returns:
        AsyncOpenAI client instance or None.
    """
    try:
        from appkit_assistant.backend.services.openai_client_service import (  # noqa: PLC0415
            get_openai_client_service,
        )

        service = get_openai_client_service()
        return service.create_client()
    except Exception as e:
        logger.warning("Failed to get OpenAI client: %s", e)
        return None

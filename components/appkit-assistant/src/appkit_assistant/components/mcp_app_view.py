"""Reflex wrapper for the McpAppBridge React component.

Renders MCP App views as sandboxed iframes with full JSON-RPC
postMessage protocol compliance for tool data push, tool call
proxying, theme sync, and dynamic iframe sizing.
"""

import logging

import reflex as rx
from reflex.assets import asset
from reflex.components.component import NoSSRComponent
from reflex.vars.base import Var

from appkit_assistant.backend.schemas import McpAppViewData

logger = logging.getLogger(__name__)

_JSX = asset("mcp_app_bridge.jsx", subfolder="appkit_assistant")
_JSX_IMPORT = f"$/public/{_JSX}"


class McpAppBridge(NoSSRComponent):
    """Reflex wrapper for the McpAppBridge React component.

    Renders an MCP App in a sandboxed iframe and manages the
    JSON-RPC postMessage protocol between the host and the app.
    """

    tag = "McpAppBridge"
    library = _JSX_IMPORT
    is_default = True

    resource_url: Var[str] = ""
    tool_input: Var[str] = "{}"
    tool_result: Var[str] = "null"
    server_id: Var[int] = 0
    server_name: Var[str] = ""
    tool_name: Var[str] = ""
    theme: Var[str] = "light"
    max_height: Var[int] = 600
    prefers_border: Var[bool] = True


def mcp_app_view(view_data: McpAppViewData) -> rx.Component:
    """Construct an McpAppBridge component from view data.

    Args:
        view_data: The MCP App view data

    Returns:
        An McpAppBridge component configured with the view data
    """
    resource_url = (
        "/api/mcp-apps/"
        + view_data.server_id.to(str)  # type: ignore[union-attr]
        + "/resource?uri="
        + view_data.resource_uri
    )

    return rx.box(
        rx.hstack(
            rx.badge(
                view_data.server_name,
                variant="soft",
                color_scheme="blue",
                size="1",
            ),
            rx.text(
                view_data.tool_name,
                size="1",
                color=rx.color("gray", 9),
            ),
            spacing="2",
            padding="4px 8px",
        ),
        McpAppBridge.create(
            resource_url=resource_url,
            tool_input=view_data.tool_input.to(str),  # type: ignore[union-attr]
            tool_result=view_data.tool_result.to(str),  # type: ignore[union-attr]
            server_id=view_data.server_id,
            server_name=view_data.server_name,
            tool_name=view_data.tool_name,
            theme=rx.color_mode_cond(light="light", dark="dark"),
            prefers_border=view_data.prefers_border.bool(),  # type: ignore[union-attr]
        ),
        width="100%",
        margin_top="8px",
    )

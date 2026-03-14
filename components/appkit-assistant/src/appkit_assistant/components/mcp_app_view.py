"""Reflex wrapper for the McpAppBridge React component.

Renders MCP App views as sandboxed iframes with full JSON-RPC
postMessage protocol compliance for tool data push, tool call
proxying, theme sync, and dynamic iframe sizing.
"""

import logging

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.schemas import McpAppViewData
from appkit_assistant.components.mcp_app_bridge import mcp_app_bridge
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


def mcp_app_view(view_data: McpAppViewData) -> rx.Component:
    """Construct an McpAppBridge component from view data.

    Args:
        view_data: The MCP App view data

    Returns:
        An McpAppBridge component configured with the view data
    """
    return mn.stack(
        mn.badge(
            view_data.server_name,
            variant="light",
            color="blue",
            size="sm",
            radius="sm",
        ),
        mn.card(
            mn.card.section(
                mcp_app_bridge(
                    resource_uri=view_data.resource_uri,
                    tool_input=view_data.tool_input.to(str),  # type: ignore[union-attr]
                    tool_result=view_data.tool_result.to(str),  # type: ignore[union-attr]
                    server_id=view_data.server_id,
                    server_name=view_data.server_name,
                    tool_name=view_data.tool_name,
                    user_id=UserSession.user_id,
                    theme=rx.color_mode_cond(light="light", dark="dark"),
                    prefers_border=True,
                    backend_url=rx.config.get_config().api_url,
                    key=view_data.id,
                ),
                p="6px 12px",
            ),
            w="100%",
            mt="0",
            p="0",
            shadow="sm",
            with_border=True,
            style={"overflow": "hidden"},
        ),
        gap="3px",
        key=view_data.id,
    )

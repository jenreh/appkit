"""Reflex wrapper for the McpAppBridge React component."""

import logging

import reflex as rx
from reflex.components.component import NoSSRComponent
from reflex.vars.base import Var

logger = logging.getLogger(__name__)

# Lokales Asset
_JSX = rx.asset("mcp_app_bridge.jsx", shared=True)
_JSX_IMPORT = f"$/public/{_JSX}"


class McpAppBridge(NoSSRComponent):
    """Reflex wrapper for the McpAppBridge React component.

    Renders an MCP App in a sandboxed iframe and manages the
    JSON-RPC postMessage protocol between the host and the app.
    """

    tag = "McpAppBridge"
    library = _JSX_IMPORT
    is_default = True

    resource_uri: Var[str] = ""
    tool_input: Var[str] = "{}"
    tool_result: Var[str] = "null"
    server_id: Var[int] = 0
    server_name: Var[str] = ""
    tool_name: Var[str] = ""
    user_id: Var[int] = 0
    theme: Var[str] = "light"
    max_height: Var[int] = 600
    prefers_border: Var[bool] = True
    backend_url: Var[str] = ""


mcp_app_bridge = McpAppBridge.create

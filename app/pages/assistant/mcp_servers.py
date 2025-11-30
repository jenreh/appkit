"""MCP server management page."""

import reflex as rx

from appkit_assistant.components import mcp_servers_table
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar


@authenticated(
    route="/admin/mcp-servers",
    title="MCP Server",
    navbar=app_navbar(),
    admin_only=True,
)
def mcp_servers_page() -> rx.Component:
    """Page for managing MCP servers."""
    return requires_admin(
        rx.vstack(
            header("MCP Server"),
            mcp_servers_table(),
            width="100%",
            max_width="1200px",
            spacing="6",
        ),
    )

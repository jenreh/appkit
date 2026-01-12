import reflex as rx

from appkit_assistant.components.mcp_oauth import mcp_oauth_callback_content
from appkit_assistant.state.mcp_oauth_state import MCPOAuthState


@rx.page(
    route="/assistant/mcp/callback",
    title="MCP Verbindung",
    on_load=MCPOAuthState.handle_mcp_oauth_callback,
)
def mcp_oauth_callback_page() -> rx.Component:
    """MCP OAuth callback page."""
    return rx.theme(
        mcp_oauth_callback_content(),
        has_background=True,
    )

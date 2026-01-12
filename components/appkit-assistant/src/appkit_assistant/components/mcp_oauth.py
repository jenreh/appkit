import reflex as rx

from appkit_assistant.state.mcp_oauth_state import MCPOAuthState


def mcp_oauth_callback_content() -> rx.Component:
    """Content for the MCP OAuth callback page."""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.cond(
                    MCPOAuthState.status == "processing",
                    rx.fragment(
                        rx.spinner(size="3"),
                        rx.text(MCPOAuthState.message, size="3"),
                    ),
                    rx.cond(
                        MCPOAuthState.status == "success",
                        rx.fragment(
                            rx.icon("circle-check", size=48, color="green"),
                            rx.text(MCPOAuthState.message, size="3", weight="medium"),
                            rx.text(
                                "Dieses Fenster wird automatisch geschlossen.",
                                size="2",
                                color="gray",
                            ),
                        ),
                        rx.fragment(
                            rx.icon("circle-alert", size=48, color="red"),
                            rx.text(MCPOAuthState.message, size="3", weight="medium"),
                            rx.button(
                                "Fenster schließen",
                                on_click=rx.call_script("window.close()"),
                                variant="soft",
                            ),
                        ),
                    ),
                ),
                align="center",
                spacing="4",
                padding="6",
            ),
            size="3",
        ),
        height="100vh",
    )

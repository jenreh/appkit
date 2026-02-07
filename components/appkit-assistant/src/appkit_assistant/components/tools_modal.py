"""Component for MCP server selection modal."""

import reflex as rx

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.state.thread_state import ThreadState


def render_mcp_server_item(server: MCPServer) -> rx.Component:
    """Render a single MCP server item in the modal."""
    return rx.hstack(
        rx.switch(
            checked=ThreadState.server_selection_state.get(server.id, False),
            on_change=lambda checked: ThreadState.toggle_mcp_server_selection(
                server.id, checked
            ),
        ),
        rx.vstack(
            rx.text(server.name, font_weight="bold", size="2"),
            rx.text(server.description, size="1", color="gray"),
            spacing="1",
            align="start",
            width="100%",
        ),
        width="100%",
    )


def tools_popover() -> rx.Component:
    """Render the tools modal popup."""
    return rx.popover.root(
        rx.tooltip(
            rx.popover.trigger(
                rx.button(
                    rx.icon("pencil-ruler", size=17),
                    rx.text(
                        ThreadState.selected_mcp_servers.length().to_string()
                        + " von "
                        + ThreadState.available_mcp_servers.length().to_string(),
                        size="1",
                    ),
                    cursor="pointer",
                    variant="ghost",
                    padding="8px",
                ),
            ),
            content="Werkzeuge verwalten",
        ),
        rx.popover.content(
            rx.vstack(
                rx.text("Werkzeuge verwalten", size="3", font_weight="bold"),
                rx.cond(
                    ThreadState.available_mcp_servers.length() > 0,
                    rx.text(
                        "Wähle deine Werkzeuge für diese Unterhaltung aus.",
                        size="2",
                        color="gray",
                        margin_bottom="1.5em",
                    ),
                    rx.text(
                        "Es sind derzeit keine Werkzeuge verfügbar. "
                        "Bitte konfigurieren Sie MCP-Server in den Einstellungen.",
                        size="2",
                        color="gray",
                        margin_top="1.5em",
                    ),
                ),
                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(
                            ThreadState.available_mcp_servers,
                            render_mcp_server_item,
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    max_height="calc(66vh - 180px)",
                    scrollbars="vertical",
                    type="auto",
                ),
                rx.hstack(
                    rx.button(
                        "Anwenden",
                        on_click=ThreadState.apply_mcp_server_selection,
                        variant="solid",
                        color_scheme="blue",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("paintbrush", size=17),
                            cursor="pointer",
                            variant="ghost",
                            padding="8px",
                            margin_left="6px",
                            on_click=ThreadState.deselect_all_mcp_servers,
                        ),
                        content="Alle abwählen",
                    ),
                    spacing="2",
                    margin_top="1.5em",
                    align="center",
                ),
                spacing="1",
            ),
            width="400px",
            padding="1.5em",
            align="end",
            side="top",
        ),
        open=ThreadState.show_tools_modal,
        on_open_change=ThreadState.toggle_tools_modal,
        placement="bottom-start",
    )

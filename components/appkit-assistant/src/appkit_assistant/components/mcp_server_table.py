"""Table component for displaying MCP servers."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.components.mcp_server_dialogs import (
    add_mcp_server_button,
    add_mcp_server_modal,
    delete_mcp_server_dialog,
    edit_mcp_server_modal,
    update_mcp_server_dialog,
)
from appkit_assistant.state.mcp_server_state import MCPServerState


def mcp_server_table_row(server: MCPServer) -> rx.Component:
    """Show an MCP server in a table row."""
    # Note: Skill table uses update_skill_role inline. MCP uses update dialog.
    return mn.table.tr(
        mn.table.td(
            mn.text(server.name, size="sm", fw="500", style={"whiteSpace": "nowrap"}),
            min_width="160px",
        ),
        mn.table.td(
            mn.text(
                server.description,
                title=server.description,
                size="sm",
                c="dimmed",
                line_clamp=2,
            ),
        ),
        mn.table.td(
            mn.group(
                mn.select(
                    value=server.required_role,
                    data=MCPServerState.available_roles,
                    placeholder="nicht eingeschränkt",
                    size="xs",
                    clearable=True,
                    check_icon_position="right",
                    on_change=lambda val: MCPServerState.update_server_role(
                        server.id, val
                    ),
                    w="160px",
                ),
                mn.box(
                    rx.cond(
                        MCPServerState.updating_role_server_id == server.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.group(
                mn.switch(
                    checked=server.active,
                    on_change=lambda checked: MCPServerState.toggle_server_active(
                        server.id, checked
                    ),
                    size="sm",
                ),
                mn.box(
                    rx.cond(
                        MCPServerState.updating_active_server_id == server.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.group(
                update_mcp_server_dialog(server),
                delete_mcp_server_dialog(server),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
    )


def mcp_servers_table(
    role_labels: dict[str, str] | None = None,
    available_roles: list[dict[str, str]] | None = None,
) -> rx.Component:
    """Admin table for managing MCP servers."""
    if role_labels is None:
        role_labels = {}
    if available_roles is None:
        available_roles = []

    return mn.stack(
        add_mcp_server_modal(),
        edit_mcp_server_modal(),
        rx.flex(
            add_mcp_server_button(),
            mn.text_input(
                placeholder="Server filtern...",
                left_section=rx.icon("search", size=16),
                left_section_pointer_events="none",
                value=MCPServerState.search_filter,
                on_change=MCPServerState.set_search_filter,
                size="sm",
                w="18rem",
            ),
            rx.spacer(),
            width="100%",
            margin_bottom="md",
            gap="12px",
            align="center",
        ),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th(mn.text("Name", size="sm", fw="700")),
                    mn.table.th(mn.text("Beschreibung", size="sm", fw="700")),
                    mn.table.th(mn.text("Rolle", size="sm", fw="700")),
                    mn.table.th(mn.text("Aktiv", size="sm", fw="700")),
                    mn.table.th(mn.text("", size="sm")),
                    style={
                        "zIndex": "10",
                        "position": "relative",
                        "boxShadow": (
                            "0 4px 6px -1px rgba(0, 0, 0, 0.05), "
                            "0 2px 4px -1px rgba(0, 0, 0, 0.03)"
                        ),
                        "clipPath": "inset(0 0 -10px 0)",
                    },
                ),
            ),
            mn.table.tbody(
                rx.foreach(MCPServerState.filtered_servers, mcp_server_table_row)
            ),
            sticky_header=True,
            sticky_header_offset="0px",
            striped=False,
            highlight_on_hover=True,
            highlight_on_hover_color=rx.color_mode_cond(
                light="gray.0",
                dark="dark.8",
            ),
            w="100%",
        ),
        w="100%",
        on_mount=[
            MCPServerState.set_available_roles(available_roles, role_labels),
            MCPServerState.load_servers_with_toast,
        ],
    )

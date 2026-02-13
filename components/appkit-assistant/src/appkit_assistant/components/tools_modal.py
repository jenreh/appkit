"""Component for MCP server and skills selection modal."""

from collections.abc import Callable
from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import MCPServer, Skill
from appkit_assistant.state.thread_state import ThreadState


def _render_tool_row(
    name: rx.Var, description: rx.Var, checked: rx.Var, on_change: Any
) -> rx.Component:
    """Generic row renderer for a tool/skill item."""
    return mn.group(
        mn.switch(
            checked=checked,
            on_change=on_change,
            mt="4px",
        ),
        mn.stack(
            mn.text(name, font_weight="bold", truncate="end"),
            mn.text(
                description,
                size="xs",
                c="dimmed",
                line_clamp=1,
                title=description,
            ),
            gap="2px",
            align="start",
            w="100%",
        ),
        wrap="nowrap",
        align="flex-start",
        w="100%",
    )


def render_mcp_server_item(server: MCPServer) -> rx.Component:
    """Render a single MCP server item in the modal."""
    return _render_tool_row(
        name=server.name,
        description=server.description,
        checked=ThreadState.server_selection_state.get(server.id, False),
        on_change=lambda checked: ThreadState.toggle_mcp_server_selection(
            server.id, checked
        ),
    )


def render_skill_item(skill: Skill) -> rx.Component:
    """Render a single skill item in the modal."""
    return _render_tool_row(
        name=skill.name,
        description=skill.description,
        checked=ThreadState.skill_selection_state.get(skill.openai_id, False),
        on_change=lambda checked: ThreadState.toggle_skill_selection(
            skill.openai_id, checked
        ),
    )


def _render_section_content(
    items: rx.Var, render_item: Callable, active_msg: str, empty_msg: str
) -> rx.Component:
    """Generic renderer for a section of items (MCP servers or Skills)."""
    return rx.fragment(
        rx.cond(
            items.length() > 0,
            mn.text(active_msg, size="sm", c="dimmed", mb="1.5em"),
            mn.text(empty_msg, size="sm", c="dimmed", mt="1.5em"),
        ),
        mn.scroll_area.autosize(
            mn.stack(
                rx.foreach(items, render_item),
                gap="sm",
                w="100%",
                pb="4px",
            ),
            w="100%",
            mah="calc(66vh - 230px)",
            scrollbars="y",
            type="always",
        ),
    )


def _trigger_button() -> rx.Component:
    """Render the button that opens the tools popover."""
    return mn.button(
        rx.icon("pencil-ruler", size=13, margin_right="6px"),
        mn.text(
            ThreadState.selected_mcp_servers.length().to_string()
            + " / "
            + ThreadState.available_mcp_servers.length().to_string(),
            size="xs",
        ),
        rx.cond(
            ThreadState.selected_model_supports_skills,
            rx.fragment(
                rx.icon("sparkles", size=13, margin="0 6px 0 9px"),
                mn.text(
                    ThreadState.selected_skills.length().to_string()
                    + " / "
                    + ThreadState.available_skills_for_selection.length().to_string(),
                    size="xs",
                ),
            ),
        ),
        cursor="pointer",
        variant="subtle",
        p="8px",
    )


def _popover_content() -> rx.Component:
    """Render the main content of the popover."""
    return mn.stack(
        rx.segmented_control.root(
            rx.segmented_control.item("Werkzeuge", value="tools"),
            rx.cond(
                ThreadState.selected_model_supports_skills,
                rx.segmented_control.item("Skills", value="skills"),
            ),
            value=rx.cond(
                ThreadState.selected_model_supports_skills,
                ThreadState.modal_active_tab,
                "tools",
            ),
            on_change=ThreadState.set_modal_active_tab,
            size="2",
            width="100%",
            margin_bottom="0.5em",
        ),
        rx.box(
            rx.box(
                _render_section_content(
                    items=ThreadState.available_mcp_servers,
                    render_item=render_mcp_server_item,
                    active_msg="Wähle deine Werkzeuge für diese Unterhaltung aus.",
                    empty_msg=(
                        "Es sind derzeit keine Werkzeuge verfügbar. "
                        "Bitte konfigurieren Sie MCP-Server in den Einstellungen."
                    ),
                ),
                visibility=rx.cond(
                    ThreadState.modal_active_tab == "tools", "visible", "hidden"
                ),
                grid_area="1 / 1",
            ),
            rx.box(
                _render_section_content(
                    items=ThreadState.available_skills_for_selection,
                    render_item=render_skill_item,
                    active_msg="Wähle deine Fähigkeiten für diese Unterhaltung aus.",
                    empty_msg="Es sind derzeit keine Fähigkeiten verfügbar.",
                ),
                visibility=rx.cond(
                    ThreadState.modal_active_tab == "skills", "visible", "hidden"
                ),
                grid_area="1 / 1",
            ),
            display="grid",
            w="100%",
        ),
        mn.group(
            mn.button(
                "Anwenden",
                on_click=[
                    ThreadState.apply_mcp_server_selection,
                    ThreadState.apply_skill_selection,
                ],
                variant="filled",
                color="blue",
            ),
            mn.tooltip(
                mn.button(
                    rx.icon("paintbrush", size=17),
                    cursor="pointer",
                    variant="subtle",
                    p="8px",
                    ml="6px",
                    on_click=[
                        ThreadState.deselect_all_mcp_servers,
                        ThreadState.deselect_all_skills,
                    ],
                ),
                label="Alle abwählen",
            ),
            gap="sm",
            mt="1.5em",
            align="center",
        ),
        gap="xs",
        maw="420px",
    )


def tools_popover() -> rx.Component:
    """Render the tools modal popup."""
    return rx.popover.root(
        mn.tooltip(
            rx.popover.trigger(_trigger_button()),
            label="Werkzeuge verwalten",
        ),
        rx.popover.content(
            _popover_content(),
            p="1.5em",
            align="end",
            side="top",
            width="420px",
        ),
        open=ThreadState.show_tools_modal,
        on_open_change=ThreadState.toggle_tools_modal,
        placement="bottom-start",
    )

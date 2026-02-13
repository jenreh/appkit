"""Component for MCP server and skills selection modal."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import MCPServer, Skill
from appkit_assistant.state.thread_state import ThreadState


def render_mcp_server_item(server: MCPServer) -> rx.Component:
    """Render a single MCP server item in the modal."""
    return mn.group(
        mn.switch(
            checked=ThreadState.server_selection_state.get(server.id, False),
            on_change=lambda checked: ThreadState.toggle_mcp_server_selection(
                server.id, checked
            ),
            mt="4px",
        ),
        mn.stack(
            mn.text(server.name, font_weight="bold", truncate="end"),
            mn.text(
                server.description,
                size="xs",
                c="dimmed",
                line_clamp=1,
                title=server.description,
            ),
            gap="2px",
            align="start",
            w="100%",
        ),
        wrap="nowrap",
        align="flex-start",
        w="100%",
    )


def render_skill_item(skill: Skill) -> rx.Component:
    """Render a single skill item in the modal."""
    return mn.group(
        mn.switch(
            checked=ThreadState.skill_selection_state.get(skill.openai_id, False),
            on_change=lambda checked: ThreadState.toggle_skill_selection(
                skill.openai_id, checked
            ),
            mt="4px",
        ),
        mn.stack(
            mn.text(skill.name, font_weight="bold", truncate="end"),
            mn.text(
                skill.description,
                size="xs",
                c="dimmed",
                line_clamp=1,
                title=skill.description,
            ),
            gap="2px",
            align="start",
            w="100%",
        ),
        wrap="nowrap",
        align="flex-start",
        w="100%",
    )


def _mcp_servers_content() -> rx.Component:
    """Render the MCP servers tab content."""
    return rx.fragment(
        rx.cond(
            ThreadState.available_mcp_servers.length() > 0,
            mn.text(
                "Wähle deine Werkzeuge für diese Unterhaltung aus.",
                size="sm",
                c="dimmed",
                mb="1.5em",
            ),
            mn.text(
                "Es sind derzeit keine Werkzeuge verfügbar. "
                "Bitte konfigurieren Sie MCP-Server "
                "in den Einstellungen.",
                size="sm",
                c="dimmed",
                mt="1.5em",
            ),
        ),
        mn.scroll_area.autosize(
            mn.stack(
                rx.foreach(
                    ThreadState.available_mcp_servers,
                    render_mcp_server_item,
                ),
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


def _skills_content() -> rx.Component:
    """Render the skills tab content."""
    return rx.fragment(
        rx.cond(
            ThreadState.available_skills_for_selection.length() > 0,
            mn.text(
                "Wähle deine Fähigkeiten für diese Unterhaltung aus.",
                size="sm",
                c="dimmed",
                mb="1.5em",
            ),
            mn.text(
                "Es sind derzeit keine Fähigkeiten verfügbar.",
                size="sm",
                c="dimmed",
                mt="1.5em",
            ),
        ),
        mn.scroll_area.autosize(
            mn.stack(
                rx.foreach(
                    ThreadState.available_skills_for_selection,
                    render_skill_item,
                ),
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


def tools_popover() -> rx.Component:
    """Render the tools modal popup."""
    return rx.popover.root(
        mn.tooltip(
            rx.popover.trigger(
                mn.button(
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
                            rx.icon(
                                "sparkles",
                                size=13,
                                margin="0 6px 0 9px",
                            ),
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
                ),
            ),
            label="Werkzeuge verwalten",
        ),
        rx.popover.content(
            mn.stack(
                rx.segmented_control.root(
                    rx.segmented_control.item("Werkzeuge", value="tools"),
                    rx.cond(
                        ThreadState.selected_model_supports_skills,
                        rx.segmented_control.item(
                            "Skills",
                            value="skills",
                        ),
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
                        _mcp_servers_content(),
                        visibility=rx.cond(
                            ThreadState.modal_active_tab == "tools",
                            "visible",
                            "hidden",
                        ),
                        grid_area="1 / 1",
                    ),
                    rx.box(
                        _skills_content(),
                        visibility=rx.cond(
                            ThreadState.modal_active_tab == "skills",
                            "visible",
                            "hidden",
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
            ),
            p="1.5em",
            align="end",
            side="top",
            width="420px",
        ),
        open=ThreadState.show_tools_modal,
        on_open_change=ThreadState.toggle_tools_modal,
        placement="bottom-start",
    )

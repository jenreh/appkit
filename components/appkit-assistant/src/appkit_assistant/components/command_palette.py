"""Component for slash command palette in the composer."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.schemas import CommandDefinition
from appkit_assistant.state.thread_state import ThreadState
from appkit_assistant.state.user_prompt_state import UserPromptState

_GRID_TEMPLATE = "max-content minmax(0, 1fr) auto"
_GRID_PROPS = {
    "display": "grid",
    "grid_template_columns": _GRID_TEMPLATE,
    "gap": "2px",
    "width": "100%",
}


def render_command_label(command: CommandDefinition, index: int) -> rx.Component:
    """Render the label cell for a command item."""
    is_selected = ThreadState.selected_command_index == index
    return mn.text(
        command.label,
        fw=600,
        size="sm",
        color=rx.cond(is_selected, rx.color("accent", 11), "inherit"),
        truncate="end",
    )


def render_command_description(command: CommandDefinition) -> rx.Component:
    """Render the description cell for a command item."""
    return mn.text(
        command.description,
        size="xs",
        c="dimmed",
        truncate="end",
    )


def render_edit_button(command: CommandDefinition) -> rx.Component:
    """Render the edit button for editable commands."""
    return rx.cond(
        command.is_editable,
        mn.action_icon(
            rx.icon("pencil", size=14),
            on_click=[
                rx.stop_propagation,
                lambda: UserPromptState.open_edit_modal(command.id),
            ],
            variant="subtle",
            c="gray",
            size="sm",
            radius="sm",
            p="4px",
        ),
        mn.box(w="24px"),
    )


def render_command_item(command: CommandDefinition, index: int) -> rx.Component:
    """Render a single command item in the palette."""
    is_selected = ThreadState.selected_command_index == index

    return mn.box(
        render_command_label(command, index),
        render_command_description(command),
        render_edit_button(command),
        data_selected=rx.cond(is_selected, "true", "false"),
        class_name="command-palette-item",
        display="grid",
        grid_template_columns="subgrid",
        grid_column="1 / -1",
        p="8px 12px",
        border_radius="var(--mantine-radius-sm)",
        cursor="pointer",
        gap="12px",
        align_items="center",
        mw="0",
        w="100%",
        background=rx.cond(
            is_selected,
            rx.color("accent", 3),
            "transparent",
        ),
        _hover={"background": rx.color("gray", 3)},
        on_click=lambda: ThreadState.select_command(command.id),
    )


def render_new_prompt_item() -> rx.Component:
    """Render the 'New Prompt...' entry at the bottom of the palette."""
    return mn.box(
        mn.button(
            mn.text(
                "Neuer Prompt...",
                size="xs",
                fw=600,
                c="dimmed",
                truncate="end",
            ),
            left_section=rx.icon("plus", size=14, color=rx.color("gray", 10)),
            gap="4px",
            align="center",
            variant="subtle",
            size="xs",
            on_click=UserPromptState.open_new_modal,
        ),
        rx.spacer(),
        mn.action_icon(
            rx.icon("x", size=16),
            on_click=[rx.stop_propagation, ThreadState.dismiss_command_palette],
            variant="subtle",
            c="gray",
            size="xs",
            radius="xs",
            p="0",
        ),
        display="flex",
        align_items="center",
        gap="12px",
        p="8px 12px 8px 3px",
        br="6px",
        w="100%",
        mb="2px",
    )


def render_section_header(label: str) -> rx.Component:
    """Render a section header for command groups."""
    return mn.group(
        mn.divider(style={"flex": 1}, m=0),
        mn.text(
            label,
            size="xs",
            color=rx.color("gray", 9),
            truncate="end",
            fw=500,
        ),
        mn.divider(style={"flex": 1}, m=0),
        align="center",
        w="100%",
        # gap="xs",
    )


def _render_command_grid(
    commands: list[CommandDefinition], offset: int = 0
) -> rx.Component:
    """Render a list of commands in a grid layout."""
    return mn.box(
        rx.foreach(
            commands,
            lambda cmd, idx: render_command_item(cmd, idx + offset),
        ),
        **_GRID_PROPS,
    )


def command_palette_content() -> rx.Component:
    """Render the command palette content."""
    return mn.stack(
        rx.cond(
            ThreadState.filtered_commands.length() > 0,
            rx.fragment(
                rx.cond(
                    ThreadState.has_filtered_user_prompts,
                    _render_command_grid(ThreadState.filtered_user_prompts),
                    rx.fragment(),
                ),
                rx.cond(
                    ThreadState.has_filtered_shared_prompts,
                    rx.fragment(
                        render_section_header("Geteilte Prompts"),
                        _render_command_grid(
                            ThreadState.filtered_shared_prompts,
                            offset=ThreadState.filtered_user_prompts.length(),
                        ),
                    ),
                    rx.fragment(),
                ),
            ),
            mn.box(
                mn.text(
                    "Keine Befehle gefunden",
                    size="sm",
                    c="dimmed",
                ),
                p="12px",
                text_align="center",
            ),
        ),
        gap=0,
        w="100%",
        p="4px",
    )


def command_palette() -> rx.Component:
    """Render the command palette popover."""
    return rx.cond(
        ThreadState.show_command_palette,
        rx.fragment(
            # Overlay to catch clicks outside
            mn.box(
                pos="fixed",
                inset="0",
                z_index="999",
                on_click=ThreadState.dismiss_command_palette,
            ),
            mn.box(
                mn.card(
                    mn.scroll_area.autosize(
                        render_new_prompt_item(),
                        command_palette_content(),
                        type="auto",
                        scrollbars="y",
                        max_height="276px",
                    ),
                    shadow="md",
                    padding="xs",
                    radius="md",
                    with_border=True,
                ),
                id="command-palette",
                pos="absolute",
                bottom="100%",
                left="9px",
                miw="420px",
                w="max-content",
                maw="50%",
                mb="-6px",
                style={"zIndex": "1000"},
            ),
        ),
        rx.fragment(),
    )

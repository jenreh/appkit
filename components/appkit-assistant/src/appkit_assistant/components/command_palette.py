"""Component for slash command palette in the composer."""

import reflex as rx

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
    return rx.text(
        command.label,
        font_weight="600",
        size="2",
        color=rx.cond(is_selected, rx.color("accent", 11), "inherit"),
        white_space="nowrap",
    )


def render_command_description(command: CommandDefinition) -> rx.Component:
    """Render the description cell for a command item."""
    return rx.text(
        command.description,
        size="1",
        color=rx.color("gray", 10),
        white_space="nowrap",
        overflow="hidden",
        text_overflow="ellipsis",
        min_width="0",
    )


def render_edit_button(command: CommandDefinition) -> rx.Component:
    """Render the edit button for editable commands."""
    return rx.cond(
        command.is_editable,
        rx.icon_button(
            rx.icon("pencil", size=14),
            on_click=[
                rx.stop_propagation,
                lambda: UserPromptState.open_edit_modal(command.id),
            ],
            variant="ghost",
            size="1",
            cursor="pointer",
            color_scheme="gray",
            type="button",
        ),
        rx.box(width="24px"),
    )


def render_command_item(command: CommandDefinition, index: int) -> rx.Component:
    """Render a single command item in the palette."""
    is_selected = ThreadState.selected_command_index == index

    return rx.box(
        render_command_label(command, index),
        render_command_description(command),
        render_edit_button(command),
        data_selected=rx.cond(is_selected, "true", "false"),
        class_name="command-palette-item",
        display="grid",
        grid_template_columns="subgrid",
        grid_column="1 / -1",
        padding="8px 12px",
        border_radius="6px",
        cursor="pointer",
        gap="12px",
        align_items="center",
        min_width="0",
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
    return rx.box(
        rx.hstack(
            rx.icon("plus", size=14, color=rx.color("gray", 10)),
            rx.text(
                "Neuer Prompt...",
                size="1",
                font_weight="600",
                color=rx.color("gray", 10),
                white_space="nowrap",
            ),
            spacing="1",
            align="center",
        ),
        rx.spacer(),
        rx.icon_button(
            rx.icon("x", size=16),
            on_click=[rx.stop_propagation, ThreadState.dismiss_command_palette],
            variant="ghost",
            size="1",
            cursor="pointer",
            color_scheme="gray",
            type="button",
        ),
        display="flex",
        align_items="center",
        gap="12px",
        padding="8px 12px 8px 8px",
        border_radius="6px",
        cursor="pointer",
        width="100%",
        margin_bottom="2px",
        _hover={"background": rx.color("gray", 3)},
        on_click=UserPromptState.open_new_modal,
    )


def render_section_header(label: str) -> rx.Component:
    """Render a section header for command groups."""
    return rx.hstack(
        rx.divider(margin="0"),
        rx.text(
            label,
            size="1",
            color=rx.color("gray", 9),
            white_space="nowrap",
            font_weight="500",
        ),
        rx.divider(margin="0"),
        align_items="center",
        width="100%",
    )


def _render_command_grid(
    commands: list[CommandDefinition], offset: int = 0
) -> rx.Component:
    """Render a list of commands in a grid layout."""
    return rx.box(
        rx.foreach(
            commands,
            lambda cmd, idx: render_command_item(cmd, idx + offset),
        ),
        **_GRID_PROPS,
    )


def command_palette_content() -> rx.Component:
    """Render the command palette content."""
    return rx.vstack(
        render_new_prompt_item(),
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
            rx.box(
                rx.text(
                    "Keine Befehle gefunden",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                padding="12px",
                text_align="center",
            ),
        ),
        spacing="0",
        width="100%",
        padding="4px",
    )


def command_palette() -> rx.Component:
    """Render the command palette popover."""
    return rx.cond(
        ThreadState.show_command_palette,
        rx.fragment(
            # Overlay to catch clicks outside
            rx.box(
                position="fixed",
                inset="0",
                z_index="999",
                on_click=ThreadState.dismiss_command_palette,
            ),
            rx.box(
                rx.card(
                    rx.scroll_area(
                        command_palette_content(),
                        id="command-palette-scroll",
                        max_height="300px",
                        type="auto",
                        width="100%",
                    ),
                    size="1",
                    box_shadow="0 4px 12px rgba(0, 0, 0, 0.15)",
                    padding="6px",
                ),
                id="command-palette",
                position="absolute",
                bottom="100%",
                left="9px",
                min_width="420px",
                width="max-content",
                max_width="50%",
                margin_bottom="-6px",
                z_index="1000",
            ),
        ),
        rx.fragment(),
    )

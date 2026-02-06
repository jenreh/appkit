"""Component for slash command palette in the composer."""

import reflex as rx

from appkit_assistant.backend.schemas import CommandDefinition
from appkit_assistant.state.thread_state import ThreadState


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
        min_width="0",  # Allow shrinking in grid
    )


def render_command_item(command: CommandDefinition, index: int) -> rx.Component:
    """Render a single command item in the palette.

    Uses CSS display:contents to participate in parent grid.

    Args:
        command: The command definition to render.
        index: The index of this item in the filtered list.
    """
    is_selected = ThreadState.selected_command_index == index

    return rx.box(
        render_command_label(command, index),
        render_command_description(command),
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
        min_width="0",  # Allow shrinking in grid
        background=rx.cond(
            is_selected,
            rx.color("accent", 3),
            "transparent",
        ),
        _hover={"background": rx.color("gray", 3)},
        on_click=lambda: ThreadState.select_command(command.id),
    )


def command_palette_content() -> rx.Component:
    """Render the command palette content."""
    return rx.cond(
        ThreadState.filtered_commands.length() > 0,
        rx.box(
            rx.foreach(
                ThreadState.filtered_commands,
                lambda cmd, idx: render_command_item(cmd, idx),
            ),
            display="grid",
            grid_template_columns="max-content minmax(0, 1fr)",
            gap="2px",
            width="100%",
            padding="4px",
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
    )


def command_palette() -> rx.Component:
    """Render the command palette popover.

    The palette appears above the textarea when "/" is typed.
    It shows available commands filtered by the text after "/".
    """
    return rx.cond(
        ThreadState.show_command_palette,
        rx.box(
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Befehle",
                            size="1",
                            weight="medium",
                            color=rx.color("gray", 10),
                        ),
                        rx.text(
                            "/" + ThreadState.command_search_prefix,
                            size="1",
                            color=rx.color("accent", 10),
                            font_family="monospace",
                        ),
                        rx.spacer(),
                        rx.icon_button(
                            rx.icon("x", size=16),
                            on_click=ThreadState.dismiss_command_palette,
                            variant="ghost",
                            size="1",
                            cursor="pointer",
                            padding="0",
                            min_width="24px",
                            justify_content="center",
                        ),
                        width="100%",
                        padding_x="12px",
                        padding_top="8px",
                        align="center",
                    ),
                    rx.separator(size="4"),
                    rx.scroll_area(
                        command_palette_content(),
                        id="command-palette-scroll",
                        max_height="240px",
                        scrollbars="vertical",
                        type="auto",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                size="1",
                style={
                    "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.15)",
                },
            ),
            id="command-palette",
            position="absolute",
            bottom="100%",
            left="0",
            min_width="400px",
            width="max-content",
            max_width="50%",
            margin_bottom="8px",
            z_index="1000",
        ),
        rx.fragment(),
    )

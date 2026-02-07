"""Component for slash command palette in the composer."""

import reflex as rx

from appkit_assistant.backend.schemas import CommandDefinition
from appkit_assistant.state.thread_state import ThreadState
from appkit_assistant.state.user_prompt_state import UserPromptState


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
        rx.box(width="24px"),  # Placeholder for non-editable commands
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
        min_width="0",  # Allow shrinking in grid
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
        # Icon + text aligned with command labels
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
        # Spacer to push close button right
        rx.box(flex="1"),
        # Close button - aligned with edit buttons
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
        flex_wrap="nowrap",
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
            class_name="whitespace-nowrap font-medium",
        ),
        rx.divider(margin="0"),
        class_name="items-center w-full",
    )


def command_palette_content() -> rx.Component:
    """Render the command palette content."""
    return rx.vstack(
        render_new_prompt_item(),
        rx.cond(
            ThreadState.filtered_commands.length() > 0,
            rx.fragment(
                # User prompts section
                rx.cond(
                    ThreadState.has_filtered_user_prompts,
                    rx.box(
                        rx.foreach(
                            ThreadState.filtered_user_prompts,
                            lambda cmd, idx: render_command_item(cmd, idx),
                        ),
                        display="grid",
                        grid_template_columns="max-content minmax(0, 1fr) auto",
                        gap="2px",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                # Shared prompts section
                rx.cond(
                    ThreadState.has_filtered_shared_prompts,
                    rx.fragment(
                        render_section_header("Geteilte Prompts"),
                        rx.box(
                            rx.foreach(
                                ThreadState.filtered_shared_prompts,
                                lambda cmd, idx: render_command_item(
                                    cmd,
                                    idx + ThreadState.filtered_user_prompts.length(),
                                ),
                            ),
                            display="grid",
                            grid_template_columns="max-content minmax(0, 1fr) auto",
                            gap="2px",
                            width="100%",
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
    """Render the command palette popover.

    The palette appears above the textarea when "/" is typed.
    It shows available commands filtered by the text after "/".
    Clicking outside the palette dismisses it.
    """
    return rx.cond(
        ThreadState.show_command_palette,
        rx.fragment(
            # Invisible overlay to catch clicks outside the palette
            rx.box(
                position="fixed",
                top="0",
                left="0",
                right="0",
                bottom="0",
                z_index="999",
                on_click=ThreadState.dismiss_command_palette,
            ),
            rx.box(
                rx.card(
                    rx.scroll_area(
                        command_palette_content(),
                        id="command-palette-scroll",
                        max_height="300px",
                        scrollbars="vertical",
                        type="auto",
                        width="100%",
                    ),
                    size="1",
                    style={
                        "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.15)",
                    },
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

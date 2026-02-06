"""User Prompt Editor UI Component.

Provides a UI for managing user-defined prompts with versioning.
"""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.user_prompt_state import (
    MAX_DESCRIPTION_LENGTH,
    MAX_HANDLE_LENGTH,
    MAX_PROMPT_LENGTH,
    UserPromptDisplay,
    UserPromptState,
)
from appkit_ui.components.dialogs import delete_dialog

# Styling constants (matching navbar_component.py)
accent_bg_color = rx.color("accent", 3)
gray_bg_color = rx.color("gray", 3)
text_color = rx.color("gray", 11)
accent_text_color = rx.color("accent", 9)
border_radius = "var(--radius-2)"


def create_prompt_dialog() -> rx.Component:
    """Dialog to create a new user prompt."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=16),
                "Neuer Prompt",
                size="2",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Neuen Prompt erstellen"),
            rx.dialog.description(
                "Erstellen Sie einen neuen persönlichen Prompt.",
                size="2",
                margin_bottom="4",
            ),
            rx.vstack(
                mn.text_input(
                    label="Handle",
                    description="Eindeutiger Bezeichner (a-z, 0-9, -)",
                    placeholder="z.b. python-expert",
                    default_value=UserPromptState.new_handle,
                    on_blur=UserPromptState.set_new_handle_and_validate,
                    error=UserPromptState.new_handle_error,
                    width="100%",
                    maxlength=MAX_HANDLE_LENGTH,
                ),
                mn.text_input(
                    label="Beschreibung",
                    description="Kurze Beschreibung des Prompts.",
                    placeholder="Optionale Beschreibung...",
                    default_value=UserPromptState.new_description,
                    on_blur=UserPromptState.set_new_description_and_validate,
                    error=UserPromptState.new_description_error,
                    width="100%",
                    maxlength=MAX_DESCRIPTION_LENGTH,
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button(
                            "Abbrechen",
                            variant="soft",
                            color_scheme="gray",
                            on_click=UserPromptState.reset_new_dialog,
                        ),
                    ),
                    rx.button(
                        "Erstellen",
                        on_click=UserPromptState.create_new_prompt,
                        disabled=UserPromptState.has_new_dialog_errors,
                        loading=UserPromptState.is_loading,
                    ),
                    spacing="3",
                    justify="end",
                    margin_top="4",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="450px",
        ),
        open=UserPromptState.new_dialog_open,
        on_open_change=UserPromptState.set_new_dialog_open,
    )


def prompt_list_item(prompt: UserPromptDisplay) -> rx.Component:
    """Render a single prompt item in the sidebar list."""
    is_selected = UserPromptState.selected_handle == prompt.handle
    is_shared_tab = UserPromptState.filter_tab == "shared_prompts"

    return rx.box(
        rx.hstack(
            rx.icon(
                "message-square-text",
                size=16,
                color=rx.color("blue", 11),
                flex_shrink="0",
            ),
            rx.box(
                rx.text(
                    prompt.handle,
                    size="2",
                    weight=rx.cond(is_selected, "bold", "regular"),
                    style={
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "display": "block",
                    },
                ),
                rx.text(
                    prompt.description,
                    size="1",
                    color="gray",
                    style={
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "display": "block",
                    },
                ),
                rx.cond(
                    is_shared_tab,
                    rx.text(
                        "von " + prompt.creator_name,
                        color="gray",
                        size="1",
                        style={
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                            "display": "block",
                        },
                    ),
                    rx.fragment(),
                ),
                display="flex",
                flex_direction="column",
                gap="2px",
                width="0",
                flex="1",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        padding="12px",
        cursor="pointer",
        background=rx.cond(
            is_selected,
            rx.color("blue", 3),
            "transparent",
        ),
        _hover={
            "background": rx.color("blue", 4),
        },
        border_bottom=f"1px solid {rx.color('gray', 4)}",
        on_click=lambda: UserPromptState.set_selected_by_handle(prompt.handle),
        width="100%",
    )


def prompt_list() -> rx.Component:
    """Left panel with scrollable prompt list."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    UserPromptState.filter_tab == "my_prompts",
                    rx.foreach(UserPromptState.my_prompts, prompt_list_item),
                    rx.foreach(UserPromptState.shared_prompts, prompt_list_item),
                ),
                spacing="0",
                width="100%",
                padding="0",
            ),
            type="hover",
            scrollbars="vertical",
            style={"height": "100%"},
        ),
        width="280px",
        min_width="280px",
        height="100%",
        border_right=f"1px solid {rx.color('gray', 4)}",
        background=rx.color("gray", 2),
    )


def editor_panel() -> rx.Component:
    """Right panel for editing the selected prompt."""

    return rx.box(
        rx.cond(
            UserPromptState.selected_handle == "",
            # Empty state
            rx.center(
                rx.vstack(
                    rx.icon("file-text", size=48, color=rx.color("gray", 8)),
                    rx.text(
                        "Wählen Sie einen Prompt aus der Liste",
                        color="gray",
                        size="3",
                    ),
                    rx.text(
                        "oder erstellen Sie einen neuen Prompt",
                        color="gray",
                        size="2",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                height="100%",
            ),
            # Editor content - simple layout like system prompt editor
            rx.vstack(
                mn.text_input(
                    default_value=UserPromptState.current_handle,
                    label="Eindeutiger Bezeichner",
                    description=(
                        "Der eindeutige Bezeichner für diesen Prompt. "
                        "Nur Kleinbuchstaben, Zahlen und Bindestriche."
                    ),
                    on_blur=UserPromptState.set_current_handle_and_validate,
                    error=UserPromptState.handle_error,
                    width="100%",
                    maxlength=MAX_HANDLE_LENGTH,
                    key=UserPromptState.textarea_key,
                    disabled=rx.cond(UserPromptState.is_owner, False, True),
                ),
                mn.text_input(
                    label="Beschreibung",
                    default_value=UserPromptState.current_description,
                    description="Kurze Beschreibung des Prompts.",
                    on_blur=UserPromptState.set_current_description_and_validate,
                    error=UserPromptState.description_error,
                    placeholder="Optionale Beschreibung...",
                    read_only=~UserPromptState.is_owner,
                    width="100%",
                    maxlength=MAX_DESCRIPTION_LENGTH,
                    key=UserPromptState.textarea_key,
                    disabled=rx.cond(UserPromptState.is_owner, False, True),
                ),
                rx.text(
                    UserPromptState.char_count.to_string()
                    + f" / {MAX_PROMPT_LENGTH} Zeichen",
                    size="1",
                    color="gray",
                    margin_top="6px",
                ),
                mn.textarea(
                    placeholder="System-Prompt hier eingeben...",
                    default_value=UserPromptState.current_prompt,
                    variant="filled",
                    width="100%",
                    key=UserPromptState.textarea_key,
                    disabled=rx.cond(UserPromptState.is_owner, False, True),
                    on_change=UserPromptState.set_current_prompt,
                    on_blur=UserPromptState.set_current_prompt_and_validate,
                    error=UserPromptState.prompt_error,
                    read_only=~UserPromptState.is_owner,
                    styles={
                        "root": {
                            "flex": 1,
                            "display": "flex",
                            "flexDirection": "column",
                        },
                        "wrapper": {"flex": 1},
                        "input": {
                            "flex": 1,
                            "height": "calc(100vh - 442px)",
                            "fontFamily": "monospace",
                            "fontSize": "0.8rem",
                        },
                    },
                ),
                rx.hstack(
                    mn.select(
                        placeholder="Aktuell",
                        data=UserPromptState.versions,
                        value=UserPromptState.selected_version_str,
                        on_change=UserPromptState.set_selected_version_id,
                        clearable=False,
                        searchable=False,
                        disabled=rx.cond(UserPromptState.is_owner, False, True),
                        width="280px",
                    ),
                    rx.cond(
                        UserPromptState.is_owner,
                        rx.hstack(
                            rx.switch(
                                checked=UserPromptState.is_shared,
                                on_change=UserPromptState.toggle_shared,
                            ),
                            rx.text("Freigeben", size="2"),
                            spacing="2",
                            align="center",
                        ),
                        rx.fragment(),
                    ),
                    rx.spacer(),
                    rx.cond(
                        UserPromptState.is_owner,
                        delete_dialog(
                            title="Prompt löschen?",
                            content=UserPromptState.current_handle,
                            on_click=UserPromptState.delete_prompt,
                            icon_button=True,
                            variant="outline",
                            color_scheme="red",
                            disabled=UserPromptState.is_loading,
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        UserPromptState.is_owner,
                        rx.button(
                            "Neue Version speichern",
                            on_click=UserPromptState.save_prompt,
                            loading=UserPromptState.is_loading,
                            disabled=UserPromptState.has_validation_errors,
                        ),
                        rx.fragment(),
                    ),
                    align="center",
                    width="100%",
                    spacing="3",
                    margin_top="12px",
                ),
                display="flex",
                flex_direction="column",
                width="100%",
                max_width="960px",
                height="100%",
                spacing="1",
                padding="6",
            ),
        ),
        flex="1",
        height="100%",
        overflow="auto",
        padding="12px",
    )


def user_prompt_editor() -> rx.Component:
    """Main component for the user prompt editor page."""
    return rx.vstack(
        # Header row with tabs and new prompt button
        rx.hstack(
            rx.segmented_control.root(
                rx.segmented_control.item(
                    rx.hstack(rx.icon("user", size=14), rx.text("Meine"), spacing="2"),
                    value="my_prompts",
                ),
                rx.segmented_control.item(
                    rx.hstack(
                        rx.icon("share-2", size=14), rx.text("Geteilt"), spacing="2"
                    ),
                    value="shared_prompts",
                ),
                value=UserPromptState.filter_tab,
                on_change=UserPromptState.set_filter_tab,
            ),
            create_prompt_dialog(),
            width="100%",
            padding="4",
            align="center",
        ),
        # Main content area
        rx.box(
            rx.hstack(
                prompt_list(),
                editor_panel(),
                spacing="0",
                width="100%",
                height="100%",
            ),
            width="100%",
            flex="1",
            border=f"1px solid {rx.color('gray', 4)}",
            border_radius="8px",
            overflow="hidden",
        ),
        width="100%",
        height="calc(100vh - 120px)",
        spacing="3",
        padding="4",
    )

"""Modal for editing user prompts from command palette."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.user_prompt_state import (
    MAX_DESCRIPTION_LENGTH,
    MAX_HANDLE_LENGTH,
    MAX_PROMPT_LENGTH,
    UserPromptState,
)
from appkit_ui.components.dialogs import delete_dialog

TEXTAREA_STYLES = {
    "root": {
        "flex": 1,
        "display": "flex",
        "flexDirection": "column",
    },
    "wrapper": {"flex": 1},
    "input": {
        "flex": 1,
        "height": "210px",
        "fontFamily": "monospace",
        "fontSize": "0.8rem",
    },
}


def _render_handle_input() -> rx.Component:
    return mn.text_input(
        label="Eindeutiger Bezeichner",
        description=(
            "Der eindeutige Bezeichner für diesen Prompt. "
            "Nur Kleinbuchstaben, Zahlen und Bindestriche."
        ),
        placeholder="z.b. python-expert",
        default_value=UserPromptState.modal_handle,
        on_blur=UserPromptState.set_modal_handle,
        error=UserPromptState.modal_handle_error,
        width="100%",
        required=True,
        maxlength=MAX_HANDLE_LENGTH,
        key=UserPromptState.modal_textarea_key,
    )


def _render_description_input() -> rx.Component:
    return mn.text_input(
        label="Beschreibung",
        description="Kurze Beschreibung des Prompts.",
        placeholder="Optionale Beschreibung...",
        default_value=UserPromptState.modal_description,
        on_blur=UserPromptState.set_modal_description_and_validate,
        error=UserPromptState.modal_description_error,
        width="100%",
        maxlength=MAX_DESCRIPTION_LENGTH,
        key=UserPromptState.modal_textarea_key,
    )


def _render_prompt_textarea() -> rx.Component:
    return mn.textarea(
        placeholder="Prompt-Text hier eingeben...",
        description=UserPromptState.modal_char_count.to_string()
        + f" / {MAX_PROMPT_LENGTH} Zeichen",
        default_value=UserPromptState.modal_prompt,
        on_change=UserPromptState.set_modal_prompt,
        on_blur=UserPromptState.set_modal_prompt_and_validate,
        error=UserPromptState.modal_prompt_error,
        width="100%",
        key=UserPromptState.modal_textarea_key,
        required=True,
        maxlength=MAX_PROMPT_LENGTH,
        styles=TEXTAREA_STYLES,
    )


def _render_metadata_row() -> rx.Component:
    return rx.flex(
        # Version selector (only for edit mode)
        rx.cond(
            ~UserPromptState.modal_is_new,
            mn.select(
                placeholder="Aktuell",
                data=UserPromptState.modal_versions,
                value=UserPromptState.modal_selected_version_str,
                on_change=UserPromptState.set_modal_selected_version_id,
                clearable=False,
                searchable=False,
                width="240px",
            ),
            rx.fragment(),
        ),
        rx.flex(
            mn.switch(
                checked=UserPromptState.modal_is_shared,
                on_change=UserPromptState.set_modal_is_shared,
            ),
            rx.tooltip(
                rx.text("Mit anderen teilen", size="2"),
                content=(
                    "Wenn aktiviert, kann dieser Prompt von allen "
                    "anderen Benutzern gesehen und verwendet werden."
                ),
            ),
            direction="row",
            gap="9px",
            align="center",
            flex_grow="1",
            margin_right="6px",
            justify_content="end",
        ),
        direction="row",
        gap="12px",
        align="center",
        width="100%",
    )


def _render_footer() -> rx.Component:
    return rx.flex(
        rx.cond(
            ~UserPromptState.modal_is_new,
            delete_dialog(
                title="Prompt löschen",
                content=" /" + UserPromptState.modal_handle + " ",
                on_click=UserPromptState.delete_from_modal,
                action_loading=UserPromptState.is_loading,
                disabled=UserPromptState.is_loading,
            ),
            rx.fragment(),
        ),
        rx.spacer(),
        mn.button(
            "Abbrechen",
            variant="subtle",
            on_click=UserPromptState.close_modal,
        ),
        mn.button(
            UserPromptState.modal_save_button_text,
            on_click=UserPromptState.save_from_modal,
            loading=UserPromptState.is_loading,
            disabled=UserPromptState.has_modal_validation_errors,
        ),
        direction="row",
        width="100%",
        gap="9px",
        margin_top="9px",
    )


def prompt_edit_modal() -> rx.Component:
    """Modal dialog for editing or creating user prompts."""
    return mn.modal(
        rx.flex(
            _render_handle_input(),
            _render_description_input(),
            _render_prompt_textarea(),
            _render_metadata_row(),
            rx.cond(
                UserPromptState.modal_error != "",
                rx.callout(
                    UserPromptState.modal_error,
                    icon="circle-alert",
                    color="red",
                    size="1",
                ),
                rx.fragment(),
            ),
            _render_footer(),
            direction="column",
            gap="12px",
            width="100%",
        ),
        title=UserPromptState.modal_title,
        opened=UserPromptState.modal_open,
        on_close=UserPromptState.close_modal,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )

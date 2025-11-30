# app/components/system_prompt_editor.py

"""System Prompt Editor UI Komponente."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.dialogs import delete_dialog


def system_prompt_editor() -> rx.Component:
    """Admin-UI für das System Prompt Versioning mit appkit-mantine & appkit-ui."""
    return rx.vstack(
        mn.markdown_preview(
            source=(
                """
Der System-Prompt legt fest, wie sich der Assistent verhält. Bitte stellen Sie sicher,
dass der Platzhalter `{mcp_prompts}` immer im Text enthalten ist. Dieser Platzhalter ist
notwendig, damit das System im Hintergrund die benötigten Funktionen und Werkzeuge
automatisch einfügen kann."""
            ),
            width="100%",
        ),
        mn.textarea(
            placeholder="System-Prompt hier eingeben (max. 10.000 Zeichen)...",
            description=f"{SystemPromptState.char_count} / 10.000 Zeichen",
            default_value=SystemPromptState.current_prompt,
            on_change=SystemPromptState.set_current_prompt,
            error=SystemPromptState.error_message,
            rows=21,
            variant="filled",
            width="100%",
        ),
        rx.hstack(
            mn.select(
                placeholder="Aktuell",
                data=SystemPromptState.versions,
                value=rx.cond(
                    SystemPromptState.selected_version_id == 0,
                    "",
                    str(SystemPromptState.selected_version_id),
                ),
                on_change=SystemPromptState.set_selected_version,
                clearable=True,
                searchable=True,
                width="280px",
            ),
            delete_dialog(
                title="Version endgültig löschen?",
                content="die ausgewählte Version",
                on_click=SystemPromptState.delete_version,
                icon_button=True,
                class_name="dialog",
                disabled=SystemPromptState.is_loading
                | (SystemPromptState.selected_version_id == 0),
            ),
            rx.spacer(),
            rx.button(
                "Neue Version speichern",
                on_click=SystemPromptState.save_current,
                disabled=SystemPromptState.is_loading
                | (
                    SystemPromptState.current_prompt
                    == SystemPromptState.last_saved_prompt
                ),
                loading=SystemPromptState.is_loading,
            ),
            align="center",
            width="100%",
            spacing="4",
        ),
        width="100%",
        max_width="960px",
        padding="6",
        spacing="5",
    )

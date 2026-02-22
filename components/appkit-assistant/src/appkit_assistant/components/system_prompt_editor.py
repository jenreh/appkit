import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.dialogs import delete_dialog


def system_prompt_editor() -> rx.Component:
    """Admin-UI für das System Prompt Versioning mit appkit-mantine & appkit-ui.

    Uses a hybrid approach for the textarea:
    - default_value + on_change prevents cursor jumping during typing
    - key prop forces re-render when selecting a different version
    - This gives us both smooth editing AND the ability to update from select
    """
    return mn.stack(
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
            key=SystemPromptState.textarea_key,
        ),
        mn.group(
            mn.select(
                placeholder="Aktuell",
                data=SystemPromptState.versions,
                value=SystemPromptState.selected_version_str,
                on_change=SystemPromptState.set_selected_version,
                clearable=False,
                searchable=False,
                width="280px",
            ),
            delete_dialog(
                title="Version endgültig löschen?",
                content="die ausgewählte Version",
                on_click=SystemPromptState.delete_version,
                icon_button=False,
                class_name="dialog",
                variant="outline",
                color="red",
                m="-2px 0",
                p="0 6px",
                disabled=SystemPromptState.is_loading
                | (SystemPromptState.selected_version_id == 0),
            ),
            rx.spacer(),
            mn.button(
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
            w="100%",
            gap="sm",
            wrap="nowrap",
        ),
        w="100%",
        maw="960px",
        p="18px",
        gap="sm",
    )

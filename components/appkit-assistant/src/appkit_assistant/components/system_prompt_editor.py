# app/components/system_prompt_editor.py

"""System Prompt Editor UI Komponente."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.dialogs import delete_dialog


def system_prompt_editor() -> rx.Component:
    """Admin-UI für das System Prompt Versioning mit appkit-mantine & appkit-ui."""
    return rx.vstack(
        rx.heading("System Prompt", size="6", margin_bottom="4"),
        # Editor mit korrektem f-string Pattern für Description
        mn.textarea(
            placeholder="System-Prompt hier eingeben (max. 20.000 Zeichen)...",
            description=f"{SystemPromptState.char_count} / 20.000 Zeichen",
            default_value=SystemPromptState.current_prompt,
            on_change=SystemPromptState.set_current_prompt,
            autosize=True,
            min_rows=18,
            max_rows=25,
            variant="filled",
            width="100%",
        ),
        rx.cond(
            SystemPromptState.error_message != "",
            rx.callout.root(
                rx.callout.text(SystemPromptState.error_message),
                color="red",
                role="alert",
            ),
        ),
        rx.hstack(
            mn.select(
                placeholder="Aktuell",
                data=[
                    {
                        "value": str(v["id"]),
                        "label": f"v{v['version']} – {v['created_at']}",
                    }
                    for v in SystemPromptState.versions
                ],
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
            rx.spacer(),
            # Mitte: Delete-Dialog aus appkit-ui
            delete_dialog(
                title="Version endgültig löschen?",
                content="die ausgewählte Version",
                on_click=SystemPromptState.delete_version,
                icon_button=False,
                class_name="dialog",
                disabled=SystemPromptState.is_loading
                | (SystemPromptState.selected_version_id == 0),
            ),
            mn.button(
                "Neue Version speichern",
                color="violet",
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
        max_width="1400px",
        padding="6",
        spacing="5",
    )

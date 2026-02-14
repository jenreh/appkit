"""Dialog components for skill management."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import Skill
from appkit_assistant.state.skill_admin_state import SkillAdminState
from appkit_ui.components.dialogs import delete_dialog

UPLOAD_ID = "skill_zip_upload"


def create_skill_modal() -> rx.Component:
    """Modal for uploading a new skill zip file."""
    return mn.modal(
        rx.flex(
            rx.upload(
                rx.cond(
                    rx.selected_files(UPLOAD_ID),
                    rx.vstack(
                        mn.text(
                            rx.selected_files(UPLOAD_ID)[0],
                            size="sm",
                            fw="500",
                        ),
                        mn.text(
                            "Klicken zum Ändern",
                            size="xs",
                            c="dimmed",
                        ),
                        align="center",
                        spacing="1",
                    ),
                    rx.vstack(
                        mn.text(
                            "ZIP-Datei hierher ziehen oder klicken",
                            size="sm",
                        ),
                        mn.text(
                            "Nur .zip Dateien",
                            size="xs",
                            c="dimmed",
                        ),
                        align="center",
                        spacing="1",
                    ),
                ),
                id=UPLOAD_ID,
                accept={
                    "application/zip": [".zip"],
                    "application/x-zip-compressed": [".zip"],
                },
                max_files=1,
                border="1px dashed var(--mantine-color-gray-5)",
                border_radius="var(--mantine-radius-md)",
                padding="2em",
                width="100%",
                cursor="pointer",
            ),
            rx.flex(
                mn.button(
                    "Abbrechen",
                    variant="subtle",
                    on_click=SkillAdminState.close_create_modal,
                ),
                mn.button(
                    "Hochladen",
                    on_click=SkillAdminState.handle_upload(
                        rx.upload_files(upload_id=UPLOAD_ID)
                    ),
                    loading=SkillAdminState.uploading,
                    disabled=~rx.selected_files(UPLOAD_ID),
                ),
                direction="row",
                width="100%",
                gap="9px",
                margin_top="12px",
                justify_content="end",
            ),
            direction="column",
            gap="12px",
            width="100%",
        ),
        title="Neuen Skill anlegen",
        opened=SkillAdminState.create_modal_open,
        on_close=SkillAdminState.close_create_modal,
        size="md",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def delete_skill_dialog(skill: Skill) -> rx.Component:
    """Delete confirmation dialog for a skill."""
    return delete_dialog(
        title="Skill löschen",
        content=skill.name,
        on_click=lambda: SkillAdminState.delete_skill(skill.id),
        icon_button=True,
        variant="ghost",
        color_scheme="red",
    )

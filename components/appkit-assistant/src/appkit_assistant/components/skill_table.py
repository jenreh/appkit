"""Table component for displaying and managing OpenAI skills."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import Skill
from appkit_assistant.components.skill_dialogs import (
    create_skill_modal,
    delete_skill_dialog,
)
from appkit_assistant.state.skill_admin_state import SkillAdminState


def _skill_table_row(skill: Skill) -> rx.Component:
    """Render a single skill row."""
    return mn.table.tr(
        mn.table.td(
            mn.text(skill.name, size="sm", fw="500", style={"whiteSpace": "nowrap"}),
        ),
        mn.table.td(
            mn.text(
                skill.description,
                size="sm",
                c="dimmed",
                line_clamp=2,
                title=skill.description,
            ),
            max_width="300px",
        ),
        mn.table.td(
            mn.text(skill.default_version, size="sm"),
        ),
        mn.table.td(
            mn.text(skill.latest_version, size="sm"),
        ),
        mn.table.td(
            mn.select(
                value=skill.required_role,
                data=SkillAdminState.available_roles,
                placeholder="Keine Rolle",
                size="xs",
                clearable=True,
                check_icon_position="right",
                on_change=lambda val: SkillAdminState.update_skill_role(skill.id, val),
                w="160px",
            ),
        ),
        mn.table.td(
            mn.switch(
                checked=skill.active,
                on_change=lambda checked: (
                    SkillAdminState.toggle_skill_active(skill.id, checked)
                ),
                size="sm",
            ),
        ),
        mn.table.td(
            rx.hstack(
                delete_skill_dialog(skill),
                spacing="2",
                align_items="center",
            ),
        ),
    )


def skills_table(
    role_labels: dict[str, str] | None = None,
    available_roles: list[dict[str, str]] | None = None,
) -> rx.Component:
    """Admin table for managing OpenAI skills."""
    if role_labels is None:
        role_labels = {}
    if available_roles is None:
        available_roles = []

    return mn.stack(
        rx.flex(
            mn.button(
                "Neuen Skill anlegen",
                left_section=rx.icon("plus", size=16),
                size="sm",
                on_click=SkillAdminState.open_create_modal,
            ),
            mn.text_input(
                placeholder="Skills filtern...",
                left_section=rx.icon("search", size=16),
                left_section_pointer_events="none",
                value=SkillAdminState.search_filter,
                on_change=SkillAdminState.set_search_filter,
                size="sm",
                w="18rem",
            ),
            rx.spacer(),
            mn.button(
                "Synchronisieren",
                left_section=rx.icon("refresh-cw", size=16),
                size="sm",
                variant="outline",
                on_click=SkillAdminState.sync_skills,
                loading=SkillAdminState.syncing,
            ),
            width="100%",
            margin_bottom="md",
            gap="12px",
            align="center",
        ),
        create_skill_modal(),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th(mn.text("Name", size="sm", fw="700")),
                    mn.table.th(mn.text("Beschreibung", size="sm", fw="700")),
                    mn.table.th(mn.text("Default", size="sm", fw="700")),
                    mn.table.th(mn.text("Latest", size="sm", fw="700")),
                    mn.table.th(mn.text("Rolle", size="sm", fw="700")),
                    mn.table.th(mn.text("Aktiv", size="sm", fw="700")),
                    mn.table.th(mn.text("", size="sm")),
                ),
            ),
            mn.table.tbody(
                rx.foreach(
                    SkillAdminState.filtered_skills,
                    _skill_table_row,
                )
            ),
            striped=False,
            highlight_on_hover=True,
            w="100%",
        ),
        w="100%",
        on_mount=lambda: [
            SkillAdminState.set_available_roles(available_roles, role_labels),
            SkillAdminState.load_skills_with_toast(),
        ],
    )

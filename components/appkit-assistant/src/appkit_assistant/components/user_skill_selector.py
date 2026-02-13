"""User skill selector component for profile page."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.skill_state import SkillState


def _skill_item(skill: dict) -> rx.Component:
    """Render a single skill toggle item."""
    return mn.group(
        mn.stack(
            mn.text(skill["name"], size="sm", fw="500"),
            mn.text(
                skill["description"],
                size="xs",
                c="dimmed",
            ),
            gap="0",
            flex="1",
        ),
        mn.switch(
            checked=skill["enabled"],
            on_change=lambda checked: SkillState.toggle_skill_enabled(
                skill["openai_id"], checked
            ),
            size="sm",
        ),
        w="100%",
        p="sm",
        style={
            "border_bottom": "1px solid var(--mantine-color-gray-3)",
        },
    )


def user_skill_selector() -> rx.Component:
    """List of skills with enable/disable toggles for the current user."""
    return mn.stack(
        rx.cond(
            SkillState.has_skills,
            mn.stack(
                rx.foreach(SkillState.available_skills, _skill_item),
                w="100%",
                gap="0",
            ),
            mn.text(
                "Keine Skills verfügbar.",
                size="sm",
                c="dimmed",
            ),
        ),
        w="100%",
        on_mount=SkillState.load_user_skills,
    )

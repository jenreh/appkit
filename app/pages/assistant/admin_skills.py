"""Administration page for OpenAI skills management."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.components.skill_table import skills_table
from appkit_assistant.roles import ASSISTANT_USER_ROLE
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar
from app.roles import MCP_ADVANCED_ROLE, MCP_BASIC_ROLE

ROLE_LABELS: dict[str, str] = {
    ASSISTANT_USER_ROLE.name: ASSISTANT_USER_ROLE.label,
    MCP_BASIC_ROLE.name: MCP_BASIC_ROLE.label,
    MCP_ADVANCED_ROLE.name: MCP_ADVANCED_ROLE.label,
}

AVAILABLE_ROLES = [
    {
        "value": ASSISTANT_USER_ROLE.name,
        "label": ASSISTANT_USER_ROLE.label,
    },
    {"value": MCP_BASIC_ROLE.name, "label": MCP_BASIC_ROLE.label},
    {
        "value": MCP_ADVANCED_ROLE.name,
        "label": MCP_ADVANCED_ROLE.label,
    },
]


@authenticated(
    route="/admin/skills",
    title="Skill Administration",
    navbar=app_navbar(),
    admin_only=True,
)
def admin_skills_page() -> rx.Component:
    """Admin page for managing OpenAI skills."""
    return requires_admin(
        mn.stack(
            header("Skill Administration"),
            skills_table(
                role_labels=ROLE_LABELS,
                available_roles=AVAILABLE_ROLES,
            ),
            w="100%",
            maw="1200px",
            p="2rem",
        ),
    )

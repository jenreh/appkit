"""Admin page for system prompt management."""

import reflex as rx

from appkit_assistant.components.system_prompt_editor import system_prompt_editor
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar


@authenticated(
    route="/admin/system-prompt",
    title="System Prompt",
    navbar=app_navbar(),
    admin_only=True,
    on_load=SystemPromptState.load_versions,
)
def system_prompt_page() -> rx.Component:
    """Admin page for editing system prompts."""
    return requires_admin(
        rx.vstack(
            header("System Prompt"),
            system_prompt_editor(),
            width="100%",
            max_width="1200px",
            spacing="6",
        ),
    )

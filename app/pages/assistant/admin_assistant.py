"""Consolidated assistant administration page with tabbed layout."""

import reflex as rx

from appkit_assistant.components import file_manager, mcp_servers_table
from appkit_assistant.components.system_prompt_editor import system_prompt_editor
from appkit_assistant.roles import (
    ASSISTANT_USER_ROLE,
)
from appkit_assistant.state.file_manager_state import FileManagerState
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar
from app.roles import MCP_ADVANCED_ROLE, MCP_BASIC_ROLE

# Mapping from role name to display label
ROLE_LABELS: dict[str, str] = {
    ASSISTANT_USER_ROLE.name: ASSISTANT_USER_ROLE.label,
    MCP_BASIC_ROLE.name: MCP_BASIC_ROLE.label,
    MCP_ADVANCED_ROLE.name: MCP_ADVANCED_ROLE.label,
}

AVAILABLE_ROLES = [
    {"value": ASSISTANT_USER_ROLE.name, "label": ASSISTANT_USER_ROLE.label},
    {"value": MCP_BASIC_ROLE.name, "label": MCP_BASIC_ROLE.label},
    {"value": MCP_ADVANCED_ROLE.name, "label": MCP_ADVANCED_ROLE.label},
]


class AdminAssistantState(rx.State):
    """State for managing admin assistant page tabs."""

    active_tab: str = "mcp"
    system_prompt_loaded: bool = False
    file_manager_loaded: bool = False

    async def on_tab_change(self, value: str) -> None:
        """Handle tab changes and load data when needed."""
        self.active_tab = value
        if value == "system_prompt" and not self.system_prompt_loaded:
            system_prompt_state = await self.get_state(SystemPromptState)
            await system_prompt_state.load_versions()
            self.system_prompt_loaded = True
        elif value == "file_manager" and not self.file_manager_loaded:
            file_manager_state = await self.get_state(FileManagerState)
            async for _ in file_manager_state.load_vector_stores():
                pass
            self.file_manager_loaded = True


@authenticated(
    route="/admin/assistant",
    title="Assistant Administration",
    navbar=app_navbar(),
    admin_only=True,
)
def admin_assistant_page() -> rx.Component:
    """Consolidated admin page for managing assistant configuration."""
    return requires_admin(
        rx.vstack(
            header("Assistant Administration"),
            rx.vstack(
                rx.tabs(
                    rx.tabs.list(
                        rx.tabs.trigger("MCP Server", value="mcp"),
                        rx.tabs.trigger("System Prompt", value="system_prompt"),
                        rx.tabs.trigger("Dateimanager", value="file_manager"),
                        margin_bottom="21px",
                    ),
                    rx.tabs.content(
                        mcp_servers_table(
                            role_labels=ROLE_LABELS, available_roles=AVAILABLE_ROLES
                        ),
                        value="mcp",
                    ),
                    rx.tabs.content(
                        system_prompt_editor(),
                        value="system_prompt",
                    ),
                    rx.tabs.content(
                        file_manager(),
                        value="file_manager",
                    ),
                    value=AdminAssistantState.active_tab,
                    on_change=AdminAssistantState.on_tab_change,
                    width="100%",
                ),
                width="100%",
                max_width="1200px",
                margin_x="auto",
                spacing="6",
            ),
            width="100%",
            spacing="6",
        ),
    )

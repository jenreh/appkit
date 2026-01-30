"""Consolidated assistant administration page with tabbed layout."""

import reflex as rx

from appkit_assistant.components import file_manager, mcp_servers_table
from appkit_assistant.components.system_prompt_editor import system_prompt_editor
from appkit_assistant.state.file_manager_state import FileManagerState
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar


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
            rx.tabs(
                rx.tabs.list(
                    rx.tabs.trigger("MCP Server", value="mcp"),
                    rx.tabs.trigger("System Prompt", value="system_prompt"),
                    rx.tabs.trigger("Dateimanager", value="file_manager"),
                    margin_bottom="21px",
                ),
                rx.tabs.content(
                    mcp_servers_table(),
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
            spacing="6",
        ),
    )

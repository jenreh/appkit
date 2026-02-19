"""Consolidated assistant administration page with tabbed layout."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.components import file_manager, mcp_servers_table
from appkit_assistant.components.ai_model_table import ai_models_table
from appkit_assistant.components.skill_table import skills_table
from appkit_assistant.components.system_prompt_editor import system_prompt_editor
from appkit_assistant.roles import (
    ASSISTANT_ADMIN_ROLE,
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
    ASSISTANT_PERPLEXITY_MODEL_ROLE,
    ASSISTANT_USER_ROLE,
)
from appkit_assistant.state.file_manager_state import FileManagerState
from appkit_assistant.state.system_prompt_state import SystemPromptState
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import (
    requires_admin,
    requires_role,
)
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar
from app.roles import (
    ASSISTANT_ADMIN_SKILL_ROLE,
    MCP_ADVANCED_ROLE,
    MCP_BASIC_ROLE,
)

# Mapping from role name to display label
ROLE_LABELS: dict[str, str] = {
    ASSISTANT_USER_ROLE.name: ASSISTANT_USER_ROLE.label,
    ASSISTANT_BASIC_MODELS_ROLE.name: ASSISTANT_BASIC_MODELS_ROLE.label,
    ASSISTANT_ADVANCED_MODELS_ROLE.name: ASSISTANT_ADVANCED_MODELS_ROLE.label,
    ASSISTANT_PERPLEXITY_MODEL_ROLE.name: ASSISTANT_PERPLEXITY_MODEL_ROLE.label,
    MCP_BASIC_ROLE.name: MCP_BASIC_ROLE.label,
    MCP_ADVANCED_ROLE.name: MCP_ADVANCED_ROLE.label,
    ASSISTANT_ADMIN_ROLE.name: ASSISTANT_ADMIN_ROLE.label,
}

ASSISTANT_ROLES = [
    {"value": ASSISTANT_USER_ROLE.name, "label": ASSISTANT_USER_ROLE.label},
    {
        "value": ASSISTANT_BASIC_MODELS_ROLE.name,
        "label": ASSISTANT_BASIC_MODELS_ROLE.label,
    },
    {
        "value": ASSISTANT_ADVANCED_MODELS_ROLE.name,
        "label": ASSISTANT_ADVANCED_MODELS_ROLE.label,
    },
    {
        "value": ASSISTANT_PERPLEXITY_MODEL_ROLE.name,
        "label": ASSISTANT_PERPLEXITY_MODEL_ROLE.label,
    },
]

MCP_ROLES = [
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
        # "models" tab loads data via on_mount of the table component


@authenticated(
    route="/admin/assistant",
    title="Assistant Administration",
    navbar=app_navbar(),
    admin_only=True,
)
def admin_assistant_page() -> rx.Component:
    """Consolidated admin page for managing assistant configuration."""
    return requires_admin(
        mn.stack(
            header("Assistant Administration"),
            mn.tabs(
                mn.tabs.list(
                    mn.tabs.tab("MCP Server", value="mcp"),
                    mn.tabs.tab("Skills", value="skills"),
                    mn.tabs.tab("KI-Modelle", value="models"),
                    mn.tabs.tab("System Prompt", value="system_prompt"),
                    mn.tabs.tab("Dateimanager", value="file_manager"),
                    margin_bottom="1rem",
                ),
                mn.tabs.panel(
                    mcp_servers_table(
                        role_labels=ROLE_LABELS, available_roles=MCP_ROLES
                    ),
                    value="mcp",
                ),
                mn.tabs.panel(
                    requires_role(
                        skills_table(
                            role_labels=ROLE_LABELS,
                            available_roles=ASSISTANT_ROLES,
                        ),
                        role=ASSISTANT_ADMIN_SKILL_ROLE.name,
                    ),
                    value="skills",
                ),
                mn.tabs.panel(
                    requires_role(
                        ai_models_table(
                            role_labels=ROLE_LABELS,
                            available_roles=ASSISTANT_ROLES,
                        ),
                        role=ASSISTANT_ADMIN_ROLE.name,
                    ),
                    value="models",
                ),
                mn.tabs.panel(
                    system_prompt_editor(),
                    value="system_prompt",
                ),
                mn.tabs.panel(
                    file_manager(),
                    value="file_manager",
                ),
                default_value="mcp",
                on_change=AdminAssistantState.on_tab_change,
                w="100%",
                maw="1200px",
                mx="auto",
                gap="lg",
            ),
            w="100%",
            p="2rem",
        ),
    )

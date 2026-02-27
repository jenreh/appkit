"""MCP server tool selection mixin for ThreadState.

Handles loading, toggling, and applying MCP server selections.
"""

import logging

import reflex as rx

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.database.repositories import mcp_server_repo
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class McpToolsMixin:
    """Mixin for MCP server (tool) selection.

    Expects state vars: ``selected_mcp_servers``, ``show_tools_modal``,
    ``available_mcp_servers``, ``temp_selected_mcp_servers``,
    ``server_selection_state``.
    """

    @rx.event
    async def load_mcp_servers(self) -> None:
        """Load available active MCP servers filtered by user roles."""
        user_session = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        user_roles: list[str] = user.roles if user else []

        async with get_asyncdb_session() as session:
            servers = await mcp_server_repo.find_all_active_ordered_by_name(session)
            filtered_servers = [
                MCPServer(**s.model_dump())
                for s in servers
                if not s.required_role or s.required_role in user_roles
            ]
            self.available_mcp_servers = filtered_servers

    @rx.event
    def toggle_tools_modal(self, show: bool) -> None:
        """Set the visibility of the tools modal."""
        self.show_tools_modal = show

    @rx.event
    def toggle_mcp_server_selection(self, server_id: int, selected: bool) -> None:
        """Toggle MCP server selection in the modal."""
        self.server_selection_state[server_id] = selected
        if selected and server_id not in self.temp_selected_mcp_servers:
            self.temp_selected_mcp_servers.append(server_id)
        elif not selected and server_id in self.temp_selected_mcp_servers:
            self.temp_selected_mcp_servers.remove(server_id)

    @rx.event
    def apply_mcp_server_selection(self) -> None:
        """Apply the temporary MCP server selection."""
        self.selected_mcp_servers = [
            server
            for server in self.available_mcp_servers
            if server.id in self.temp_selected_mcp_servers
        ]
        self.show_tools_modal = False

    @rx.event
    def deselect_all_mcp_servers(self) -> None:
        """Deselect all MCP servers in the modal."""
        self.server_selection_state = {}
        self.temp_selected_mcp_servers = []

    @rx.event
    def is_mcp_server_selected(self, server_id: int) -> bool:
        """Check if an MCP server is selected."""
        return server_id in self.temp_selected_mcp_servers

    def _restore_mcp_selection(self, server_ids: list[int]) -> None:
        """Restore MCP selection state from a list of server IDs."""
        if not server_ids:
            self.selected_mcp_servers = []
            self.temp_selected_mcp_servers = []
            self.server_selection_state = {}
            return

        self.selected_mcp_servers = [
            server for server in self.available_mcp_servers if server.id in server_ids
        ]
        self.temp_selected_mcp_servers = list(server_ids)
        self.server_selection_state = dict.fromkeys(server_ids, True)

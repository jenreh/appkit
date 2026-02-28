"""MCP Apps state mixin for ThreadState.

Manages MCP App views in the conversation: tracking active views,
caching the UI tool registry, and handling app-originated events.
"""

import logging
from typing import Any

from appkit_assistant.backend.schemas import McpAppToolInfo, McpAppViewData

logger = logging.getLogger(__name__)


class McpAppsMixin:
    """Mixin for MCP Apps state management.

    Expects state vars: ``mcp_app_views``, ``_ui_tool_registry``.
    """

    def _handle_mcp_app_view(self, view_data: McpAppViewData) -> None:
        """Add an MCP App view to the current conversation.

        Args:
            view_data: The MCP App view data to add
        """
        self.mcp_app_views.append(view_data)
        logger.debug(
            "Added MCP App view: tool=%s, server=%s",
            view_data.tool_name,
            view_data.server_name,
        )

    def _update_ui_tool_registry(
        self,
        tools: list[McpAppToolInfo],
    ) -> None:
        """Update the UI tool registry from discovered tools.

        Args:
            tools: List of UI-enabled tool metadata
        """
        for tool in tools:
            self._ui_tool_registry[tool.tool_name] = tool.model_dump()

    def _get_ui_tool_info(
        self,
        tool_name: str,
    ) -> dict[str, Any] | None:
        """Look up UI tool info from the registry.

        Args:
            tool_name: The tool name to look up

        Returns:
            Tool info dict or None if not found
        """
        return self._ui_tool_registry.get(tool_name)

    def _clear_mcp_app_state(self) -> None:
        """Clear MCP App views and UI tool registry."""
        self.mcp_app_views = []
        self._ui_tool_registry = {}

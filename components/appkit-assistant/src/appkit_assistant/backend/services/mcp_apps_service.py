"""MCP Apps Service for direct MCP client communication.

Provides a parallel direct MCP client connection to MCP servers,
alongside the existing LLM-provider-mediated path. The direct client
negotiates the io.modelcontextprotocol/ui extension, discovers
UI-enabled tools, fetches ui:// HTML resources, and proxies tool
calls from app iframes.
"""

import logging
import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, Tool

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.schemas import (
    McpAppResource,
    McpAppToolInfo,
    MCPAuthType,
)
from appkit_assistant.backend.services.mcp_token_service import (
    MCPTokenService,
)

logger = logging.getLogger(__name__)

# Default TTL for cached sessions and tool metadata (seconds)
_SESSION_TTL_S = 300  # 5 minutes
_TOOL_CACHE_TTL_S = 300


class McpAppsService:
    """Service for direct MCP client communication with App support.

    Manages MCP client sessions, discovers UI-enabled tools,
    fetches resources, and proxies tool calls for MCP Apps.
    """

    def __init__(
        self,
        token_service: MCPTokenService | None = None,
    ) -> None:
        self._token_service = token_service
        # Cache: (server_id, user_id) -> (tools, timestamp)
        self._tool_cache: dict[tuple[int, int], tuple[list[McpAppToolInfo], float]] = {}
        # Cache: (server_id, user_id) -> (supports_apps, timestamp)
        self._apps_support_cache: dict[tuple[int, int], tuple[bool, float]] = {}

    async def _get_auth_headers(
        self,
        server: MCPServer,
        user_id: int,
    ) -> dict[str, str]:
        """Build authorization headers for a server request.

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Returns:
            Dictionary of HTTP headers including auth if available
        """
        headers: dict[str, str] = {}

        if server.auth_type == MCPAuthType.OAUTH_DISCOVERY and self._token_service:
            token = await self._token_service.get_valid_token(server, user_id)
            if token:
                headers["Authorization"] = f"Bearer {token.access_token}"
                logger.debug(
                    "Injected OAuth token for MCP Apps server %s",
                    server.name,
                )

        return headers

    async def discover_ui_tools(
        self,
        server: MCPServer,
        user_id: int,
    ) -> list[McpAppToolInfo]:
        """Discover tools with UI (App) views on an MCP server.

        Calls tools/list through a direct MCP client and filters for
        tools with ``_meta.ui.resourceUri`` metadata.

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Returns:
            List of UI-enabled tool metadata
        """
        if server.id is None:
            return []

        cache_key = (server.id, user_id)
        cached = self._tool_cache.get(cache_key)
        if cached:
            tools, ts = cached
            if (time.monotonic() - ts) < _TOOL_CACHE_TTL_S:
                return tools

        try:
            headers = await self._get_auth_headers(server, user_id)
            ui_tools = await self._fetch_ui_tools(server, headers)
            self._tool_cache[cache_key] = (ui_tools, time.monotonic())
            logger.info(
                "Discovered %d UI tools on server %s",
                len(ui_tools),
                server.name,
            )
            return ui_tools
        except Exception:
            logger.exception(
                "Failed to discover UI tools on server %s",
                server.name,
            )
            return []

    async def _fetch_ui_tools(
        self,
        server: MCPServer,
        headers: dict[str, str],
    ) -> list[McpAppToolInfo]:
        """Fetch and filter UI-enabled tools from an MCP server.

        Args:
            server: The MCP server configuration
            headers: HTTP headers for the request

        Returns:
            List of UI-enabled tool metadata
        """
        ui_tools: list[McpAppToolInfo] = []

        async with (
            streamablehttp_client(server.url, headers=headers) as (
                read_stream,
                write_stream,
                _,
            ),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.list_tools()

            for tool in result.tools:
                tool_info = self._extract_ui_tool_info(tool, server)
                if tool_info:
                    ui_tools.append(tool_info)

        return ui_tools

    def _extract_ui_tool_info(
        self,
        tool: Tool,
        server: MCPServer,
    ) -> McpAppToolInfo | None:
        """Extract UI tool info from an MCP Tool definition.

        Args:
            tool: The MCP Tool definition
            server: The MCP server configuration

        Returns:
            McpAppToolInfo if the tool has UI metadata, None otherwise
        """
        meta = getattr(tool, "meta", None) or {}
        ui_meta: dict[str, Any] = meta.get("ui", {}) if meta else {}
        resource_uri = ui_meta.get("resourceUri")

        if not resource_uri:
            return None

        visibility = ui_meta.get("visibility", [])

        return McpAppToolInfo(
            tool_name=tool.name,
            resource_uri=resource_uri,
            visibility=visibility,
            server_id=server.id or 0,
            server_label=server.name,
            input_schema=(tool.inputSchema if tool.inputSchema else {}),
        )

    async def fetch_resource(
        self,
        server: MCPServer,
        user_id: int,
        resource_uri: str,
    ) -> McpAppResource | None:
        """Fetch an MCP App resource (HTML content) from a server.

        Args:
            server: The MCP server configuration
            user_id: The user's ID
            resource_uri: The ui:// URI to fetch

        Returns:
            McpAppResource with HTML content or None on failure
        """
        try:
            headers = await self._get_auth_headers(server, user_id)

            async with (
                streamablehttp_client(server.url, headers=headers) as (
                    read_stream,
                    write_stream,
                    _,
                ),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                result = await session.read_resource(resource_uri)

                html_content = ""
                for content in result.contents:
                    if hasattr(content, "text"):
                        html_content += content.text

                return McpAppResource(
                    uri=resource_uri,
                    html_content=html_content,
                )
        except Exception:
            logger.exception(
                "Failed to fetch resource %s from server %s",
                resource_uri,
                server.name,
            )
            return None

    async def proxy_tool_call(
        self,
        server: MCPServer,
        user_id: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Proxy a tool call from an MCP App iframe to the server.

        Args:
            server: The MCP server configuration
            user_id: The user's ID
            tool_name: Name of the tool to call
            arguments: Tool call arguments

        Returns:
            The tool call result as a dictionary
        """
        logger.info(
            "Proxying tool call %s to server %s for user %d",
            tool_name,
            server.name,
            user_id,
        )

        try:
            headers = await self._get_auth_headers(server, user_id)

            async with (
                streamablehttp_client(server.url, headers=headers) as (
                    read_stream,
                    write_stream,
                    _,
                ),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                result: CallToolResult = await session.call_tool(tool_name, arguments)

                return _call_tool_result_to_dict(result)
        except Exception:
            logger.exception(
                "Failed to proxy tool call %s to server %s",
                tool_name,
                server.name,
            )
            return {"isError": True, "content": []}

    async def is_apps_supported(
        self,
        server: MCPServer,
        user_id: int,
    ) -> bool:
        """Check if the server supports MCP Apps (has UI-enabled tools).

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Returns:
            True if the server has UI-enabled tools
        """
        if server.id is None:
            return False

        cache_key = (server.id, user_id)
        cached = self._apps_support_cache.get(cache_key)
        if cached:
            supported, ts = cached
            if (time.monotonic() - ts) < _TOOL_CACHE_TTL_S:
                return supported

        tools = await self.discover_ui_tools(server, user_id)
        supported = len(tools) > 0
        self._apps_support_cache[cache_key] = (
            supported,
            time.monotonic(),
        )
        return supported

    def get_cached_ui_tools(
        self,
        server_id: int,
        user_id: int,
    ) -> list[McpAppToolInfo]:
        """Get cached UI tools without making a network request.

        Args:
            server_id: The MCP server ID
            user_id: The user's ID

        Returns:
            Cached list of UI tools, or empty list if not cached
        """
        cache_key = (server_id, user_id)
        cached = self._tool_cache.get(cache_key)
        if cached:
            tools, ts = cached
            if (time.monotonic() - ts) < _TOOL_CACHE_TTL_S:
                return tools
        return []

    def build_ui_tool_registry(
        self,
        tools: list[McpAppToolInfo],
    ) -> dict[str, McpAppToolInfo]:
        """Build a tool name → McpAppToolInfo mapping.

        Args:
            tools: List of UI tool metadata

        Returns:
            Dictionary mapping tool names to their metadata
        """
        return {tool.tool_name: tool for tool in tools}


def _call_tool_result_to_dict(result: CallToolResult) -> dict[str, Any]:
    """Convert a CallToolResult to a serializable dictionary."""
    content_list = [item.model_dump() for item in result.content]

    return {
        "isError": bool(result.isError),
        "content": content_list,
    }

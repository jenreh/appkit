"""MCP Apps Service for direct MCP client communication.

Provides a parallel direct MCP client connection to MCP servers,
alongside the existing LLM-provider-mediated path. The direct client
negotiates the io.modelcontextprotocol/ui extension (SEP-1865 §Capability
Negotiation), discovers UI-enabled tools, fetches ui:// HTML resources,
and proxies tool calls from app iframes.
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp import ClientSession  # noqa: F401 - kept for re-export / type hints
from mcp import types as t
from mcp.client.streamable_http import streamable_http_client
from mcp.types import (
    CallToolResult,
    ClientCapabilities,
    Implementation,
    InitializeResult,
    Tool,
)

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

# Default TTL for cached tool metadata (seconds)
_TOOL_CACHE_TTL_S = 300

# Extension identifier per SEP-1865
_EXTENSION_ID = "io.modelcontextprotocol/ui"
_SUPPORTED_MIME_TYPE = "text/html;profile=mcp-app"

# Client info sent to MCP servers
_CLIENT_INFO = Implementation(name="appkit", version="1.0.0")


class _McpAppsClientSession(ClientSession):
    """ClientSession with MCP Apps capability advertised.

    Overrides `initialize()` to include the ``io.modelcontextprotocol/ui``
    extension in the ``experimental`` field of ``ClientCapabilities``.
    This signals to the MCP server that this host supports MCP Apps,
    so the server can register UI-enabled tools (spec §Capability Negotiation).
    """

    async def initialize(self) -> InitializeResult:
        result = await self.send_request(
            t.ClientRequest(
                t.InitializeRequest(
                    params=t.InitializeRequestParams(
                        protocolVersion=t.LATEST_PROTOCOL_VERSION,
                        capabilities=ClientCapabilities(
                            experimental={
                                "extensions": {
                                    _EXTENSION_ID: {
                                        "mimeTypes": [_SUPPORTED_MIME_TYPE],
                                    }
                                }
                            },
                        ),
                        clientInfo=_CLIENT_INFO,
                    ),
                )
            ),
            t.InitializeResult,
        )
        self._server_capabilities = result.capabilities  # type: ignore[attr-defined]
        await self.send_notification(t.ClientNotification(t.InitializedNotification()))
        logger.debug(
            "MCP Apps session initialized (protocolVersion=%s)",
            result.protocolVersion,
        )
        return result


class McpAppsService:
    """Service for direct MCP client communication with App support.

    Manages MCP client sessions, discovers UI-enabled tools,
    fetches resources, and proxies tool calls for MCP Apps.
    """

    def __init__(self, token_service: MCPTokenService | None = None) -> None:
        self._token_service = token_service
        # Cache for tools: (server_id, user_id) -> (tools, timestamp)
        self._tool_cache: dict[tuple[int, int], tuple[list[McpAppToolInfo], float]] = {}

    @asynccontextmanager
    async def _connect_for_apps(self, server: MCPServer, user_id: int):
        """Create an authenticated MCP Apps client session context.

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Yields:
            An initialized _McpAppsClientSession
        """
        headers = await self._get_auth_headers(server, user_id)
        async with (
            httpx.AsyncClient(headers=headers) as http_client,
            streamable_http_client(server.url, http_client=http_client) as (
                read_stream,
                write_stream,
                _,
            ),
            # Use _McpAppsClientSession to advertise io.modelcontextprotocol/ui
            _McpAppsClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            yield session

    def _get_cached_tools(
        self,
        key: tuple[int, int],
    ) -> list[McpAppToolInfo] | None:
        """Retrieve cached UI tools if valid."""
        if cached := self._tool_cache.get(key):
            tools, ts = cached
            if (time.monotonic() - ts) < _TOOL_CACHE_TTL_S:
                return tools
        return None

    async def _get_auth_headers(
        self,
        server: MCPServer,
        user_id: int,
    ) -> dict[str, str]:
        """Build authorization headers for a server request."""
        headers: dict[str, str] = {}

        # Parse custom headers from server configuration (API_KEY etc.)
        if server.headers:
            try:
                headers_dict = json.loads(server.headers)
                if isinstance(headers_dict, dict):
                    headers.update(headers_dict)
            except json.JSONDecodeError:
                logger.warning("Invalid headers JSON for server %s", server.name)

        # Override with OAuth token if available
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
        """Discover tools with UI (App) views on an MCP server."""
        if server.id is None:
            return []

        cache_key = (server.id, user_id)
        if tools := self._get_cached_tools(cache_key):
            return tools

        try:
            async with self._connect_for_apps(server, user_id) as session:
                ui_tools = await self._list_ui_tools(session, server)

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

    async def _list_ui_tools(
        self,
        session: ClientSession,
        server: MCPServer,
    ) -> list[McpAppToolInfo]:
        """Fetch and filter UI-enabled tools from an active session."""
        result = await session.list_tools()

        return [
            info
            for tool in result.tools
            if (info := self._extract_ui_tool_info(tool, server))
        ]

    def _extract_ui_tool_info(
        self,
        tool: Tool,
        server: MCPServer,
    ) -> McpAppToolInfo | None:
        """Extract UI tool info from an MCP Tool definition."""
        meta = getattr(tool, "meta", None) or {}
        ui_meta: dict[str, Any] = meta.get("ui", {}) if meta else {}
        resource_uri = ui_meta.get("resourceUri")

        if not resource_uri:
            return None

        return McpAppToolInfo(
            tool_name=tool.name,
            resource_uri=resource_uri,
            visibility=ui_meta.get("visibility", []),
            server_id=server.id or 0,
            server_label=server.name,
            input_schema=(tool.inputSchema or {}),
        )

    async def fetch_resource(
        self,
        server: MCPServer,
        user_id: int,
        resource_uri: str,
    ) -> McpAppResource | None:
        """Fetch an MCP App resource (HTML content) from a server."""
        try:
            async with self._connect_for_apps(server, user_id) as session:
                result = await session.read_resource(resource_uri)

            html_content = ""
            csp: dict[str, Any] | None = None
            permissions: dict[str, bool] | None = None
            prefers_border: bool | None = None

            for content in result.contents:
                if hasattr(content, "text"):
                    html_content += content.text

                # Extract _meta.ui fields from resource content
                raw_meta: dict[str, Any] = getattr(content, "_meta", None) or {}
                if ui_meta := raw_meta.get("ui", {}):
                    csp = ui_meta.get("csp", csp)
                    permissions = ui_meta.get("permissions", permissions)
                    if "prefersBorder" in ui_meta:
                        prefers_border = bool(ui_meta["prefersBorder"])

            return McpAppResource(
                uri=resource_uri,
                html_content=html_content,
                csp=csp,
                permissions=permissions,
                prefers_border=prefers_border,
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
        """Proxy a tool call from an MCP App iframe to the server."""
        logger.info(
            "Proxying tool call %s to server %s for user %d",
            tool_name,
            server.name,
            user_id,
        )

        try:
            async with self._connect_for_apps(server, user_id) as session:
                result: CallToolResult = await session.call_tool(tool_name, arguments)

            # Note: CallToolResult needs standardizing to dict
            # We use the existing function outside the class or standard extraction
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
        """Check if the server supports MCP Apps (has UI-enabled tools)."""
        if server.id is None:
            return False

        # Reuse discovery logic which handles caching.
        # We removed _apps_support_cache as it was redundant with _tool_cache
        tools = await self.discover_ui_tools(server, user_id)
        return len(tools) > 0

    def get_cached_ui_tools(
        self,
        server_id: int,
        user_id: int,
    ) -> list[McpAppToolInfo]:
        """Get cached UI tools without making a network request."""
        return self._get_cached_tools((server_id, user_id)) or []

    def build_ui_tool_registry(
        self,
        tools: list[McpAppToolInfo],
    ) -> dict[str, McpAppToolInfo]:
        """Build a tool name → McpAppToolInfo mapping."""
        return {tool.tool_name: tool for tool in tools}


def _call_tool_result_to_dict(result: CallToolResult) -> dict[str, Any]:
    """Convert a CallToolResult to a serializable dictionary."""
    content_list = [item.model_dump(exclude_none=True) for item in result.content]

    return {
        "isError": bool(result.isError),
        "content": content_list,
    }

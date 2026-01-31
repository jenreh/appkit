"""MCP Capabilities Mixin for processors.

Provides MCP (Model Context Protocol) authentication and tool configuration
capabilities that can be composed with processor classes.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from appkit_assistant.backend.database.models import (
    AssistantMCPUserToken,
    MCPServer,
)
from appkit_assistant.backend.processors.processor_base import mcp_oauth_redirect_uri
from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
    MCPAuthType,
)
from appkit_assistant.backend.services.mcp_auth_service import MCPAuthService
from appkit_assistant.backend.services.mcp_token_service import MCPTokenService
from appkit_commons.database.session import get_session_manager

logger = logging.getLogger(__name__)


class MCPCapabilities:
    """Mixin providing MCP authentication and tool configuration.

    Add this to a processor class to enable MCP server support with:
    - OAuth token management
    - Auth-required chunk creation
    - Header parsing
    - Server configuration

    Usage:
        class MyProcessor(StreamingProcessorBase, MCPCapabilities):
            def __init__(self, ...):
                StreamingProcessorBase.__init__(self, ...)
                MCPCapabilities.__init__(self, oauth_redirect_uri, processor_name)
    """

    def __init__(
        self,
        oauth_redirect_uri: str | None = None,
        processor_name: str = "unknown",
    ) -> None:
        """Initialize MCP capabilities.

        Args:
            oauth_redirect_uri: OAuth redirect URI for MCP servers
            processor_name: Name for chunk metadata and logging
        """
        redirect_uri = oauth_redirect_uri or mcp_oauth_redirect_uri()
        self._mcp_auth_service = MCPAuthService(redirect_uri=redirect_uri)
        self._mcp_token_service = MCPTokenService(self._mcp_auth_service)
        self._pending_auth_servers: list[MCPServer] = []
        self._mcp_processor_name = processor_name
        self._mcp_current_user_id: int | None = None

        logger.debug("Using redirect URI for MCP OAuth: %s", redirect_uri)

    @property
    def mcp_processor_name(self) -> str:
        """Get the processor name for MCP operations."""
        return self._mcp_processor_name

    @property
    def current_user_id(self) -> int | None:
        """Get the current user ID."""
        return self._mcp_current_user_id

    @current_user_id.setter
    def current_user_id(self, value: int | None) -> None:
        """Set the current user ID."""
        self._mcp_current_user_id = value

    @property
    def mcp_auth_service(self) -> MCPAuthService:
        """Get the MCP auth service."""
        return self._mcp_auth_service

    @property
    def mcp_token_service(self) -> MCPTokenService:
        """Get the MCP token service."""
        return self._mcp_token_service

    @property
    def pending_auth_servers(self) -> list[MCPServer]:
        """Get the list of servers pending authentication."""
        return self._pending_auth_servers

    def clear_pending_auth_servers(self) -> None:
        """Clear the pending auth servers list."""
        self._pending_auth_servers = []

    def add_pending_auth_server(self, server: MCPServer) -> None:
        """Add a server to the pending auth list.

        Args:
            server: The MCP server requiring authentication
        """
        if server not in self._pending_auth_servers:
            self._pending_auth_servers.append(server)

    async def get_valid_token(
        self,
        server: MCPServer,
        user_id: int,
    ) -> AssistantMCPUserToken | None:
        """Get a valid OAuth token for a server.

        Args:
            server: The MCP server
            user_id: The user's ID

        Returns:
            A valid token or None
        """
        return await self._mcp_token_service.get_valid_token(server, user_id)

    def parse_mcp_headers(self, server: MCPServer) -> dict[str, str]:
        """Parse headers from server configuration.

        Args:
            server: The MCP server configuration

        Returns:
            Dictionary of HTTP headers
        """
        if not server.headers or server.headers == "{}":
            return {}

        try:
            headers_dict = json.loads(server.headers)
            return dict(headers_dict)
        except json.JSONDecodeError:
            logger.warning("Invalid headers JSON for server %s", server.name)
            return {}

    def parse_mcp_headers_with_auth(
        self,
        server: MCPServer,
    ) -> tuple[dict[str, str], str | None]:
        """Parse headers and extract auth token separately.

        Used by Claude which sends auth token separately from headers.

        Args:
            server: The MCP server configuration

        Returns:
            Tuple of (headers_without_auth, auth_token)
        """
        headers = self.parse_mcp_headers(server)
        auth_token: str | None = None

        # Extract Bearer token from Authorization header
        auth_header = headers.pop("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]  # Remove "Bearer " prefix
        elif auth_header:
            auth_token = auth_header

        return headers, auth_token

    async def create_auth_required_chunk(
        self,
        server: MCPServer,
        user_id: int | None = None,
        processor_name: str | None = None,
    ) -> Chunk:
        """Create an AUTH_REQUIRED chunk for a server.

        Builds the authorization URL and returns a chunk that signals
        the UI to show an authentication dialog.

        Args:
            server: The MCP server requiring authentication
            user_id: The current user's ID (uses internal state if None)
            processor_name: Name of the processor (uses internal state if None)

        Returns:
            An AUTH_REQUIRED Chunk with auth URL
        """
        effective_user_id = (
            user_id if user_id is not None else self._mcp_current_user_id
        )
        effective_processor = processor_name or self._mcp_processor_name
        auth_url = ""
        state = ""

        try:
            with get_session_manager().session() as session:
                auth_service = self._mcp_auth_service
                (
                    auth_url,
                    state,
                ) = await auth_service.build_authorization_url_with_registration(
                    server,
                    session=session,
                    user_id=effective_user_id,
                )
                logger.info(
                    "Built auth URL for server %s, state=%s, url=%s",
                    server.name,
                    state,
                    auth_url[:100] if auth_url else "None",
                )
        except Exception as e:
            logger.error("Cannot build auth URL for server %s: %s", server.name, str(e))

        return Chunk(
            type=ChunkType.AUTH_REQUIRED,
            text=f"{server.name} benötigt Ihre Autorisierung",
            chunk_metadata={
                "server_id": str(server.id) if server.id else "",
                "server_name": server.name,
                "auth_url": auth_url,
                "state": state,
                "processor": effective_processor,
            },
        )

    async def yield_pending_auth_chunks(
        self,
    ) -> AsyncGenerator[Chunk, None]:
        """Yield auth chunks for all pending servers.

        Generator that yields AUTH_REQUIRED chunks for each server
        that needs authentication. Uses internal current_user_id and
        mcp_processor_name state.

        Yields:
            AUTH_REQUIRED Chunk for each pending server
        """
        logger.debug(
            "Processing pending auth servers: %d", len(self._pending_auth_servers)
        )
        for server in self._pending_auth_servers:
            logger.debug("Yielding auth chunk for server: %s", server.name)
            yield await self.create_auth_required_chunk(server)

    async def configure_mcp_servers_with_tokens(
        self,
        servers: list[MCPServer] | None,
        user_id: int | None,
    ) -> tuple[list[dict[str, Any]], str]:
        """Configure MCP servers with OAuth tokens.

        For each server:
        1. Parse headers
        2. If OAuth required, inject token or mark for auth

        Args:
            servers: List of MCP server configurations
            user_id: The current user's ID

        Returns:
            Tuple of (server_configs, mcp_prompt)
        """
        if not servers:
            return [], ""

        server_configs = []
        prompts = []

        for server in servers:
            headers = self.parse_mcp_headers(server)

            # Handle OAuth servers
            if server.auth_type == MCPAuthType.OAUTH_DISCOVERY and user_id is not None:
                token = await self.get_valid_token(server, user_id)
                if token:
                    headers["Authorization"] = f"Bearer {token.access_token}"
                    logger.debug("Injected OAuth token for server %s", server.name)
                else:
                    self.add_pending_auth_server(server)
                    logger.debug(
                        "No valid token for OAuth server %s, auth may be required",
                        server.name,
                    )

            server_configs.append(
                {
                    "name": server.name,
                    "url": server.url,
                    "headers": headers,
                }
            )

            if server.prompt:
                prompts.append(f"- {server.prompt}")

        return server_configs, "\n".join(prompts) if prompts else ""

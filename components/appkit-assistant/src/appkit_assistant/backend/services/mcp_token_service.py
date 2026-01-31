"""MCP Token Service for OAuth token management.

Provides unified token retrieval and validation for MCP servers
across all AI processors.
"""

import logging

import reflex as rx

from appkit_assistant.backend.database.models import AssistantMCPUserToken, MCPServer
from appkit_assistant.backend.services.mcp_auth_service import MCPAuthService

logger = logging.getLogger(__name__)


class MCPTokenService:
    """Service for managing MCP OAuth tokens."""

    def __init__(self, mcp_auth_service: MCPAuthService) -> None:
        """Initialize the token service.

        Args:
            mcp_auth_service: The MCP auth service for token operations
        """
        self._mcp_auth_service = mcp_auth_service

    async def get_valid_token(
        self,
        server: MCPServer,
        user_id: int,
    ) -> AssistantMCPUserToken | None:
        """Get a valid OAuth token for the given server and user.

        Retrieves the stored token and refreshes it if expired
        (when a refresh token is available).

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Returns:
            A valid token or None if not available
        """
        if server.id is None:
            logger.debug("Server %s has no ID, cannot retrieve token", server.name)
            return None

        with rx.session() as session:
            token = self._mcp_auth_service.get_user_token(session, user_id, server.id)

            if token is None:
                logger.debug(
                    "No token found for user %d on server %s", user_id, server.name
                )
                return None

            # Check if token is valid or can be refreshed
            return await self._mcp_auth_service.ensure_valid_token(
                session, server, token
            )

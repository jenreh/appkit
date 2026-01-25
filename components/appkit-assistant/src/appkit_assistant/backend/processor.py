"""
Base processor interface for AI processing services.
"""

import abc
import asyncio
import logging
from collections.abc import AsyncGenerator

from appkit_assistant.backend.models import AIModel, Chunk, MCPServer, Message
from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)

# OAuth callback path - must match registered redirect URIs
MCP_OAUTH_CALLBACK_PATH = "/assistant/mcp/callback"


def mcp_oauth_redirect_uri() -> str:
    """Build the MCP OAuth redirect URI from configuration."""
    reflex_config: ReflexConfig | None = service_registry().get(ReflexConfig)
    if reflex_config:
        base_url = reflex_config.deploy_url
        port = reflex_config.frontend_port
        # Only add port if not standard (80 for http, 443 for https)
        if port and port not in (80, 443):
            return f"{base_url}:{port}{MCP_OAUTH_CALLBACK_PATH}"
        return f"{base_url}{MCP_OAUTH_CALLBACK_PATH}"
    # Fallback for development
    return f"http://localhost:8080{MCP_OAUTH_CALLBACK_PATH}"


class Processor(abc.ABC):
    """Base processor interface for AI processing services."""

    @abc.abstractmethod
    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """
        Process the thread using an AI model.

        Args:
            messages: The list of messages to process.
            model_id: The ID of the model to use.
            files: Optional list of file paths that were uploaded.
            mcp_servers: Optional list of MCP servers to use as tools.
            cancellation_token: Optional event to signal cancellation.

        Returns:
            An async generator that yields Chunk objects containing different content
            types.
        """

    @abc.abstractmethod
    def get_supported_models(self) -> dict[str, AIModel]:
        """
        Get a dictionary of models supported by this processor.

        Returns:
            Dictionary mapping model IDs to AIModel objects.
        """

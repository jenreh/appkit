"""
Base processor interface for AI processing services.
"""

import abc
import asyncio
import contextvars
import logging
from collections.abc import AsyncGenerator

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    Message,
    ProcessingStatistics,
)
from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)

# Context variable for request-scoped statistics
statistics_ctx: contextvars.ContextVar[ProcessingStatistics | None] = (
    contextvars.ContextVar("statistics", default=None)
)

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


class ProcessorBase(abc.ABC):
    """Base processor interface for AI processing services."""

    def __init__(self, processor_name: str | None = None) -> None:
        """Initialize the processor."""
        self._processor_name = processor_name or self.__class__.__name__

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

    def _reset_statistics(self, model_id: str) -> None:
        """Reset statistics for a new request."""
        stats = ProcessingStatistics(
            model=model_id,
            processor=self._processor_name,
        )
        statistics_ctx.set(stats)

    def _get_statistics(self) -> ProcessingStatistics | None:
        """Get the current statistics object."""
        return statistics_ctx.get()

    def _update_statistics(
        self,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tool_use: tuple[str, str | None] | None = None,
    ) -> None:
        """Update processing statistics.

        Args:
            input_tokens: Number of input tokens to set.
            output_tokens: Number of output tokens to set.
            tool_use: Tuple of (tool_name, server_label) to increment usage.
        """
        stats = statistics_ctx.get()
        if not stats:
            return

        if input_tokens is not None:
            stats.input_tokens = input_tokens
        if output_tokens is not None:
            stats.output_tokens = output_tokens

        if tool_use:
            tool_name, server_label = tool_use
            key = f"{server_label}.{tool_name}" if server_label else tool_name
            stats.tool_uses[key] = stats.tool_uses.get(key, 0) + 1

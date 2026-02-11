"""Streaming Processor Base class.

Provides a unified base class for all streaming AI processors with:
- Standardized dict-based event dispatch
- Cancellation token handling
- Common state management
- Composed service dependencies
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from appkit_assistant.backend.database.models import (
    MCPServer,
)
from appkit_assistant.backend.processors.processor_base import ProcessorBase
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    ChunkType,
    Message,
)
from appkit_assistant.backend.services.auth_error_detector import AuthErrorDetector
from appkit_assistant.backend.services.chunk_factory import ChunkFactory

logger = logging.getLogger(__name__)


class StreamingProcessorBase(ProcessorBase, ABC):
    """Base class for streaming AI processors.

    Provides common functionality for:
    - Event dispatch via dict-based handlers
    - Cancellation token checking
    - Common state tracking (reasoning sessions)
    - Chunk creation via ChunkFactory
    - Error detection via AuthErrorDetector

    Note: For user ID tracking and MCP capabilities, combine with MCPCapabilities mixin.

    Subclasses must implement:
    - _get_event_handlers(): Return dict mapping event types to handlers
    - get_supported_models(): Return supported models
    """

    def __init__(
        self,
        models: dict[str, AIModel],
        processor_name: str,
    ) -> None:
        """Initialize the streaming processor base.

        Args:
            models: Dictionary of supported AI models
            processor_name: Name for chunk metadata (e.g., "claude_responses")
        """
        super().__init__(processor_name=processor_name)
        self.models = models
        self._chunk_factory = ChunkFactory(processor_name)
        self._auth_detector = AuthErrorDetector()

        # Common streaming state
        self._current_reasoning_session: str | None = None

    @property
    def chunk_factory(self) -> ChunkFactory:
        """Get the chunk factory instance."""
        return self._chunk_factory

    @property
    def auth_detector(self) -> AuthErrorDetector:
        """Get the auth error detector instance."""
        return self._auth_detector

    @property
    def current_reasoning_session(self) -> str | None:
        """Get the current reasoning session ID."""
        return self._current_reasoning_session

    @current_reasoning_session.setter
    def current_reasoning_session(self, value: str | None) -> None:
        """Set the current reasoning session ID."""
        self._current_reasoning_session = value

    def get_supported_models(self) -> dict[str, AIModel]:
        """Return supported models."""
        return self.models

    @abstractmethod
    def _get_event_handlers(self) -> dict[str, Any]:
        """Get the event handler mapping.

        Returns:
            Dict mapping event type strings to handler methods.
            Handler methods should accept the event and return Chunk | None.
        """

    def _handle_event(self, event: Any) -> Chunk | None:
        """Handle a streaming event using dict-based dispatch.

        Args:
            event: The event object from the API stream

        Returns:
            A Chunk if the event produced content, None otherwise
        """
        event_type = getattr(event, "type", None)
        if not event_type:
            return None

        handlers = self._get_event_handlers()
        handler = handlers.get(event_type)

        if handler:
            return handler(event)

        logger.debug("Unhandled event type: %s", event_type)
        return None

    async def _process_stream_with_cancellation(
        self,
        stream: Any,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process a stream with cancellation support.

        Args:
            stream: Async iterable stream of events
            cancellation_token: Optional event to signal cancellation

        Yields:
            Chunk objects from handled events
        """
        try:
            async for event in stream:
                if cancellation_token and cancellation_token.is_set():
                    logger.info("Processing cancelled by user")
                    break

                chunk = self._handle_event(event)
                if chunk:
                    yield chunk
        except Exception as e:
            error_msg = str(e)
            logger.error("Error during stream processing: %s", error_msg)

            # Only yield error chunk if NOT an auth error
            if not self._auth_detector.is_auth_error(error_msg):
                yield self._chunk_factory.error(
                    f"Ein Fehler ist aufgetreten: {error_msg}",
                    error_type=type(e).__name__,
                )

    def _create_chunk(
        self,
        chunk_type: ChunkType,
        content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a chunk using the factory (convenience method).

        Args:
            chunk_type: The type of chunk
            content: The text content
            extra_metadata: Additional metadata

        Returns:
            A Chunk instance
        """
        return self._chunk_factory.create(chunk_type, content, extra_metadata)

    @abstractmethod
    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages and generate response chunks.

        Must be implemented by subclasses to handle vendor-specific API calls.
        """

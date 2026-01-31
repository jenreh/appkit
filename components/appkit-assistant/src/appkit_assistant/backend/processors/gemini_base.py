"""
Gemini base processor for generating AI responses using Google's GenAI API.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Final

from google import genai

from appkit_assistant.backend.models import (
    AIModel,
    Chunk,
    MCPServer,
    Message,
)
from appkit_assistant.backend.processor import Processor

logger = logging.getLogger(__name__)

GEMINI_3_PRO: Final = AIModel(
    id="gemini-3-pro-preview",
    text="Gemini 3 Pro",
    icon="googlegemini",
    model="gemini-3-pro-preview",
    stream=True,
    supports_attachments=False,  # Deferred to Phase 2
    supports_tools=True,
)

GEMINI_3_FLASH: Final = AIModel(
    id="gemini-3-flash-preview",
    text="Gemini 3 Flash",
    icon="googlegemini",
    model="gemini-3-flash-preview",
    stream=True,
    supports_attachments=False,  # Deferred to Phase 2
    supports_tools=True,
)


class BaseGeminiProcessor(Processor, ABC):
    """Base class for Gemini processors with common initialization and utilities."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
    ) -> None:
        """Initialize the base Gemini processor.

        Args:
            models: Dictionary of supported AI models
            api_key: Google GenAI API key
        """
        self.models = models
        self.client: genai.Client | None = None

        if api_key:
            try:
                self.client = genai.Client(
                    api_key=api_key, http_options={"api_version": "v1beta"}
                )
            except Exception as e:
                logger.error("Failed to initialize Gemini client: %s", e)
        else:
            logger.warning("Gemini API key not found. Processor disabled.")

    def get_supported_models(self) -> dict[str, AIModel]:
        """Get supported models."""
        return self.models

    @abstractmethod
    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages."""

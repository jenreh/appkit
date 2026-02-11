"""
OpenAI processor for generating AI responses using OpenAI's API.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from appkit_assistant.backend.database.models import (
    MCPServer,
)
from appkit_assistant.backend.processors.processor_base import ProcessorBase
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    Message,
)

logger = logging.getLogger(__name__)


class BaseOpenAIProcessor(ProcessorBase, ABC):
    """Base class for OpenAI processors with common initialization and utilities."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
        is_azure: bool = False,
        processor_name: str | None = None,
    ) -> None:
        """Initialize the base OpenAI processor.

        Args:
            models: Dictionary of supported AI models
            api_key: API key for OpenAI/Azure OpenAI
            base_url: Base URL for the API
            is_azure: Whether to use Azure OpenAI
            processor_name: Optional processor name
        """
        super().__init__(processor_name=processor_name)
        self.api_key = api_key
        self.base_url = base_url
        self.models = models
        self.is_azure = is_azure
        self.client = None

        if self.api_key and self.base_url and is_azure:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=f"{self.base_url}/openai/v1",
                default_query={"api-version": "preview"},
            )
        elif self.api_key and self.base_url:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            logger.warning("No API key found. Processor will not work.")

    @abstractmethod
    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages and generate AI response chunks."""

    def get_supported_models(self) -> dict[str, AIModel]:
        """Return supported models if API key is available."""
        return self.models if self.api_key else {}

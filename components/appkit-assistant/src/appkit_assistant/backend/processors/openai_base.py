"""
OpenAI processor for generating AI responses using OpenAI's API.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Final

from openai import AsyncOpenAI

from appkit_assistant.backend.models import (
    AIModel,
    Chunk,
    MCPServer,
    Message,
)
from appkit_assistant.backend.processor import Processor

logger = logging.getLogger(__name__)

DEFAULT: Final = AIModel(
    id="default",
    text="Default (GPT 4.1 Mini)",
    icon="avvia_intelligence",
    model="default",
    stream=True,
)

O3: Final = AIModel(
    id="o3",
    text="o3 Reasoning",
    icon="openai",
    model="o3",
    temperature=1,
    stream=True,
    supports_attachments=False,
    supports_tools=True,
)

O4_MINI: Final = AIModel(
    id="o4-mini",
    text="o4 Mini Reasoning",
    icon="openai",
    model="o4-mini",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    temperature=1,
)

GPT_5: Final = AIModel(
    id="gpt-5",
    text="GPT 5",
    icon="openai",
    model="gpt-5",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_1: Final = AIModel(
    id="gpt-5.1",
    text="GPT 5.1",
    icon="openai",
    model="gpt-5.1",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_2: Final = AIModel(
    id="gpt-5.2",
    text="GPT 5.2",
    icon="openai",
    model="gpt-5.2",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_MINI: Final = AIModel(
    id="gpt-5-mini",
    text="GPT 5 Mini",
    icon="openai",
    model="gpt-5-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_1_MINI: Final = AIModel(
    id="gpt-5.1-mini",
    text="GPT 5.1 Mini",
    icon="openai",
    model="gpt-5.1-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_NANO: Final = AIModel(
    id="gpt-5-nano",
    text="GPT 5 Nano",
    icon="openai",
    model="gpt-5-nano",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)


class BaseOpenAIProcessor(Processor, ABC):
    """Base class for OpenAI processors with common initialization and utilities."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
        is_azure: bool = False,
    ) -> None:
        """Initialize the base OpenAI processor.

        Args:
            models: Dictionary of supported AI models
            api_key: API key for OpenAI/Azure OpenAI
            base_url: Base URL for the API
            is_azure: Whether to use Azure OpenAI client
        """
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

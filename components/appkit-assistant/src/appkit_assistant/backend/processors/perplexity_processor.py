import asyncio
import enum
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from appkit_assistant.backend.models import AIModel, Chunk, MCPServer, Message
from appkit_assistant.backend.processors.openai_chat_completion_processor import (
    OpenAIChatCompletionsProcessor,
)

logger = logging.getLogger(__name__)


class ContextSize(enum.StrEnum):
    """Enum for context size options."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PerplexityAIModel(AIModel):
    """AI model for Perplexity API."""

    search_context_size: ContextSize = ContextSize.MEDIUM
    search_domain_filter: list[str] = []


SONAR = PerplexityAIModel(
    id="sonar",
    text="Perplexity Sonar",
    icon="perplexity",
    model="sonar",
    stream=True,
)

SONAR_PRO = PerplexityAIModel(
    id="sonar-pro",
    text="Perplexity Sonar Pro",
    icon="perplexity",
    model="sonar-pro",
    stream=True,
    keywords=["sonar", "perplexity"],
)

SONAR_DEEP_RESEARCH = PerplexityAIModel(
    id="sonar-deep-research",
    text="Perplexity Deep Research",
    icon="perplexity",
    model="sonar-deep-research",
    search_context_size=ContextSize.HIGH,
    stream=True,
    keywords=["reasoning", "deep", "research", "perplexity"],
)

SONAR_REASONING = PerplexityAIModel(
    id="sonar-reasoning",
    text="Perplexity Reasoning",
    icon="perplexity",
    model="sonar-reasoning",
    search_context_size=ContextSize.HIGH,
    stream=True,
    keywords=["reasoning", "perplexity"],
)

ALL_MODELS = {
    SONAR.id: SONAR,
    SONAR_PRO.id: SONAR_PRO,
    SONAR_DEEP_RESEARCH.id: SONAR_DEEP_RESEARCH,
    SONAR_REASONING.id: SONAR_REASONING,
}


class PerplexityProcessor(OpenAIChatCompletionsProcessor):
    """Processor that generates text responses using the Perplexity API."""

    def __init__(
        self,
        api_key: str | None = os.getenv("PERPLEXITY_API_KEY"),
        models: dict[str, PerplexityAIModel] | None = None,
    ) -> None:
        self.base_url = "https://api.perplexity.ai"
        super().__init__(api_key=api_key, base_url=self.base_url, models=models)

    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,  # noqa: ARG002
        payload: dict[str, Any] | None = None,
        cancellation_token: asyncio.Event | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Chunk, None]:
        if model_id not in self.models:
            logger.error("Model %s not supported by Perplexity processor", model_id)
            raise ValueError(f"Model {model_id} not supported by Perplexity processor")

        model = self.models[model_id]

        # Create Perplexity-specific payload
        perplexity_payload = {
            "search_domain_filter": model.search_domain_filter,
            "return_images": True,
            "return_related_questions": True,
            "web_search_options": {
                "search_context_size": model.search_context_size,
            },
        }

        # Merge with any additional payload
        if payload:
            perplexity_payload.update(payload)

        async for response in super().process(
            messages=messages,
            model_id=model_id,
            files=files,
            mcp_servers=None,
            payload=perplexity_payload,
            cancellation_token=cancellation_token,
            **kwargs,
        ):
            yield response

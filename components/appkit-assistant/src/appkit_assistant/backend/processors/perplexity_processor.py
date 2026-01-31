import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncStream

from appkit_assistant.backend.database.models import (
    MCPServer,
)
from appkit_assistant.backend.models.perplexity import PerplexityAIModel
from appkit_assistant.backend.processors.openai_chat_completion_processor import (
    OpenAIChatCompletionsProcessor,
)
from appkit_assistant.backend.schemas import (
    Chunk,
    Message,
)
from appkit_assistant.backend.services.chunk_factory import ChunkFactory

logger = logging.getLogger(__name__)


class PerplexityProcessor(OpenAIChatCompletionsProcessor):
    """Processor that generates text responses using the Perplexity API."""

    def __init__(
        self,
        api_key: str | None = os.getenv("PERPLEXITY_API_KEY"),
        models: dict[str, PerplexityAIModel] | None = None,
    ) -> None:
        self.base_url = "https://api.perplexity.ai"
        super().__init__(api_key=api_key, base_url=self.base_url, models=models)
        self._chunk_factory = ChunkFactory(processor_name="perplexity")

    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,  # noqa: ARG002
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        cancellation_token: asyncio.Event | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using Perplexity API with citation support.

        Args:
            messages: List of messages to process.
            model_id: ID of the model to use.
            files: File attachments (not used in Perplexity).
            mcp_servers: MCP servers (not supported, will log warning).
            payload: Additional payload parameters.
            cancellation_token: Optional event to signal cancellation.
            **kwargs: Additional arguments.
        """
        if not self.client:
            raise ValueError("Perplexity Client not initialized.")

        if model_id not in self.models:
            logger.error("Model %s not supported by Perplexity processor", model_id)
            raise ValueError(f"Model {model_id} not supported by Perplexity processor")

        if mcp_servers:
            logger.warning(
                "MCP servers provided to PerplexityProcessor but not supported."
            )

        model = self.models[model_id]
        perplexity_payload = self._build_perplexity_payload(model, payload)

        try:
            chat_messages = self._convert_messages_to_openai_format(messages)
            session = await self.client.chat.completions.create(
                model=model.model,
                messages=chat_messages[:-1],
                stream=model.stream,
                temperature=model.temperature,
                extra_body=perplexity_payload,
            )

            if isinstance(session, AsyncStream):
                async for chunk in self._process_streaming_response(
                    session, model, cancellation_token
                ):
                    yield chunk
            else:
                async for chunk in self._process_non_streaming_response(session, model):
                    yield chunk

        except Exception as e:
            logger.error("Error in Perplexity processor: %s", e)
            raise

    def _build_perplexity_payload(
        self, model: PerplexityAIModel, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build the Perplexity-specific payload.

        Args:
            model: The Perplexity AI model configuration.
            payload: Additional payload parameters to merge.

        Returns:
            Combined payload dictionary for the API request.
        """
        perplexity_payload = {
            "search_domain_filter": model.search_domain_filter,
            "return_images": True,
            "return_related_questions": True,
            "web_search_options": {
                "search_context_size": model.search_context_size,
            },
        }
        if payload:
            perplexity_payload.update(payload)
        return perplexity_payload

    async def _process_streaming_response(
        self,
        session: AsyncStream[Any],
        model: PerplexityAIModel,
        cancellation_token: asyncio.Event | None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process a streaming response from Perplexity API.

        Args:
            session: The async stream from the API.
            model: The model configuration.
            cancellation_token: Optional cancellation event.

        Yields:
            Chunk objects with text content and citations.
        """
        citations: list[str] = []

        async for event in session:
            if cancellation_token and cancellation_token.is_set():
                logger.info("Processing cancelled by user")
                break

            # Extract citations from streaming response if available
            if hasattr(event, "citations") and event.citations:
                citations = event.citations

            if event.choices and event.choices[0].delta:
                content = event.choices[0].delta.content
                if content:
                    yield self._create_chunk(
                        content, model.model, stream=True, message_id=event.id
                    )

        # After streaming completes, yield citation annotations
        async for chunk in self._yield_citations(citations):
            yield chunk

    async def _process_non_streaming_response(
        self, session: Any, model: PerplexityAIModel
    ) -> AsyncGenerator[Chunk, None]:
        """Process a non-streaming response from Perplexity API.

        Args:
            session: The response object from the API.
            model: The model configuration.

        Yields:
            Chunk objects with text content and citations.
        """
        content = session.choices[0].message.content
        citations: list[str] = []

        if hasattr(session, "citations") and session.citations:
            citations = session.citations

        if content:
            yield self._create_chunk(content, model.model, message_id=session.id)

        async for chunk in self._yield_citations(citations):
            yield chunk

    async def _yield_citations(
        self, citations: list[str]
    ) -> AsyncGenerator[Chunk, None]:
        """Yield annotation chunks for citations.

        Args:
            citations: List of citation URLs from Perplexity API.

        Yields:
            Chunk objects with citation annotations.
        """
        if not citations:
            return

        logger.debug("Processing %d citations from Perplexity", len(citations))

        # Yield individual ANNOTATION chunks for citations display
        for url in citations:
            yield self._chunk_factory.annotation(
                text=url,
                annotation_data={"url": url, "source": "perplexity"},
            )

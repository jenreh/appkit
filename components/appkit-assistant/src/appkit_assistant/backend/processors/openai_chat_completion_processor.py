import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from appkit_assistant.backend.database.models import (
    MCPServer,
)
from appkit_assistant.backend.processors.openai_base import BaseOpenAIProcessor
from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
    Message,
    MessageType,
)

logger = logging.getLogger(__name__)


class OpenAIChatCompletionsProcessor(BaseOpenAIProcessor):
    """Processor that generates responses using OpenAI's Chat Completions API."""

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
        """Process messages using the Chat Completions API."""
        self._validate_inputs(model_id, mcp_servers)

        # Reset statistics for the new request
        self._reset_statistics(model_id)

        model = self.models[model_id]
        request_kwargs = self._build_request_kwargs(messages, model, payload)

        response = await self.client.chat.completions.create(**request_kwargs)

        if isinstance(response, AsyncStream):
            async for chunk in self._handle_stream_response(
                response, model.model, cancellation_token
            ):
                yield chunk
        else:
            async for chunk in self._handle_sync_response(response, model.model):
                yield chunk

        # Yield final completion chunk with statistics
        yield self._create_completion_chunk()

    def _validate_inputs(
        self, model_id: str, mcp_servers: list[MCPServer] | None
    ) -> None:
        """Validate input parameters."""
        if not self.client:
            raise ValueError("OpenAI Client not initialized.")

        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not supported by OpenAI processor")

        if mcp_servers:
            logger.warning(
                "MCP servers provided to ChatCompletionsProcessor but not supported. "
                "Use OpenAIResponsesProcessor for MCP functionality."
            )

    def _build_request_kwargs(
        self,
        messages: list[Message],
        model: Any,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build arguments for the OpenAI API request."""
        chat_messages = self._convert_messages_to_openai_format(messages)

        kwargs = {
            "model": model.model,
            "messages": chat_messages,
            "stream": model.stream,
            "temperature": model.temperature,
            "extra_body": payload,
        }

        if model.stream:
            kwargs["stream_options"] = {"include_usage": True}

        return kwargs

    async def _handle_stream_response(
        self,
        stream: AsyncStream,
        model_name: str,
        cancellation_token: asyncio.Event | None,
    ) -> AsyncGenerator[Chunk, None]:
        """Handle streaming response from OpenAI."""
        async for event in stream:
            if cancellation_token and cancellation_token.is_set():
                logger.info("Processing cancelled by user")
                break

            if event.choices and event.choices[0].delta.content:
                yield self._create_text_chunk(
                    event.choices[0].delta.content,
                    model_name,
                    stream=True,
                    message_id=event.id,
                )

            # Capture usage stats from stream (usually in the last chunk)
            if hasattr(event, "usage") and event.usage:
                self._update_statistics(
                    input_tokens=event.usage.prompt_tokens,
                    output_tokens=event.usage.completion_tokens,
                )

    async def _handle_sync_response(
        self,
        response: ChatCompletion,
        model_name: str,
    ) -> AsyncGenerator[Chunk, None]:
        """Handle synchronous response from OpenAI."""
        if response.usage:
            self._update_statistics(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        content = response.choices[0].message.content
        if content:
            yield self._create_text_chunk(
                content,
                model_name,
                stream=False,
                message_id=response.id,
            )

    def _create_text_chunk(
        self,
        content: str,
        model: str,
        stream: bool = False,
        message_id: str | None = None,
    ) -> Chunk:
        """Create a text chunk."""
        metadata = {
            "source": "chat_completions",
            "streaming": str(stream),
            "model": model,
        }
        if message_id:
            metadata["message_id"] = message_id

        return Chunk(
            type=ChunkType.TEXT,
            text=content,
            chunk_metadata=metadata,
        )

    def _create_completion_chunk(self) -> Chunk:
        """Create the final completion chunk with statistics."""
        stats = self._get_statistics()
        logger.debug("Completion statistics: %s", stats)
        return Chunk(
            type=ChunkType.COMPLETION,
            text="Response generation completed",
            chunk_metadata={"status": "response_complete"},
            statistics=stats,
        )

    def _convert_messages_to_openai_format(
        self, messages: list[Message]
    ) -> list[ChatCompletionMessageParam]:
        """Convert internal messages to OpenAI chat completion format.

        Merges consecutive user/assistant messages as required by OpenAI.
        """
        formatted: list[ChatCompletionMessageParam] = []
        role_map = {
            MessageType.HUMAN: "user",
            MessageType.SYSTEM: "system",
            MessageType.ASSISTANT: "assistant",
        }

        for msg in messages or []:
            if msg.type not in role_map:
                continue

            role = role_map[msg.type]
            if formatted and role != "system" and formatted[-1]["role"] == role:
                # Merge consecutive user/assistant messages
                current_content = formatted[-1]["content"] or ""
                formatted[-1]["content"] = f"{current_content}\n\n{msg.text}"
            else:
                formatted.append({"role": role, "content": msg.text})  # type: ignore

        return formatted

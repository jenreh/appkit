# ruff: noqa: ARG002, SLF001, S105, S106, PERF401
"""Tests for OpenAIChatCompletionsProcessor.

Covers init, input validation, request building, message conversion,
stream/sync response handling, and completion chunk creation.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncStream

from appkit_assistant.backend.processors.openai_chat_completion_processor import (
    OpenAIChatCompletionsProcessor,
)
from appkit_assistant.backend.schemas import (
    AIModel,
    ChunkType,
    Message,
    MessageType,
)

_PATCH = "appkit_assistant.backend.processors.openai_chat_completion_processor"


# ============================================================================
# Helpers
# ============================================================================


def _model(
    model_id: str = "gpt-4o",
    stream: bool = True,
    temperature: float = 0.7,
) -> AIModel:
    return AIModel(
        id=model_id,
        text=model_id,
        model=model_id,
        stream=stream,
        temperature=temperature,
    )


def _make_processor(
    api_key: str = "sk-test",
    base_url: str | None = None,
    on_azure: bool = False,
    models: dict[str, AIModel] | None = None,
) -> OpenAIChatCompletionsProcessor:
    if models is None:
        models = {"gpt-4o": _model()}
    with patch(
        "appkit_assistant.backend.processors.openai_base.AsyncOpenAI"
    ) as mock_cls:
        mock_cls.return_value = MagicMock()
        return OpenAIChatCompletionsProcessor(
            models=models,
            api_key=api_key,
            base_url=base_url,
            on_azure=on_azure,
        )


# ============================================================================
# Initialization
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = _make_processor()
        assert proc.client is not None

    def test_no_api_key(self) -> None:
        proc = OpenAIChatCompletionsProcessor(models={"m": _model()}, api_key=None)
        assert proc.client is None

    def test_get_supported_models_with_key(self) -> None:
        proc = _make_processor()
        assert proc.get_supported_models() == proc.models

    def test_get_supported_models_no_key(self) -> None:
        proc = OpenAIChatCompletionsProcessor(models={"m": _model()}, api_key=None)
        assert proc.get_supported_models() == {}


# ============================================================================
# _validate_inputs
# ============================================================================


class TestValidateInputs:
    def test_no_client_raises(self) -> None:
        proc = OpenAIChatCompletionsProcessor(models={"m": _model()}, api_key=None)
        with pytest.raises(ValueError, match="not initialized"):
            proc._validate_inputs("m", None)

    def test_unknown_model_raises(self) -> None:
        proc = _make_processor()
        with pytest.raises(ValueError, match="not supported"):
            proc._validate_inputs("unknown-model", None)

    def test_valid_model_passes(self) -> None:
        proc = _make_processor()
        proc._validate_inputs("gpt-4o", None)  # no exception

    def test_mcp_servers_warns(self) -> None:
        proc = _make_processor()
        server = MagicMock()
        proc._validate_inputs("gpt-4o", [server])  # logs warning but no error


# ============================================================================
# _build_request_kwargs
# ============================================================================


class TestBuildRequestKwargs:
    def test_streaming_model(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="hello")]
        model = _model(stream=True)
        kwargs = proc._build_request_kwargs(msgs, model, None)
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["stream"] is True
        assert kwargs["temperature"] == 0.7
        assert "stream_options" in kwargs
        assert kwargs["stream_options"]["include_usage"] is True

    def test_non_streaming_model(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="hello")]
        model = _model(stream=False)
        kwargs = proc._build_request_kwargs(msgs, model, None)
        assert kwargs["stream"] is False
        assert "stream_options" not in kwargs

    def test_payload_passthrough(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="hello")]
        model = _model()
        payload = {"top_p": 0.9}
        kwargs = proc._build_request_kwargs(msgs, model, payload)
        assert kwargs["extra_body"] == {"top_p": 0.9}


# ============================================================================
# _convert_messages_to_openai_format
# ============================================================================


class TestConvertMessages:
    def test_basic_conversion(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.HUMAN, text="Hello"),
            Message(type=MessageType.ASSISTANT, text="Hi"),
        ]
        result = proc._convert_messages_to_openai_format(msgs)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi"

    def test_system_message(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.SYSTEM, text="Be helpful"),
            Message(type=MessageType.HUMAN, text="Hello"),
        ]
        result = proc._convert_messages_to_openai_format(msgs)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"

    def test_consecutive_user_merge(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.HUMAN, text="First"),
            Message(type=MessageType.HUMAN, text="Second"),
        ]
        result = proc._convert_messages_to_openai_format(msgs)
        assert len(result) == 1
        assert "First" in result[0]["content"]
        assert "Second" in result[0]["content"]

    def test_consecutive_system_not_merged(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.SYSTEM, text="S1"),
            Message(type=MessageType.SYSTEM, text="S2"),
        ]
        result = proc._convert_messages_to_openai_format(msgs)
        assert len(result) == 2

    def test_empty_messages(self) -> None:
        proc = _make_processor()
        result = proc._convert_messages_to_openai_format([])
        assert result == []

    def test_none_messages(self) -> None:
        proc = _make_processor()
        result = proc._convert_messages_to_openai_format(None)
        assert result == []


# ============================================================================
# _create_text_chunk
# ============================================================================


class TestCreateTextChunk:
    def test_basic(self) -> None:
        proc = _make_processor()
        chunk = proc._create_text_chunk("hello", "gpt-4o")
        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "hello"
        assert chunk.chunk_metadata["source"] == "chat_completions"
        assert chunk.chunk_metadata["streaming"] == "False"
        assert chunk.chunk_metadata["model"] == "gpt-4o"

    def test_streaming(self) -> None:
        proc = _make_processor()
        chunk = proc._create_text_chunk(
            "hello", "gpt-4o", stream=True, message_id="msg-123"
        )
        assert chunk.chunk_metadata["streaming"] == "True"
        assert chunk.chunk_metadata["message_id"] == "msg-123"


# ============================================================================
# _create_completion_chunk
# ============================================================================


class TestCreateCompletionChunk:
    def test_creates_completion(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")
        chunk = proc._create_completion_chunk()
        assert chunk.type == ChunkType.COMPLETION
        assert chunk.chunk_metadata["status"] == "response_complete"
        assert chunk.statistics is not None


# ============================================================================
# Stream response handling
# ============================================================================


class TestHandleStreamResponse:
    @pytest.mark.asyncio
    async def test_text_events(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        event1 = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"))],
            id="msg-1",
            usage=None,
        )
        event2 = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=" world"))],
            id="msg-1",
            usage=None,
        )

        async def mock_stream():
            yield event1
            yield event2

        chunks = []
        async for chunk in proc._handle_stream_response(mock_stream(), "gpt-4o", None):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].text == "Hello"
        assert chunks[1].text == " world"

    @pytest.mark.asyncio
    async def test_cancellation(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        event = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="X"))],
            id="msg-1",
            usage=None,
        )

        cancel = asyncio.Event()
        cancel.set()  # already cancelled

        async def mock_stream():
            yield event
            yield event

        chunks = []
        async for chunk in proc._handle_stream_response(
            mock_stream(), "gpt-4o", cancel
        ):
            chunks.append(chunk)

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_usage_captured(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50)
        event = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="T"))],
            id="msg-1",
            usage=usage,
        )

        async def mock_stream():
            yield event

        chunks = []
        async for chunk in proc._handle_stream_response(mock_stream(), "gpt-4o", None):
            chunks.append(chunk)

        stats = proc._get_statistics()
        assert stats.input_tokens == 100
        assert stats.output_tokens == 50


# ============================================================================
# Sync response handling
# ============================================================================


class TestHandleSyncResponse:
    @pytest.mark.asyncio
    async def test_basic_response(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Final answer"))],
            id="chatcmpl-123",
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

        chunks = []
        async for chunk in proc._handle_sync_response(response, "gpt-4o"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].text == "Final answer"
        stats = proc._get_statistics()
        assert stats.input_tokens == 10

    @pytest.mark.asyncio
    async def test_no_content(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
            id="chatcmpl-123",
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=0),
        )

        chunks = []
        async for chunk in proc._handle_sync_response(response, "gpt-4o"):
            chunks.append(chunk)

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_no_usage(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Result"))],
            id="chatcmpl-123",
            usage=None,
        )

        chunks = []
        async for chunk in proc._handle_sync_response(response, "gpt-4o"):
            chunks.append(chunk)

        assert len(chunks) == 1


# ============================================================================
# Full process flow
# ============================================================================


class TestProcess:
    @pytest.mark.asyncio
    async def test_process_streaming(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")

        # Test streaming path by mocking the API and isinstance check
        msg_chunk = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))],
            id="msg-1",
            usage=None,
        )
        completion_choice = SimpleNamespace(delta=SimpleNamespace(content=None))
        completion_chunk = SimpleNamespace(
            choices=[completion_choice],
            id="msg-1",
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

        # Create an async generator simulating OpenAI stream
        async def mock_stream_generator():
            yield msg_chunk
            yield completion_chunk

        # Mock the client.chat.completions.create to return the generator
        proc.client.chat.completions.create = AsyncMock(
            return_value=mock_stream_generator()
        )

        # Patch isinstance to recognize our generator as AsyncStream
        original_isinstance = isinstance

        def mocked_isinstance(obj, classinfo):
            # For AsyncStream checks on our mock generator, return True
            if classinfo is AsyncStream and hasattr(obj, "__anext__"):
                return True
            return original_isinstance(obj, classinfo)

        with patch(f"{_PATCH}.isinstance", side_effect=mocked_isinstance):
            msgs = [Message(type=MessageType.HUMAN, text="Hello")]
            chunks = []
            async for chunk in proc.process(msgs, "gpt-4o"):
                chunks.append(chunk)

            # Verify streaming path was taken and produced chunks
            assert any(c.type == ChunkType.TEXT for c in chunks), (
                "Should have TEXT chunks from streaming"
            )
            assert chunks[-1].type == ChunkType.COMPLETION, (
                "Last chunk should be COMPLETION"
            )

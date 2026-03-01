"""Tests for StreamingProcessorBase.

Covers event dispatch, cancellation handling, chunk creation,
model management, and error handling during stream processing.
"""

# ruff: noqa: ARG002

import asyncio
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.processors.streaming_base import StreamingProcessorBase
from appkit_assistant.backend.schemas import AIModel, Chunk, ChunkType, Message

# ============================================================================
# Concrete subclass for testing the abstract base
# ============================================================================


class _TestProcessor(StreamingProcessorBase):
    """Minimal concrete processor for testing the abstract base."""

    def __init__(self, models: dict[str, AIModel] | None = None) -> None:
        super().__init__(models or {}, "test_processor")
        self._custom_handlers: dict[str, Any] = {}

    def set_handler(self, event_type: str, handler: Any) -> None:
        self._custom_handlers[event_type] = handler

    def _get_event_handlers(self) -> dict[str, Any]:
        return self._custom_handlers

    async def process(  # noqa: ARG002
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        yield self._create_chunk(ChunkType.TEXT, "test")


def _make_model(model_id: str = "test-model") -> AIModel:
    return AIModel(
        id=model_id,
        model=model_id,
        display_name="Test Model",
        text=model_id,
        provider="test",
    )


# ============================================================================
# Initialisation
# ============================================================================


class TestInit:
    def test_defaults(self) -> None:
        proc = _TestProcessor()
        assert proc._processor_name == "test_processor"  # noqa: SLF001
        assert proc.models == {}
        assert proc.chunk_factory is not None
        assert proc.auth_detector is not None
        assert proc.current_reasoning_session is None

    def test_with_models(self) -> None:
        models = {"m1": _make_model("m1")}
        proc = _TestProcessor(models)
        assert proc.get_supported_models() == models


# ============================================================================
# _handle_event
# ============================================================================


class TestHandleEvent:
    def test_known_event_type(self) -> None:
        proc = _TestProcessor()
        chunk = Chunk(type=ChunkType.TEXT, text="hello")
        proc.set_handler("text_delta", lambda _e: chunk)

        event = SimpleNamespace(type="text_delta")
        result = proc._handle_event(event)  # noqa: SLF001
        assert result is chunk

    def test_unknown_event_type(self) -> None:
        proc = _TestProcessor()
        event = SimpleNamespace(type="unknown_event")
        result = proc._handle_event(event)  # noqa: SLF001
        assert result is None

    def test_no_type_attribute(self) -> None:
        proc = _TestProcessor()
        event = SimpleNamespace()  # no type attribute
        result = proc._handle_event(event)  # noqa: SLF001
        assert result is None

    def test_handler_returns_none(self) -> None:
        proc = _TestProcessor()
        proc.set_handler("skip_event", lambda _e: None)
        event = SimpleNamespace(type="skip_event")
        result = proc._handle_event(event)  # noqa: SLF001
        assert result is None


# ============================================================================
# _process_stream_with_cancellation
# ============================================================================


class TestProcessStreamWithCancellation:
    @pytest.mark.asyncio
    async def test_processes_all_events(self) -> None:
        proc = _TestProcessor()
        chunk = Chunk(type=ChunkType.TEXT, text="hi")
        proc.set_handler("text", lambda _e: chunk)

        async def fake_stream():
            yield SimpleNamespace(type="text")
            yield SimpleNamespace(type="text")

        result = [
            c
            async for c in proc._process_stream_with_cancellation(  # noqa: SLF001
                fake_stream()
            )
        ]
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_cancellation_stops_stream(self) -> None:
        proc = _TestProcessor()
        chunk = Chunk(type=ChunkType.TEXT, text="hi")
        proc.set_handler("text", lambda _e: chunk)
        cancel = asyncio.Event()

        async def fake_stream():
            yield SimpleNamespace(type="text")
            cancel.set()
            yield SimpleNamespace(type="text")
            yield SimpleNamespace(type="text")

        result = [
            c
            async for c in proc._process_stream_with_cancellation(  # noqa: SLF001
                fake_stream(), cancel
            )
        ]
        # Should get first chunk, then stop
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_error_yields_error_chunk(self) -> None:
        proc = _TestProcessor()

        async def failing_stream():
            raise RuntimeError("stream broke")
            yield  # noqa: RET503 - needed to make async generator

        result = [
            c
            async for c in proc._process_stream_with_cancellation(  # noqa: SLF001
                failing_stream()
            )
        ]
        assert len(result) == 1
        assert result[0].type == ChunkType.ERROR

    @pytest.mark.asyncio
    async def test_auth_error_suppressed(self) -> None:
        proc = _TestProcessor()
        proc._auth_detector.is_auth_error = MagicMock(return_value=True)  # noqa: SLF001

        async def auth_fail_stream():
            raise RuntimeError("401 Unauthorized")
            yield  # noqa: RET503

        result = [
            c
            async for c in proc._process_stream_with_cancellation(  # noqa: SLF001
                auth_fail_stream()
            )
        ]
        # Auth errors should NOT yield error chunks
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_skips_none_chunks(self) -> None:
        proc = _TestProcessor()
        proc.set_handler("skip", lambda _e: None)
        chunk = Chunk(type=ChunkType.TEXT, text="real")
        proc.set_handler("text", lambda _e: chunk)

        async def mixed_stream():
            yield SimpleNamespace(type="skip")
            yield SimpleNamespace(type="text")
            yield SimpleNamespace(type="skip")

        result = [
            c
            async for c in proc._process_stream_with_cancellation(  # noqa: SLF001
                mixed_stream()
            )
        ]
        assert len(result) == 1


# ============================================================================
# _create_chunk
# ============================================================================


class TestCreateChunk:
    def test_creates_chunk(self) -> None:
        proc = _TestProcessor()
        chunk = proc._create_chunk(ChunkType.TEXT, "hello")  # noqa: SLF001
        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "hello"
        assert chunk.chunk_metadata["processor"] == "test_processor"

    def test_extra_metadata(self) -> None:
        proc = _TestProcessor()
        chunk = proc._create_chunk(  # noqa: SLF001
            ChunkType.TEXT, "hi", {"key": "value"}
        )
        assert chunk.chunk_metadata["key"] == "value"
        assert chunk.chunk_metadata["processor"] == "test_processor"


# ============================================================================
# get_supported_models
# ============================================================================


class TestGetSupportedModels:
    def test_empty_models(self) -> None:
        proc = _TestProcessor()
        assert proc.get_supported_models() == {}

    def test_populated_models(self) -> None:
        models = {"a": _make_model("a"), "b": _make_model("b")}
        proc = _TestProcessor(models)
        result = proc.get_supported_models()
        assert len(result) == 2
        assert "a" in result
        assert "b" in result


# ============================================================================
# current_reasoning_session property
# ============================================================================


class TestReasoningSession:
    def test_get_set(self) -> None:
        proc = _TestProcessor()
        assert proc.current_reasoning_session is None
        proc.current_reasoning_session = "session-1"
        assert proc.current_reasoning_session == "session-1"
        proc.current_reasoning_session = None
        assert proc.current_reasoning_session is None

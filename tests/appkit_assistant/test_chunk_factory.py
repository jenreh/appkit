"""Tests for ChunkFactory service."""

import pytest

from appkit_assistant.backend.schemas import ChunkType, ProcessingStatistics
from appkit_assistant.backend.services.chunk_factory import ChunkFactory


class TestChunkFactory:
    """Test suite for ChunkFactory."""

    def test_init_sets_processor_name(self) -> None:
        """ChunkFactory initializes with processor name."""
        factory = ChunkFactory("test_processor")

        assert factory.processor_name == "test_processor"

    def test_create_basic_chunk(self) -> None:
        """create() creates chunk with type and content."""
        factory = ChunkFactory("test")

        chunk = factory.create(ChunkType.TEXT, "Test content")

        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "Test content"
        assert chunk.chunk_metadata["processor"] == "test"

    def test_create_with_extra_metadata(self) -> None:
        """create() includes extra metadata."""
        factory = ChunkFactory("test")

        chunk = factory.create(
            ChunkType.TEXT, "Content", extra_metadata={"key1": "value1", "key2": 123}
        )

        assert chunk.chunk_metadata["key1"] == "value1"
        assert chunk.chunk_metadata["key2"] == "123"  # Converted to string

    def test_create_filters_none_metadata(self) -> None:
        """create() excludes None values from metadata."""
        factory = ChunkFactory("test")

        chunk = factory.create(
            ChunkType.TEXT, "Content", extra_metadata={"key1": "value", "key2": None}
        )

        assert "key1" in chunk.chunk_metadata
        assert "key2" not in chunk.chunk_metadata

    def test_text_chunk(self) -> None:
        """text() creates TEXT chunk."""
        factory = ChunkFactory("test")

        chunk = factory.text("Hello world")

        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "Hello world"
        assert chunk.chunk_metadata["processor"] == "test"

    def test_text_chunk_with_delta(self) -> None:
        """text() includes delta metadata when provided."""
        factory = ChunkFactory("test")

        chunk = factory.text("Full text", delta="new")

        assert chunk.chunk_metadata["delta"] == "new"

    def test_thinking_chunk(self) -> None:
        """thinking() creates THINKING chunk."""
        factory = ChunkFactory("test")

        chunk = factory.thinking("Analyzing request")

        assert chunk.type == ChunkType.THINKING
        assert chunk.text == "Analyzing request"
        assert chunk.chunk_metadata["status"] == "in_progress"

    def test_thinking_chunk_with_reasoning_id(self) -> None:
        """thinking() includes reasoning_id when provided."""
        factory = ChunkFactory("test")

        chunk = factory.thinking(
            "Thinking...", reasoning_id="reason-123", status="completed", delta="delta"
        )

        assert chunk.chunk_metadata["reasoning_id"] == "reason-123"
        assert chunk.chunk_metadata["status"] == "completed"
        assert chunk.chunk_metadata["delta"] == "delta"

    def test_thinking_result_chunk(self) -> None:
        """thinking_result() creates THINKING_RESULT chunk."""
        factory = ChunkFactory("test")

        chunk = factory.thinking_result("Result text")

        assert chunk.type == ChunkType.THINKING_RESULT
        assert chunk.text == "Result text"
        assert chunk.chunk_metadata["status"] == "completed"

    def test_thinking_result_with_reasoning_id(self) -> None:
        """thinking_result() includes reasoning_id when provided."""
        factory = ChunkFactory("test")

        chunk = factory.thinking_result("Result", reasoning_id="reason-456")

        assert chunk.chunk_metadata["reasoning_id"] == "reason-456"

    def test_tool_call_chunk(self) -> None:
        """tool_call() creates TOOL_CALL chunk with required metadata."""
        factory = ChunkFactory("test")

        chunk = factory.tool_call(
            "Calling search tool", tool_name="search", tool_id="tool-123"
        )

        assert chunk.type == ChunkType.TOOL_CALL
        assert chunk.text == "Calling search tool"
        assert chunk.chunk_metadata["tool_name"] == "search"
        assert chunk.chunk_metadata["tool_id"] == "tool-123"
        assert chunk.chunk_metadata["status"] == "starting"

    def test_tool_call_chunk_with_optional_metadata(self) -> None:
        """tool_call() includes optional server and reasoning metadata."""
        factory = ChunkFactory("test")

        chunk = factory.tool_call(
            "Tool call",
            tool_name="search",
            tool_id="tool-123",
            server_label="MCP Server",
            status="running",
            reasoning_session="reason-789",
        )

        assert chunk.chunk_metadata["server_label"] == "MCP Server"
        assert chunk.chunk_metadata["reasoning_session"] == "reason-789"
        assert chunk.chunk_metadata["status"] == "running"

    def test_tool_result_chunk(self) -> None:
        """tool_result() creates TOOL_RESULT chunk."""
        factory = ChunkFactory("test")

        chunk = factory.tool_result("Search results: 5 items", tool_id="tool-123")

        assert chunk.type == ChunkType.TOOL_RESULT
        assert chunk.text == "Search results: 5 items"
        assert chunk.chunk_metadata["tool_id"] == "tool-123"
        assert chunk.chunk_metadata["status"] == "completed"
        assert chunk.chunk_metadata["error"] == "False"

    def test_tool_result_chunk_with_error(self) -> None:
        """tool_result() marks error results."""
        factory = ChunkFactory("test")

        chunk = factory.tool_result("Tool failed", tool_id="tool-123", is_error=True)

        assert chunk.chunk_metadata["error"] == "True"

    def test_tool_result_with_all_optional_metadata(self) -> None:
        """tool_result() includes all optional metadata."""
        factory = ChunkFactory("test")

        chunk = factory.tool_result(
            "Result",
            tool_id="tool-123",
            status="failed",
            is_error=True,
            reasoning_session="reason-abc",
            tool_name="search",
            server_label="Server A",
        )

        assert chunk.chunk_metadata["reasoning_session"] == "reason-abc"
        assert chunk.chunk_metadata["tool_name"] == "search"
        assert chunk.chunk_metadata["server_label"] == "Server A"

    def test_lifecycle_chunk(self) -> None:
        """lifecycle() creates LIFECYCLE chunk."""
        factory = ChunkFactory("test")

        chunk = factory.lifecycle("done")

        assert chunk.type == ChunkType.LIFECYCLE
        assert chunk.text == "done"
        assert chunk.chunk_metadata["stage"] == "done"

    def test_lifecycle_chunk_with_extra(self) -> None:
        """lifecycle() includes extra metadata."""
        factory = ChunkFactory("test")

        chunk = factory.lifecycle("in_progress", extra={"step": "2", "total": "5"})

        assert chunk.chunk_metadata["stage"] == "in_progress"
        assert chunk.chunk_metadata["step"] == "2"
        assert chunk.chunk_metadata["total"] == "5"

    def test_completion_chunk(self) -> None:
        """completion() creates COMPLETION chunk."""
        factory = ChunkFactory("test")

        chunk = factory.completion()

        assert chunk.type == ChunkType.COMPLETION
        assert chunk.text == "Response generation completed"
        assert chunk.chunk_metadata["status"] == "response_complete"

    def test_completion_chunk_with_statistics(self) -> None:
        """completion() includes processing statistics when provided."""
        factory = ChunkFactory("test")
        stats = ProcessingStatistics(
            input_tokens=100,
            output_tokens=50,
            tool_uses={"search": 2},
            model="gpt-4",
            processor="openai",
        )

        chunk = factory.completion(status="finished", statistics=stats)

        assert chunk.statistics is not None
        assert chunk.statistics.input_tokens == 100
        assert chunk.statistics.output_tokens == 50
        assert chunk.statistics.tool_uses == {"search": 2}

    def test_error_chunk(self) -> None:
        """error() creates ERROR chunk."""
        factory = ChunkFactory("test")

        chunk = factory.error("Something went wrong")

        assert chunk.type == ChunkType.ERROR
        assert chunk.text == "Something went wrong"
        assert chunk.chunk_metadata["error_type"] == "unknown"

    def test_error_chunk_with_error_type(self) -> None:
        """error() includes error type when provided."""
        factory = ChunkFactory("test")

        chunk = factory.error("Auth failed", error_type="authentication_error")

        assert chunk.chunk_metadata["error_type"] == "authentication_error"

    def test_auth_required_chunk(self) -> None:
        """auth_required() creates AUTH_REQUIRED chunk."""
        factory = ChunkFactory("test")

        chunk = factory.auth_required(
            server_name="GitHub MCP",
            auth_url="https://github.com/login",
            state="state-123",
        )

        assert chunk.type == ChunkType.AUTH_REQUIRED
        assert "GitHub MCP" in chunk.text
        assert chunk.chunk_metadata["server_name"] == "GitHub MCP"
        assert chunk.chunk_metadata["auth_url"] == "https://github.com/login"
        assert chunk.chunk_metadata["state"] == "state-123"

    def test_auth_required_with_server_id(self) -> None:
        """auth_required() includes server_id when provided."""
        factory = ChunkFactory("test")

        chunk = factory.auth_required(
            server_name="Test Server", server_id="server-456"
        )

        assert chunk.chunk_metadata["server_id"] == "server-456"

    def test_annotation_chunk(self) -> None:
        """annotation() creates ANNOTATION chunk."""
        factory = ChunkFactory("test")

        chunk = factory.annotation(
            "File citation", {"file_id": "file-123", "quote": "Original text"}
        )

        assert chunk.type == ChunkType.ANNOTATION
        assert chunk.text == "File citation"
        assert chunk.chunk_metadata["file_id"] == "file-123"
        assert chunk.chunk_metadata["quote"] == "Original text"

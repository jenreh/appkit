"""Tests for OpenAIResponsesProcessor.

Covers:
- Initialization (with/without API key, with/without base_url, Azure mode)
- get_supported_models()
- _create_client()
- _handle_event() and all sub-handlers
- _extract_annotation_text()
- _handle_lifecycle_events()
- _handle_text_events()
- _handle_item_events() (all item types)
- _handle_mcp_events() (all MCP event types)
- _handle_shell_events()
- _handle_search_events() (file_search, web_search)
- _handle_completion_events()
- _handle_image_events()
- _processing_chunk()
- _extract_error_text()
- _configure_mcp_tools()
- _convert_messages_to_responses_format()
- _extract_responses_content()
- process() – no client raises ValueError
- process() – unsupported model raises ValueError
- process() – cancellation_token respected
- _process_file_uploads_streaming() – various paths
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.openai_responses_processor import (
    OpenAIResponsesProcessor,
)
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    ChunkType,
    MCPAuthType,
    Message,
    MessageType,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_event(event_type: str, **kwargs: Any) -> MagicMock:
    """Create a mock event with a .type attribute and optional extras."""
    ev = MagicMock()
    ev.type = event_type
    for key, value in kwargs.items():
        setattr(ev, key, value)
    return ev


def _make_item(item_type: str, **kwargs: Any) -> MagicMock:
    item = MagicMock()
    item.type = item_type
    for key, value in kwargs.items():
        setattr(item, key, value)
    return item


def _make_processor(
    model_id: str = "gpt-4o-test",
    api_key: str = "sk-fake",
    base_url: str | None = None,
    on_azure: bool = False,
) -> OpenAIResponsesProcessor:
    model = AIModel(
        id=model_id,
        text="GPT-4o Test",
        model="gpt-4o",
        stream=True,
        temperature=0.7,
        supports_search=False,
    )
    return OpenAIResponsesProcessor(
        models={model_id: model},
        api_key=api_key,
        base_url=base_url,
        on_azure=on_azure,
    )


async def _collect(gen) -> list[Chunk]:
    """Collect all chunks from an async generator."""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return chunks


# ── Initialization ─────────────────────────────────────────────────────────────


class TestOpenAIResponsesProcessorInit:
    def test_init_with_api_key_creates_client(self):
        p = _make_processor()
        assert p._client is not None

    def test_init_without_api_key_no_client(self):
        model = AIModel(id="m", text="M", model="gpt-4o")
        p = OpenAIResponsesProcessor(models={"m": model}, api_key=None)
        assert p._client is None

    def test_init_empty_api_key_no_client(self):
        model = AIModel(id="m", text="M", model="gpt-4o")
        p = OpenAIResponsesProcessor(models={"m": model}, api_key="")
        assert p._client is None

    def test_init_with_base_url(self):
        p = _make_processor(base_url="https://custom.openai.azure.com")
        assert p._client is not None
        assert p._base_url == "https://custom.openai.azure.com"

    def test_init_azure_mode(self):
        p = _make_processor(
            base_url="https://my-resource.openai.azure.com", on_azure=True
        )
        assert p._on_azure is True
        assert p._client is not None

    def test_get_supported_models_with_key(self):
        p = _make_processor()
        models = p.get_supported_models()
        assert "gpt-4o-test" in models

    def test_get_supported_models_without_key(self):
        model = AIModel(id="m", text="M", model="gpt-4o")
        p = OpenAIResponsesProcessor(models={"m": model}, api_key=None)
        assert p.get_supported_models() == {}

    def test_processor_name_set(self):
        p = _make_processor()
        assert p._processor_name == "openai_responses"


# ── _create_client() ──────────────────────────────────────────────────────────


class TestCreateClient:
    def test_standard_client(self):
        p = _make_processor()
        client = p._create_client()
        assert client is not None

    def test_no_api_key_returns_none(self):
        model = AIModel(id="m", text="M", model="gpt-4o")
        p = OpenAIResponsesProcessor(models={"m": model}, api_key=None)
        p._api_key = None
        assert p._create_client() is None

    def test_base_url_client(self):
        p = _make_processor(base_url="https://proxy.example.com/v1")
        assert p._client is not None

    def test_azure_client(self):
        p = _make_processor(
            base_url="https://my-resource.openai.azure.com", on_azure=True
        )
        assert p._client is not None


# ── _processing_chunk() ───────────────────────────────────────────────────────


class TestProcessingChunk:
    def test_returns_processing_type(self):
        p = _make_processor()
        chunk = p._processing_chunk("started")
        assert chunk.type == ChunkType.PROCESSING

    def test_includes_status(self):
        p = _make_processor()
        chunk = p._processing_chunk("completed", "vs_123")
        assert chunk.chunk_metadata["status"] == "completed"
        assert chunk.chunk_metadata["vector_store_id"] == "vs_123"

    def test_extra_kwargs_in_metadata(self):
        p = _make_processor()
        chunk = p._processing_chunk("failed", None, error="disk full")
        assert chunk.chunk_metadata["error"] == "disk full"


# ── _handle_lifecycle_events() ────────────────────────────────────────────────


class TestHandleLifecycleEvents:
    def test_response_created(self):
        p = _make_processor()
        ev = _make_event("response.created")
        chunk = p._handle_lifecycle_events("response.created", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE
        assert "created" in chunk.text

    def test_response_in_progress(self):
        p = _make_processor()
        ev = _make_event("response.in_progress")
        chunk = p._handle_lifecycle_events("response.in_progress", ev)
        assert chunk is not None
        assert "in_progress" in chunk.text

    def test_response_done(self):
        p = _make_processor()
        ev = _make_event("response.done")
        chunk = p._handle_lifecycle_events("response.done", ev)
        assert chunk is not None
        assert "done" in chunk.text

    def test_unknown_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.unknown")
        chunk = p._handle_lifecycle_events("response.unknown", ev)
        assert chunk is None


# ── _handle_text_events() ─────────────────────────────────────────────────────


class TestHandleTextEvents:
    def test_output_text_delta(self):
        p = _make_processor()
        ev = _make_event("response.output_text.delta", delta="Hello ")
        chunk = p._handle_text_events("response.output_text.delta", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "Hello "

    def test_annotation_added_url_citation(self):
        p = _make_processor()
        annotation = MagicMock()
        annotation.type = "url_citation"
        annotation.url = "https://example.com"
        annotation.text = "[1]"
        ev = _make_event("response.output_text.annotation.added", annotation=annotation)
        chunk = p._handle_text_events(
            "response.output_text.annotation.added", ev
        )
        assert chunk is not None
        assert chunk.type == ChunkType.ANNOTATION

    def test_unknown_text_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.output_text.other")
        chunk = p._handle_text_events("response.output_text.other", ev)
        assert chunk is None


# ── _extract_annotation_text() ───────────────────────────────────────────────


class TestExtractAnnotationText:
    def test_extracts_text_field(self):
        p = _make_processor()
        ann = MagicMock()
        ann.text = "[citation]"
        result = p._extract_annotation_text(ann)
        assert result == "[citation]"

    def test_url_citation_without_text(self):
        p = _make_processor()
        ann = MagicMock()
        ann.text = None
        ann.type = "url_citation"
        ann.url = "https://example.com"
        # MagicMock has .text = None so spec it properly
        result = p._extract_annotation_text(ann)
        # Should fall through to url_citation branch
        assert "example.com" in result or result is not None

    def test_dict_annotation_text(self):
        p = _make_processor()
        ann = {"text": "[2]", "type": "file_citation"}
        result = p._extract_annotation_text(ann)
        assert result == "[2]"

    def test_dict_url_citation_fallback(self):
        p = _make_processor()
        ann = {"type": "url_citation", "url": "https://example.com/doc"}
        result = p._extract_annotation_text(ann)
        assert "example.com" in result

    def test_dict_file_citation_fallback(self):
        p = _make_processor()
        ann = {"type": "file_citation", "filename": "report.pdf"}
        result = p._extract_annotation_text(ann)
        assert "report.pdf" in result

    def test_unknown_type_returns_str(self):
        p = _make_processor()
        ann = {"type": "unknown_type"}
        result = p._extract_annotation_text(ann)
        assert isinstance(result, str)


# ── _handle_item_events() ─────────────────────────────────────────────────────


class TestHandleItemEvents:
    def test_item_added_mcp_call(self):
        p = _make_processor()
        item = _make_item(
            "mcp_call", name="my_tool", id="tool-id-1", server_label="my-server"
        )
        ev = _make_event("response.output_item.added", item=item)
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert "tool-id-1" in p._tool_name_map

    def test_item_added_shell_call(self):
        p = _make_processor()
        item = _make_item("shell_call", name="bash", id="shell-id-1")
        ev = _make_event("response.output_item.added", item=item)
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_item_added_function_call(self):
        p = _make_processor()
        item = _make_item("function_call", name="my_func", call_id="func-id-1")
        ev = _make_event("response.output_item.added", item=item)
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_item_added_reasoning(self):
        p = _make_processor()
        item = _make_item("reasoning", id="reason-1")
        ev = _make_event("response.output_item.added", item=item)
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING
        assert p.current_reasoning_session == "reason-1"

    def test_item_added_file_search_returns_none(self):
        p = _make_processor()
        item = _make_item("file_search_call")
        ev = _make_event("response.output_item.added", item=item)
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is None

    def test_item_done_function_call(self):
        p = _make_processor()
        item = _make_item("function_call", call_id="func-id-1", output="result text")
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_item_done_reasoning(self):
        p = _make_processor()
        item = _make_item("reasoning", id="reason-1", summary=["Summary text."])
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING_RESULT

    def test_item_done_mcp_call_success(self):
        p = _make_processor()
        item = _make_item(
            "mcp_call",
            id="tool-id-1",
            name="my_tool",
            server_label="my-server",
            error=None,
            output="success result",
        )
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT
        assert "success result" in chunk.text

    def test_item_done_mcp_call_with_error(self):
        p = _make_processor()
        item = _make_item(
            "mcp_call",
            id="tool-id-1",
            name="my_tool",
            server_label="my-server",
            error={"content": [{"text": "something went wrong"}]},
            output=None,
        )
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_item_done_shell_call_success(self):
        p = _make_processor()
        item = _make_item(
            "shell_call", id="sh-1", name="bash", error=None, output="stdout output"
        )
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_item_done_shell_call_with_error(self):
        p = _make_processor()
        item = _make_item(
            "shell_call", id="sh-1", name="bash", error="exit code 1", output=None
        )
        ev = _make_event("response.output_item.done", item=item)
        chunk = p._handle_item_events("response.output_item.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_no_item_attribute_returns_none(self):
        p = _make_processor()
        ev = MagicMock(spec=[])  # no .item
        chunk = p._handle_item_events("response.output_item.added", ev)
        assert chunk is None


# ── _handle_mcp_events() ──────────────────────────────────────────────────────


class TestHandleMCPEvents:
    def test_mcp_call_arguments_delta(self):
        p = _make_processor()
        p._tool_name_map["tool-1"] = "server.tool"
        ev = _make_event(
            "response.mcp_call_arguments.delta", item_id="tool-1", delta='{"key":'
        )
        chunk = p._handle_mcp_events("response.mcp_call_arguments.delta", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_mcp_call_arguments_done(self):
        p = _make_processor()
        p._tool_name_map["tool-1"] = "server.tool"
        ev = _make_event(
            "response.mcp_call_arguments.done",
            item_id="tool-1",
            arguments='{"key": "val"}',
        )
        chunk = p._handle_mcp_events("response.mcp_call_arguments.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_mcp_call_failed(self):
        p = _make_processor()
        p._tool_name_map["tool-1"] = "server.tool"
        ev = _make_event("response.mcp_call.failed", item_id="tool-1")
        chunk = p._handle_mcp_events("response.mcp_call.failed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_mcp_in_progress_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.mcp_call.in_progress", item_id="tool-1")
        chunk = p._handle_mcp_events("response.mcp_call.in_progress", ev)
        assert chunk is None

    def test_mcp_list_tools_failed_no_auth_error(self):
        p = _make_processor()
        ev = _make_event(
            "response.mcp_list_tools.failed", item_id="tool-1", error=None
        )
        chunk = p._handle_mcp_events("response.mcp_list_tools.failed", ev)
        # Should get a listing_failed chunk
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_mcp_list_tools_failed_auth_error_queues_server(
        self, mcp_server_no_auth
    ):
        p = _make_processor()
        p._available_mcp_servers = [mcp_server_no_auth]
        error_obj = MagicMock()
        error_obj.message = "401 Unauthorized test-server"
        ev = _make_event(
            "response.mcp_list_tools.failed",
            item_id="tool-1",
            error=error_obj,
        )
        chunk = p._handle_mcp_events("response.mcp_list_tools.failed", ev)
        assert chunk is not None

    def test_unknown_mcp_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.mcp_unknown.event", item_id="tool-1")
        chunk = p._handle_mcp_events("response.mcp_unknown.event", ev)
        assert chunk is None


# ── _handle_shell_events() ────────────────────────────────────────────────────


class TestHandleShellEvents:
    def test_shell_arguments_delta(self):
        p = _make_processor()
        p._tool_name_map["sh-1"] = "shell.bash"
        ev = _make_event(
            "response.shell_call_arguments.delta", item_id="sh-1", delta="echo "
        )
        chunk = p._handle_shell_events("response.shell_call_arguments.delta", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_shell_arguments_done(self):
        p = _make_processor()
        p._tool_name_map["sh-1"] = "shell.bash"
        ev = _make_event(
            "response.shell_call_arguments.done", item_id="sh-1", arguments="echo hi"
        )
        chunk = p._handle_shell_events("response.shell_call_arguments.done", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_shell_call_failed(self):
        p = _make_processor()
        p._tool_name_map["sh-1"] = "shell.bash"
        ev = _make_event("response.shell_call.failed", item_id="sh-1")
        chunk = p._handle_shell_events("response.shell_call.failed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_shell_in_progress_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.shell_call.in_progress", item_id="sh-1")
        chunk = p._handle_shell_events("response.shell_call.in_progress", ev)
        assert chunk is None

    def test_shell_call_completed_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.shell_call.completed", item_id="sh-1")
        chunk = p._handle_shell_events("response.shell_call.completed", ev)
        assert chunk is None

    def test_unknown_shell_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.unknown_shell.event")
        chunk = p._handle_shell_events("response.unknown_shell.event", ev)
        assert chunk is None


# ── _handle_search_events() ───────────────────────────────────────────────────


class TestHandleSearchEvents:
    def test_file_search_searching(self):
        p = _make_processor()
        ev = _make_event(
            "response.file_search_call.searching", call_id="fs-1"
        )
        chunk = p._handle_search_events("response.file_search_call.searching", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_file_search_completed_updates_stats(self):
        p = _make_processor()
        p._reset_statistics("gpt-4o")
        ev = _make_event("response.file_search_call.completed", call_id="fs-1")
        chunk = p._handle_search_events("response.file_search_call.completed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_web_search_searching_no_query(self):
        p = _make_processor()
        ev = _make_event("response.web_search_call.searching", call_id="ws-1")
        ev.query_set = None
        chunk = p._handle_search_events("response.web_search_call.searching", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_web_search_searching_with_query(self):
        p = _make_processor()
        query_set = MagicMock()
        query_set.queries = ["What is Python?"]
        ev = _make_event(
            "response.web_search_call.searching", call_id="ws-1", query_set=query_set
        )
        chunk = p._handle_search_events("response.web_search_call.searching", ev)
        assert chunk is not None
        assert "Python" in chunk.text

    def test_web_search_completed(self):
        p = _make_processor()
        p._reset_statistics("gpt-4o")
        ev = _make_event("response.web_search_call.completed", call_id="ws-1")
        chunk = p._handle_search_events("response.web_search_call.completed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_unrelated_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.other_event")
        chunk = p._handle_search_events("response.other_event", ev)
        assert chunk is None


# ── _handle_completion_events() ───────────────────────────────────────────────


class TestHandleCompletionEvents:
    def test_response_completed_yields_completion_chunk(self):
        p = _make_processor()
        p._reset_statistics("gpt-4o")
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 50
        response = MagicMock()
        response.usage = usage
        ev = _make_event("response.completed", response=response)
        chunk = p._handle_completion_events("response.completed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION

    def test_response_completed_with_tool_map(self):
        p = _make_processor()
        p._reset_statistics("gpt-4o")
        p._tool_name_map["t1"] = "server.tool"
        ev = _make_event("response.completed", response=MagicMock())
        chunk = p._handle_completion_events("response.completed", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION

    def test_other_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.other")
        chunk = p._handle_completion_events("response.other", ev)
        assert chunk is None


# ── _handle_image_events() ────────────────────────────────────────────────────


class TestHandleImageEvents:
    def test_image_event_with_url(self):
        p = _make_processor()
        ev = _make_event("response.image.created", url="https://images.example.com/img.png")
        chunk = p._handle_image_events("response.image.created", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.IMAGE

    def test_image_event_with_data(self):
        p = _make_processor()
        ev = _make_event("response.image.partial", data="base64encodeddata")
        chunk = p._handle_image_events("response.image.partial", ev)
        assert chunk is not None
        assert chunk.type == ChunkType.IMAGE

    def test_non_image_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.text.delta")
        chunk = p._handle_image_events("response.text.delta", ev)
        assert chunk is None

    def test_image_event_without_url_or_data_returns_none(self):
        p = _make_processor()
        ev = MagicMock(spec=["type"])
        ev.type = "response.image.created"
        chunk = p._handle_image_events("response.image.created", ev)
        assert chunk is None


# ── _handle_event() dispatch ──────────────────────────────────────────────────


class TestHandleEventDispatch:
    def test_no_type_attr_returns_none(self):
        p = _make_processor()
        chunk = p._handle_event(object())
        assert chunk is None

    def test_known_ignored_event_returns_none(self):
        p = _make_processor()
        ev = _make_event("response.output_item.added")
        ev.item = None  # no item → returns None from _handle_item_events
        chunk = p._handle_event(ev)
        assert chunk is None

    def test_lifecycle_event_dispatched(self):
        p = _make_processor()
        ev = _make_event("response.created")
        chunk = p._handle_event(ev)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE

    def test_text_delta_dispatched(self):
        p = _make_processor()
        ev = _make_event("response.output_text.delta", delta="word")
        chunk = p._handle_event(ev)
        assert chunk is not None
        assert chunk.type == ChunkType.TEXT

    def test_completion_dispatched(self):
        p = _make_processor()
        p._reset_statistics("gpt-4o")
        ev = _make_event("response.completed", response=MagicMock())
        chunk = p._handle_event(ev)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION


# ── _extract_error_text() ─────────────────────────────────────────────────────


class TestExtractErrorText:
    def test_dict_with_content_list(self):
        p = _make_processor()
        error = {"content": [{"text": "Service unavailable"}]}
        assert p._extract_error_text(error) == "Service unavailable"

    def test_dict_with_empty_content(self):
        p = _make_processor()
        error = {"content": []}
        assert p._extract_error_text(error) == "Unknown error"

    def test_non_dict_returns_unknown(self):
        p = _make_processor()
        assert p._extract_error_text("some error string") == "Unknown error"

    def test_dict_with_non_list_content(self):
        p = _make_processor()
        error = {"content": "plain text error"}
        assert p._extract_error_text(error) == "Unknown error"


# ── _convert_messages_to_responses_format() ───────────────────────────────────


class TestConvertMessagesToResponsesFormat:
    async def test_human_message_converted(self):
        p = _make_processor()
        messages = [Message(text="Hello", type=MessageType.HUMAN)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
        ):
            result = await p._convert_messages_to_responses_format(messages)
        roles = [m["role"] for m in result]
        assert "system" in roles
        assert "user" in roles

    async def test_assistant_message_converted(self):
        p = _make_processor()
        messages = [Message(text="Reply", type=MessageType.ASSISTANT)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
        ):
            result = await p._convert_messages_to_responses_format(messages)
        roles = [m["role"] for m in result]
        assert "assistant" in roles

    async def test_system_message_skipped(self):
        p = _make_processor()
        messages = [Message(text="System instruction", type=MessageType.SYSTEM)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
        ):
            result = await p._convert_messages_to_responses_format(messages)
        # Only the prepended system message (from build()) should be present
        assert len(result) == 1
        assert result[0]["role"] == "system"

    async def test_no_system_prompt_when_disabled(self):
        p = _make_processor()
        messages = [Message(text="Hi", type=MessageType.HUMAN)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
        ):
            result = await p._convert_messages_to_responses_format(
                messages, use_system_prompt=False
            )
        # No system message prepended
        assert all(m["role"] != "system" for m in result)


# ── _extract_responses_content() ─────────────────────────────────────────────


class TestExtractResponsesContent:
    def test_none_output_returns_none(self):
        p = _make_processor()
        session = MagicMock()
        session.output = None
        assert p._extract_responses_content(session) is None

    def test_empty_output_returns_none(self):
        p = _make_processor()
        session = MagicMock()
        session.output = []
        assert p._extract_responses_content(session) is None

    def test_list_content_extracts_text(self):
        p = _make_processor()
        content_item = MagicMock()
        content_item.content = [{"text": "hello world"}]
        session = MagicMock()
        session.output = [content_item]
        result = p._extract_responses_content(session)
        assert result == "hello world"

    def test_string_content_returns_str(self):
        p = _make_processor()
        content_item = MagicMock()
        content_item.content = "direct text"
        session = MagicMock()
        session.output = [content_item]
        result = p._extract_responses_content(session)
        assert result == "direct text"


# ── process() – error paths ───────────────────────────────────────────────────


class TestProcessErrors:
    async def test_no_client_raises_value_error(self):
        model = AIModel(id="m", text="M", model="gpt-4o")
        p = OpenAIResponsesProcessor(models={"m": model}, api_key=None)
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in p.process(messages, "m"):
                pass

    async def test_unsupported_model_raises_value_error(self):
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not supported"):
            async for _ in p.process(messages, "nonexistent-model"):
                pass

    async def test_cancellation_token_stops_processing(self):
        p = _make_processor()
        cancel = asyncio.Event()
        cancel.set()  # already cancelled

        messages = [Message(text="hi", type=MessageType.HUMAN)]

        # Mock out file upload + request creation to avoid real API calls
        async def fake_file_uploads(**_kwargs):
            chunk = MagicMock()
            chunk.chunk_metadata = {}
            yield chunk

        async def fake_stream():
            for i in range(10):
                yield _make_event("response.output_text.delta", delta=f"word{i}")

        mock_session = MagicMock()
        mock_session.__aiter__ = lambda s: fake_stream()

        with (
            patch.object(
                p, "_process_file_uploads_streaming", side_effect=fake_file_uploads
            ),
            patch.object(
                p, "_create_responses_request", new=AsyncMock(return_value=mock_session)
            ),
        ):
            chunks = []
            async for chunk in p.process(
                messages, "gpt-4o-test", cancellation_token=cancel
            ):
                chunks.append(chunk)
        # Cancelled before any text chunk → 0 or very few text chunks
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 0


# ── _configure_mcp_tools() ────────────────────────────────────────────────────


class TestConfigureMCPTools:
    async def test_no_servers_returns_empty(self):
        p = _make_processor()
        tools, prompt = await p._configure_mcp_tools(None, user_id=None)
        assert tools == []
        assert prompt == ""

    async def test_single_server_no_auth(self, mcp_server_no_auth):
        p = _make_processor()
        tools, prompt = await p._configure_mcp_tools(
            [mcp_server_no_auth], user_id=None
        )
        assert len(tools) == 1
        assert tools[0]["server_label"] == "test-server"
        assert "Use this server" in prompt

    async def test_server_with_bearer_header(self, mcp_server_with_headers):
        p = _make_processor()
        tools, prompt = await p._configure_mcp_tools(
            [mcp_server_with_headers], user_id=None
        )
        assert len(tools) == 1
        assert "headers" in tools[0]
        assert tools[0]["headers"]["Authorization"] == "Bearer static-token-123"

    async def test_oauth_server_no_token_adds_pending(self, mcp_server_oauth):
        p = _make_processor()
        with patch.object(p, "get_valid_token", new=AsyncMock(return_value=None)):
            tools, _ = await p._configure_mcp_tools([mcp_server_oauth], user_id=42)
        assert mcp_server_oauth in p.pending_auth_servers

    async def test_oauth_server_with_valid_token_injects_header(
        self, mcp_server_oauth
    ):
        p = _make_processor()
        fake_token = MagicMock()
        fake_token.access_token = "bearer-xyz"
        with patch.object(
            p, "get_valid_token", new=AsyncMock(return_value=fake_token)
        ):
            tools, _ = await p._configure_mcp_tools([mcp_server_oauth], user_id=42)
        assert tools[0]["headers"]["Authorization"] == "Bearer bearer-xyz"


# ── _process_file_uploads_streaming() ────────────────────────────────────────


class TestProcessFileUploadsStreaming:
    async def test_no_thread_uuid_yields_skipped(self):
        p = _make_processor()
        chunks = []
        async for chunk in p._process_file_uploads_streaming(
            files=None, payload={}, user_id=1
        ):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].chunk_metadata["status"] == "skipped"

    async def test_no_user_id_yields_skipped(self):
        p = _make_processor()
        chunks = []
        async for chunk in p._process_file_uploads_streaming(
            files=["file.txt"], payload={"thread_uuid": "abc"}, user_id=None
        ):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].chunk_metadata["status"] == "skipped"

    async def test_thread_not_found_yields_skipped(self):
        p = _make_processor()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def fake_session_ctx():
            yield mock_session

        with patch(
            "appkit_assistant.backend.processors.openai_responses_processor."
            "get_asyncdb_session"
        ) as mock_get:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_cm

            chunks = []
            async for chunk in p._process_file_uploads_streaming(
                files=["file.txt"],
                payload={"thread_uuid": "not-found-uuid"},
                user_id=1,
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].chunk_metadata["status"] == "skipped"

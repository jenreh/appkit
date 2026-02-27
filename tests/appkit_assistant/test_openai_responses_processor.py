# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for OpenAIResponsesProcessor.

Covers init, client creation, model support, event handlers,
message conversion, annotation extraction, and file upload flow.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.openai_responses_processor import (
    OpenAIResponsesProcessor,
)
from appkit_assistant.backend.schemas import (
    AIModel,
    ChunkType,
    Message,
    MessageType,
)

# ============================================================================
# Fixtures
# ============================================================================


def _model(model_id: str = "gpt-4o") -> AIModel:
    return AIModel(
        id=model_id,
        text=model_id,
        model=model_id,
        stream=True,
        temperature=0.7,
        supports_search=True,
    )


def _make_processor(
    api_key: str = "sk-test",
    base_url: str | None = None,
    on_azure: bool = False,
    models: dict[str, AIModel] | None = None,
) -> OpenAIResponsesProcessor:
    if models is None:
        models = {"gpt-4o": _model()}
    with (
        patch(
            "appkit_assistant.backend.processors.openai_responses_processor."
            "mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ),
        patch(
            "appkit_assistant.backend.processors.openai_responses_processor."
            "AsyncOpenAI",
        ) as mock_openai,
    ):
        mock_openai.return_value = MagicMock()
        return OpenAIResponsesProcessor(
            models=models,
            api_key=api_key,
            base_url=base_url,
            on_azure=on_azure,
        )


# ============================================================================
# Initialization & client creation
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = _make_processor()
        assert proc._processor_name == "openai_responses"
        assert proc.mcp_processor_name == "openai_responses"
        assert proc._client is not None
        assert proc._file_upload_service is not None

    def test_no_api_key(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.openai_responses_processor."
            "mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            proc = OpenAIResponsesProcessor(models={"m": _model()}, api_key=None)
        assert proc._client is None
        assert proc._file_upload_service is None

    def test_get_supported_models_with_key(self) -> None:
        proc = _make_processor()
        assert proc.get_supported_models() == proc.models

    def test_get_supported_models_no_key(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.openai_responses_processor."
            "mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            proc = OpenAIResponsesProcessor(models={"m": _model()}, api_key=None)
        assert proc.get_supported_models() == {}


class TestCreateClient:
    def test_standard(self) -> None:
        with (
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "AsyncOpenAI",
            ) as mock_cls,
        ):
            OpenAIResponsesProcessor(models={"m": _model()}, api_key="key")
            mock_cls.assert_called_once_with(api_key="key")

    def test_custom_base_url(self) -> None:
        with (
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "AsyncOpenAI",
            ) as mock_cls,
        ):
            OpenAIResponsesProcessor(
                models={"m": _model()},
                api_key="key",
                base_url="https://custom.api",
            )
            mock_cls.assert_called_once_with(
                api_key="key", base_url="https://custom.api"
            )

    def test_azure_base_url(self) -> None:
        with (
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(
                "appkit_assistant.backend.processors.openai_responses_processor."
                "AsyncOpenAI",
            ) as mock_cls,
        ):
            OpenAIResponsesProcessor(
                models={"m": _model()},
                api_key="key",
                base_url="https://azure.api",
                on_azure=True,
            )
            mock_cls.assert_called_once_with(
                api_key="key",
                base_url="https://azure.api/openai/v1",
                default_query={"api-version": "preview"},
            )


# ============================================================================
# _handle_event dispatch
# ============================================================================


class TestHandleEvent:
    def test_no_type_attr(self) -> None:
        proc = _make_processor()
        assert proc._handle_event(object()) is None

    def test_lifecycle_created(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="response.created")
        chunk = proc._handle_event(event)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE

    def test_text_delta(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="response.output_text.delta", delta="hello")
        chunk = proc._handle_event(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "hello"

    def test_unhandled_known_event(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="response.output_item.added", item=None)
        # Should return None (known but no-op event)
        assert proc._handle_event(event) is None

    def test_unhandled_unknown_event(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="some.future.event")
        assert proc._handle_event(event) is None


# ============================================================================
# Lifecycle events
# ============================================================================


class TestLifecycleEvents:
    @pytest.mark.parametrize(
        ("event_type", "expected_text"),
        [
            ("response.created", "created"),
            ("response.in_progress", "in_progress"),
            ("response.done", "done"),
        ],
    )
    def test_lifecycle(self, event_type: str, expected_text: str) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type=event_type)
        chunk = proc._handle_lifecycle_events(event_type, event)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE
        assert chunk.text == expected_text

    def test_unknown_lifecycle(self) -> None:
        proc = _make_processor()
        assert proc._handle_lifecycle_events("response.xyz", None) is None


# ============================================================================
# Text events
# ============================================================================


class TestTextEvents:
    def test_text_delta(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(delta="chunk text")
        chunk = proc._handle_text_events("response.output_text.delta", event)
        assert chunk is not None
        assert chunk.text == "chunk text"

    def test_annotation_added(self) -> None:
        proc = _make_processor()
        annotation = SimpleNamespace(
            type="url_citation", url="https://x.com", text=None
        )
        event = SimpleNamespace(annotation=annotation)
        chunk = proc._handle_text_events("response.output_text.annotation.added", event)
        assert chunk is not None
        assert chunk.type == ChunkType.ANNOTATION

    def test_unknown_text_event(self) -> None:
        proc = _make_processor()
        assert proc._handle_text_events("response.output_text.xyz", None) is None


# ============================================================================
# Annotation extraction
# ============================================================================


class TestExtractAnnotationText:
    def test_text_attribute(self) -> None:
        proc = _make_processor()
        ann = SimpleNamespace(text="[1]")
        assert proc._extract_annotation_text(ann) == "[1]"

    def test_url_citation(self) -> None:
        proc = _make_processor()
        ann = SimpleNamespace(type="url_citation", text=None, url="https://a.com")
        assert proc._extract_annotation_text(ann) == "https://a.com"

    def test_file_citation(self) -> None:
        proc = _make_processor()
        ann = SimpleNamespace(type="file_citation", text=None, filename="doc.pdf")
        assert proc._extract_annotation_text(ann) == "doc.pdf"

    def test_dict_annotation(self) -> None:
        proc = _make_processor()
        ann = {"type": "url_citation", "text": None, "url": "https://b.com"}
        assert proc._extract_annotation_text(ann) == "https://b.com"

    def test_unknown_type_fallback(self) -> None:
        proc = _make_processor()
        ann = SimpleNamespace(type="unknown", text=None)
        result = proc._extract_annotation_text(ann)
        assert "unknown" in result

    def test_no_type_falls_to_filename(self) -> None:
        proc = _make_processor()
        ann = SimpleNamespace(text=None, filename="report.pdf")
        # no type attr → falls to file_citation branch via `not ann_type`
        assert proc._extract_annotation_text(ann) == "report.pdf"


# ============================================================================
# Search events
# ============================================================================


class TestSearchEvents:
    def test_file_search_searching(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(call_id="fs1")
        chunk = proc._handle_file_search_event(
            "response.file_search_call.searching", event
        )
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_file_search_completed(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(call_id="fs1")
        chunk = proc._handle_file_search_event(
            "response.file_search_call.completed", event
        )
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_web_search_searching_with_queries(self) -> None:
        proc = _make_processor()
        qs = SimpleNamespace(queries=["python asyncio"])
        event = SimpleNamespace(call_id="ws1", query_set=qs)
        chunk = proc._handle_web_search_event(
            "response.web_search_call.searching", event
        )
        assert chunk is not None
        assert "python asyncio" in chunk.text

    def test_web_search_completed(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(call_id="ws1")
        chunk = proc._handle_web_search_event(
            "response.web_search_call.completed", event
        )
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_search_events_dispatch_file(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(call_id="fs1")
        chunk = proc._handle_search_events("response.file_search_call.completed", event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_search_events_dispatch_web(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(call_id="ws1")
        chunk = proc._handle_search_events("response.web_search_call.completed", event)
        assert chunk is not None

    def test_search_events_irrelevant(self) -> None:
        proc = _make_processor()
        assert proc._handle_search_events("response.text.delta", None) is None


# ============================================================================
# Item events
# ============================================================================


class TestItemEvents:
    def test_mcp_call_added(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="mcp_call", name="search", id="t1", server_label="GitHub"
        )
        chunk = proc._handle_item_added(item)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert "GitHub.search" in chunk.text
        assert proc._tool_name_map["t1"] == "GitHub.search"

    def test_shell_call_added(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="shell_call", name="bash", id="s1")
        chunk = proc._handle_item_added(item)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_function_call_added(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="function_call", name="get_weather", call_id="f1")
        chunk = proc._handle_item_added(item)
        assert chunk is not None
        assert "get_weather" in chunk.text

    def test_reasoning_added(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="reasoning", id="r1")
        chunk = proc._handle_item_added(item)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING
        assert proc.current_reasoning_session == "r1"

    def test_file_search_added_returns_none(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="file_search_call")
        assert proc._handle_item_added(item) is None

    def test_mcp_call_done_success(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="mcp_call",
            id="t1",
            name="search",
            server_label="GH",
            error=None,
            output="result",
        )
        chunk = proc._handle_item_done(item)
        assert chunk is not None
        assert chunk.text == "result"

    def test_mcp_call_done_error(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="mcp_call",
            id="t1",
            name="search",
            server_label="GH",
            error={"content": [{"text": "timeout"}]},
            output=None,
        )
        chunk = proc._handle_item_done(item)
        assert chunk is not None
        assert "timeout" in chunk.text
        assert chunk.chunk_metadata["error"] == "True"

    def test_function_call_done(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="function_call", call_id="f1", output="42")
        chunk = proc._handle_item_done(item)
        assert chunk is not None
        assert chunk.text == "42"

    def test_reasoning_done(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(type="reasoning", id="r1", summary=["step1"])
        chunk = proc._handle_item_done(item)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING_RESULT


# ============================================================================
# Shell events
# ============================================================================


class TestShellEvents:
    def test_shell_arguments_delta(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["s1"] = "shell.bash"
        event = SimpleNamespace(item_id="s1", delta="--flag")
        chunk = proc._handle_shell_events("response.shell_call_arguments.delta", event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_shell_arguments_done(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(item_id="s1", arguments='{"cmd": "ls"}')
        chunk = proc._handle_shell_events("response.shell_call_arguments.done", event)
        assert chunk is not None
        assert "Parameter" in chunk.text

    def test_shell_failed(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["s1"] = "shell.bash"
        event = SimpleNamespace(item_id="s1")
        chunk = proc._handle_shell_events("response.shell_call.failed", event)
        assert chunk is not None
        assert chunk.chunk_metadata["error"] == "True"

    def test_shell_in_progress_returns_none(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(item_id="s1")
        assert (
            proc._handle_shell_events("response.shell_call.in_progress", event) is None
        )


# ============================================================================
# MCP events
# ============================================================================


class TestMcpEvents:
    def test_arguments_delta(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["t1"] = "GH.search"
        event = SimpleNamespace(item_id="t1", delta='{"query":')
        chunk = proc._handle_mcp_events("response.mcp_call_arguments.delta", event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_arguments_done(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(item_id="t1", arguments='{"q": "test"}')
        chunk = proc._handle_mcp_events("response.mcp_call_arguments.done", event)
        assert chunk is not None
        assert "Parameter" in chunk.text

    def test_call_failed(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["t1"] = "GH.search"
        event = SimpleNamespace(item_id="t1")
        chunk = proc._handle_mcp_events("response.mcp_call.failed", event)
        assert chunk is not None
        assert chunk.chunk_metadata["error"] == "True"

    def test_list_tools_failed_with_auth(self) -> None:
        proc = _make_processor()
        server = MagicMock()
        server.name = "GitHub"
        server.id = 1
        proc._available_mcp_servers = [server]
        event = SimpleNamespace(item_id="t1", error="401 GitHub unauthorized")
        chunk = proc._handle_mcp_events("response.mcp_list_tools.failed", event)
        assert chunk is not None
        assert chunk.chunk_metadata["status"] == "auth_required"


# ============================================================================
# Completion events
# ============================================================================


class TestCompletionEvents:
    def test_response_completed_with_usage(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        response = SimpleNamespace(usage=usage)
        event = SimpleNamespace(type="response.completed", response=response)
        chunk = proc._handle_completion_events("response.completed", event)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION

    def test_response_completed_no_usage(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gpt-4o")
        event = SimpleNamespace(type="response.completed", response=None)
        chunk = proc._handle_completion_events("response.completed", event)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION

    def test_non_completion_event(self) -> None:
        proc = _make_processor()
        assert proc._handle_completion_events("response.xyz", None) is None


# ============================================================================
# Image events
# ============================================================================


class TestImageEvents:
    def test_image_event_with_url(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(url="https://img.test/a.png", data="")
        chunk = proc._handle_image_events("response.image.done", event)
        assert chunk is not None
        assert chunk.type == ChunkType.IMAGE

    def test_non_image_event(self) -> None:
        proc = _make_processor()
        assert proc._handle_image_events("response.text.delta", None) is None

    def test_image_event_no_attrs(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="response.image.delta")
        assert proc._handle_image_events("response.image.delta", event) is None


# ============================================================================
# Content / no-op events
# ============================================================================


class TestContentEvents:
    def test_always_returns_none(self) -> None:
        proc = _make_processor()
        assert proc._handle_content_events("response.content_part.added", None) is None


# ============================================================================
# _processing_chunk helper
# ============================================================================


class TestProcessingChunk:
    def test_creates_processing_chunk(self) -> None:
        proc = _make_processor()
        chunk = proc._processing_chunk("completed", "vs_abc")
        assert chunk.type == ChunkType.PROCESSING
        assert chunk.chunk_metadata["status"] == "completed"
        assert chunk.chunk_metadata["vector_store_id"] == "vs_abc"


# ============================================================================
# Message conversion
# ============================================================================


class TestConvertMessages:
    @pytest.mark.asyncio
    async def test_basic_messages(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.HUMAN, text="Hello"),
            Message(type=MessageType.ASSISTANT, text="Hi there"),
        ]
        with patch.object(
            proc._system_prompt_builder,
            "build",
            new_callable=AsyncMock,
            return_value="system prompt",
        ):
            result = await proc._convert_messages_to_responses_format(msgs)

        # system + 2 messages
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_skip_system_prompt(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hi")]
        result = await proc._convert_messages_to_responses_format(
            msgs, use_system_prompt=False
        )
        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_system_messages_filtered(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.SYSTEM, text="ignored"),
            Message(type=MessageType.HUMAN, text="Hello"),
        ]
        with patch.object(
            proc._system_prompt_builder,
            "build",
            new_callable=AsyncMock,
            return_value="system prompt",
        ):
            result = await proc._convert_messages_to_responses_format(msgs)

        # system + 1 user (SYSTEM message skipped)
        assert len(result) == 2


# ============================================================================
# Extract responses content
# ============================================================================


class TestExtractResponsesContent:
    def test_valid_output(self) -> None:
        proc = _make_processor()
        content_part = SimpleNamespace(content=[{"text": "result"}])
        session = SimpleNamespace(output=[content_part])
        assert proc._extract_responses_content(session) == "result"

    def test_no_output(self) -> None:
        proc = _make_processor()
        session = SimpleNamespace(output=None)
        assert proc._extract_responses_content(session) is None

    def test_empty_list(self) -> None:
        proc = _make_processor()
        session = SimpleNamespace(output=[])
        assert proc._extract_responses_content(session) is None

    def test_string_content(self) -> None:
        proc = _make_processor()
        content_part = SimpleNamespace(content="plain text")
        session = SimpleNamespace(output=[content_part])
        assert proc._extract_responses_content(session) == "plain text"

    def test_no_content_attr(self) -> None:
        proc = _make_processor()
        session = SimpleNamespace(output=[SimpleNamespace()])
        assert proc._extract_responses_content(session) is None


# ============================================================================
# Error text extraction
# ============================================================================


class TestExtractErrorText:
    def test_dict_with_content(self) -> None:
        proc = _make_processor()
        error = {"content": [{"text": "Not found"}]}
        assert proc._extract_error_text(error) == "Not found"

    def test_dict_empty_content(self) -> None:
        proc = _make_processor()
        error = {"content": []}
        assert proc._extract_error_text(error) == "Unknown error"

    def test_non_dict(self) -> None:
        proc = _make_processor()
        assert proc._extract_error_text("some error") == "Unknown error"


# ============================================================================
# Shell call done
# ============================================================================


class TestShellCallDone:
    def test_success(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="shell_call", id="s1", name="bash", error=None, output="ok"
        )
        chunk = proc._handle_shell_call_done(item)
        assert chunk is not None
        assert chunk.text == "ok"

    def test_error(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="shell_call",
            id="s1",
            name="bash",
            error={"content": [{"text": "fail"}]},
            output=None,
        )
        chunk = proc._handle_shell_call_done(item)
        assert chunk is not None
        assert "fail" in chunk.text
        assert chunk.chunk_metadata["error"] == "True"

    def test_no_output(self) -> None:
        proc = _make_processor()
        item = SimpleNamespace(
            type="shell_call", id="s1", name="bash", error=None, output=None
        )
        chunk = proc._handle_shell_call_done(item)
        assert "Shell erfolgreich" in chunk.text


# ============================================================================
# Configure MCP tools
# ============================================================================


class TestConfigureMcpTools:
    @pytest.mark.asyncio
    async def test_no_servers(self) -> None:
        proc = _make_processor()
        tools, prompt = await proc._configure_mcp_tools(None, None)
        assert tools == []
        assert prompt == ""

    @pytest.mark.asyncio
    async def test_server_with_headers(self) -> None:
        proc = _make_processor()
        server = MagicMock()
        server.name = "TestMCP"
        server.url = "https://mcp.test/sse"
        server.headers = '{"X-Key": "val"}'
        server.auth_type = None
        server.prompt = "Use search tool"
        tools, prompt = await proc._configure_mcp_tools([server], None)
        assert len(tools) == 1
        assert tools[0]["server_label"] == "TestMCP"
        assert tools[0]["headers"]["X-Key"] == "val"
        assert "Use search" in prompt

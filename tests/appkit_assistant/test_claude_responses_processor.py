# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ClaudeResponsesProcessor.

Covers init, client creation, model support, event handlers,
message conversion, header parsing, MCP tool configuration,
content block start/delta/stop, and file content blocks.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.claude_responses_processor import (
    ClaudeResponsesProcessor,
)
from appkit_assistant.backend.schemas import (
    AIModel,
    ChunkType,
    MCPAuthType,
    Message,
    MessageType,
)

# ============================================================================
# Helpers
# ============================================================================

_PATCH_PREFIX = "appkit_assistant.backend.processors.claude_responses_processor"


def _model(model_id: str = "claude-sonnet") -> AIModel:
    return AIModel(
        id=model_id,
        text=model_id,
        model=model_id,
        stream=True,
        temperature=0.7,
    )


def _make_processor(
    api_key: str = "sk-test",
    base_url: str | None = None,
    on_azure: bool = False,
    models: dict[str, AIModel] | None = None,
) -> ClaudeResponsesProcessor:
    if models is None:
        models = {"claude-sonnet": _model()}
    with (
        patch(
            f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ),
        patch(f"{_PATCH_PREFIX}.AsyncAnthropic") as mock_cls,
        patch(f"{_PATCH_PREFIX}.AsyncAnthropicFoundry"),
    ):
        mock_cls.return_value = MagicMock()
        return ClaudeResponsesProcessor(
            models=models,
            api_key=api_key,
            base_url=base_url,
            on_azure=on_azure,
        )


def _make_server(
    name: str = "TestMCP",
    url: str = "https://mcp.test/sse",
    headers: str | None = None,
    auth_type: str | None = None,
    prompt: str | None = None,
) -> MagicMock:
    server = MagicMock()
    server.name = name
    server.url = url
    server.headers = headers
    server.auth_type = auth_type
    server.prompt = prompt
    return server


# ============================================================================
# Initialization & client creation
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = _make_processor()
        assert proc._processor_name == "claude_responses"
        assert proc.client is not None

    def test_no_api_key(self) -> None:
        with patch(
            f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            proc = ClaudeResponsesProcessor(models={"m": _model()}, api_key=None)
        assert proc.client is None

    def test_get_supported_models_with_key(self) -> None:
        proc = _make_processor()
        assert proc.get_supported_models() == proc.models

    def test_get_supported_models_no_key(self) -> None:
        with patch(
            f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            proc = ClaudeResponsesProcessor(models={"m": _model()}, api_key=None)
        assert proc.get_supported_models() == {}


class TestCreateClient:
    def test_standard(self) -> None:
        with (
            patch(
                f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(f"{_PATCH_PREFIX}.AsyncAnthropic") as mock_cls,
        ):
            ClaudeResponsesProcessor(models={"m": _model()}, api_key="key")
            mock_cls.assert_called_once_with(api_key="key")

    def test_with_base_url(self) -> None:
        with (
            patch(
                f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(f"{_PATCH_PREFIX}.AsyncAnthropic") as mock_cls,
        ):
            ClaudeResponsesProcessor(
                models={"m": _model()},
                api_key="key",
                base_url="https://custom.api",
            )
            mock_cls.assert_called_once_with(
                api_key="key", base_url="https://custom.api"
            )

    def test_azure_foundry(self) -> None:
        with (
            patch(
                f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(f"{_PATCH_PREFIX}.AsyncAnthropicFoundry") as mock_cls,
        ):
            ClaudeResponsesProcessor(
                models={"m": _model()},
                api_key="key",
                base_url="https://azure.api",
                on_azure=True,
            )
            mock_cls.assert_called_once_with(
                api_key="key",
                base_url="https://azure.api/anthropic",
            )

    def test_azure_no_base_url(self) -> None:
        with (
            patch(
                f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
                return_value="https://test/cb",
            ),
            patch(f"{_PATCH_PREFIX}.AsyncAnthropicFoundry") as mock_cls,
        ):
            ClaudeResponsesProcessor(
                models={"m": _model()},
                api_key="key",
                on_azure=True,
            )
            mock_cls.assert_called_once_with(api_key="key")


# ============================================================================
# _handle_event dispatch
# ============================================================================


class TestHandleEvent:
    def test_message_start(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="message_start")
        chunk = proc._handle_event(event)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE

    def test_message_delta_stop_reason(self) -> None:
        proc = _make_processor()
        delta = SimpleNamespace(stop_reason="end_turn")
        event = SimpleNamespace(type="message_delta", delta=delta)
        chunk = proc._handle_event(event)
        assert chunk is not None
        assert "end_turn" in chunk.text

    def test_message_delta_no_stop(self) -> None:
        proc = _make_processor()
        delta = SimpleNamespace(stop_reason=None)
        event = SimpleNamespace(type="message_delta", delta=delta)
        assert proc._handle_event(event) is None

    def test_message_stop_with_usage(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("claude-sonnet")
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        message = SimpleNamespace(usage=usage)
        event = SimpleNamespace(type="message_stop", message=message)
        chunk = proc._handle_event(event)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION


# ============================================================================
# Content block start
# ============================================================================


class TestContentBlockStart:
    def test_text_block_no_separator(self) -> None:
        proc = _make_processor()
        proc._needs_text_separator = False
        block = SimpleNamespace(type="text")
        event = SimpleNamespace(type="content_block_start", content_block=block)
        assert proc._handle_content_block_start(event) is None

    def test_text_block_with_separator(self) -> None:
        proc = _make_processor()
        proc._needs_text_separator = True
        block = SimpleNamespace(type="text")
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.text == "\n\n"
        assert proc._needs_text_separator is False

    def test_thinking_block(self) -> None:
        proc = _make_processor()
        block = SimpleNamespace(type="thinking", id="think1")
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING
        assert proc.current_reasoning_session == "think1"

    def test_tool_use_block(self) -> None:
        proc = _make_processor()
        block = SimpleNamespace(type="tool_use", name="search", id="t1")
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert proc._tool_name_map["t1"] == ("search", None)

    def test_mcp_tool_use_block(self) -> None:
        proc = _make_processor()
        block = SimpleNamespace(
            type="mcp_tool_use",
            name="search",
            id="t2",
            server_name="GitHub",
        )
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert "GitHub.search" in chunk.text
        assert proc._tool_name_map["t2"] == ("search", "GitHub")

    def test_mcp_tool_result_success(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["t1"] = ("search", "GitHub")
        block = SimpleNamespace(
            type="mcp_tool_result",
            tool_use_id="t1",
            is_error=False,
            content=[{"text": "found 5 results"}],
        )
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT
        assert "found 5 results" in chunk.text

    def test_mcp_tool_result_error(self) -> None:
        proc = _make_processor()
        proc._tool_name_map["t1"] = ("search", "GitHub")
        block = SimpleNamespace(
            type="mcp_tool_result",
            tool_use_id="t1",
            is_error=True,
            content=None,
        )
        event = SimpleNamespace(type="content_block_start", content_block=block)
        chunk = proc._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.chunk_metadata["error"] == "True"

    def test_no_content_block(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="content_block_start")
        assert proc._handle_content_block_start(event) is None

    def test_unknown_block_type(self) -> None:
        proc = _make_processor()
        block = SimpleNamespace(type="unknown")
        event = SimpleNamespace(type="content_block_start", content_block=block)
        assert proc._handle_content_block_start(event) is None


# ============================================================================
# Content block delta
# ============================================================================


class TestContentBlockDelta:
    def test_text_delta(self) -> None:
        proc = _make_processor()
        delta = SimpleNamespace(type="text_delta", text="hello world")
        event = SimpleNamespace(type="content_block_delta", delta=delta)
        chunk = proc._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.text == "hello world"

    def test_thinking_delta(self) -> None:
        proc = _make_processor()
        proc.current_reasoning_session = "think1"
        delta = SimpleNamespace(type="thinking_delta", thinking="hmm...")
        event = SimpleNamespace(type="content_block_delta", delta=delta)
        chunk = proc._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING
        assert chunk.text == "hmm..."

    def test_input_json_delta(self) -> None:
        proc = _make_processor()
        proc._current_tool_context = {
            "tool_name": "search",
            "tool_id": "t1",
            "server_label": "GH",
        }
        delta = SimpleNamespace(type="input_json_delta", partial_json='{"q": "test"}')
        event = SimpleNamespace(type="content_block_delta", delta=delta)
        chunk = proc._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_no_delta(self) -> None:
        proc = _make_processor()
        event = SimpleNamespace(type="content_block_delta")
        assert proc._handle_content_block_delta(event) is None

    def test_unknown_delta(self) -> None:
        proc = _make_processor()
        delta = SimpleNamespace(type="unknown_delta")
        event = SimpleNamespace(type="content_block_delta", delta=delta)
        assert proc._handle_content_block_delta(event) is None


# ============================================================================
# Content block stop
# ============================================================================


class TestContentBlockStop:
    def test_reasoning_stop(self) -> None:
        proc = _make_processor()
        proc.current_reasoning_session = "think1"
        event = SimpleNamespace(type="content_block_stop")
        chunk = proc._handle_content_block_stop(event)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING_RESULT
        assert proc.current_reasoning_session is None

    def test_tool_context_stop(self) -> None:
        proc = _make_processor()
        proc.current_reasoning_session = None
        proc._current_tool_context = {
            "tool_name": "search",
            "tool_id": "t1",
            "server_label": "GH",
        }
        event = SimpleNamespace(type="content_block_stop")
        chunk = proc._handle_content_block_stop(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert proc._current_tool_context is None

    def test_nothing_active(self) -> None:
        proc = _make_processor()
        proc.current_reasoning_session = None
        proc._current_tool_context = None
        event = SimpleNamespace(type="content_block_stop")
        assert proc._handle_content_block_stop(event) is None


# ============================================================================
# _parse_mcp_headers
# ============================================================================


class TestParseMcpHeaders:
    def test_no_headers(self) -> None:
        proc = _make_processor()
        server = _make_server(headers=None)
        token, suffix = proc._parse_mcp_headers(server)
        assert token is None
        assert suffix == ""

    def test_empty_headers(self) -> None:
        proc = _make_processor()
        server = _make_server(headers="{}")
        token, suffix = proc._parse_mcp_headers(server)
        assert token is None
        assert suffix == ""

    def test_bearer_token(self) -> None:
        proc = _make_processor()
        server = _make_server(headers=json.dumps({"Authorization": "Bearer my-token"}))
        token, suffix = proc._parse_mcp_headers(server)
        assert token == "my-token"
        assert suffix == ""

    def test_raw_auth_header(self) -> None:
        proc = _make_processor()
        server = _make_server(headers=json.dumps({"Authorization": "Basic abc"}))
        token, _ = proc._parse_mcp_headers(server)
        assert token == "Basic abc"

    def test_custom_headers_as_query_params(self) -> None:
        proc = _make_processor()
        server = _make_server(headers=json.dumps({"X-Project-ID": "123"}))
        _, suffix = proc._parse_mcp_headers(server)
        assert "project_id=123" in suffix

    def test_invalid_json(self) -> None:
        proc = _make_processor()
        server = _make_server(headers="not-json")
        token, suffix = proc._parse_mcp_headers(server)
        assert token is None
        assert suffix == ""


# ============================================================================
# _extract_mcp_result_text
# ============================================================================


class TestExtractMcpResultText:
    def test_none(self) -> None:
        proc = _make_processor()
        assert proc._extract_mcp_result_text(None) == ""

    def test_string(self) -> None:
        proc = _make_processor()
        assert proc._extract_mcp_result_text("plain") == "plain"

    def test_list_of_dicts(self) -> None:
        proc = _make_processor()
        content = [{"text": "a"}, {"text": "b"}]
        assert proc._extract_mcp_result_text(content) == "ab"

    def test_list_of_objects(self) -> None:
        proc = _make_processor()
        content = [SimpleNamespace(text="x"), SimpleNamespace(text="y")]
        assert proc._extract_mcp_result_text(content) == "xy"


# ============================================================================
# Message conversion
# ============================================================================


class TestConvertMessages:
    @pytest.mark.asyncio
    async def test_basic_messages(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.HUMAN, text="Hello"),
            Message(type=MessageType.ASSISTANT, text="Hi"),
        ]
        result = await proc._convert_messages_to_claude_format(msgs)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_system_messages_filtered(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.SYSTEM, text="sys"),
            Message(type=MessageType.HUMAN, text="Hello"),
        ]
        result = await proc._convert_messages_to_claude_format(msgs)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_files_attached_to_last_user(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Analyze")]
        files = [{"type": "image", "source": {"type": "base64"}}]
        result = await proc._convert_messages_to_claude_format(
            msgs, file_content_blocks=files
        )
        assert len(result) == 1
        # With file, content is a list
        assert isinstance(result[0]["content"], list)
        assert len(result[0]["content"]) == 2  # file + text


# ============================================================================
# Configure MCP tools
# ============================================================================


class TestConfigureMcpTools:
    @pytest.mark.asyncio
    async def test_no_servers(self) -> None:
        proc = _make_processor()
        tools, configs, prompt = await proc._configure_mcp_tools(None)
        assert tools == []
        assert configs == []
        assert prompt == ""

    @pytest.mark.asyncio
    async def test_server_with_bearer(self) -> None:
        proc = _make_processor()
        server = _make_server(
            headers=json.dumps({"Authorization": "Bearer token"}),
        )
        tools, configs, _prompt = await proc._configure_mcp_tools([server], None)
        assert len(tools) == 1
        assert tools[0]["type"] == "mcp_toolset"
        assert configs[0]["authorization_token"] == "token"

    @pytest.mark.asyncio
    async def test_server_with_custom_headers_skipped(self) -> None:
        proc = _make_processor()
        server = _make_server(
            headers=json.dumps({"X-API-Key": "val"}),
        )
        tools, configs, _ = await proc._configure_mcp_tools([server], None)
        # Server with custom headers should be skipped (warning issued)
        assert len(tools) == 0
        assert len(configs) == 0
        assert len(proc._mcp_warnings) == 1

    @pytest.mark.asyncio
    async def test_oauth_with_token(self) -> None:
        proc = _make_processor()
        server = _make_server(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            headers="{}",
        )
        mock_token = MagicMock()
        mock_token.access_token = "oauth-tok"
        proc._mcp_token_service.get_valid_token = AsyncMock(return_value=mock_token)
        _, configs, _ = await proc._configure_mcp_tools([server], 1)
        assert configs[0]["authorization_token"] == "oauth-tok"

    @pytest.mark.asyncio
    async def test_prompts_joined(self) -> None:
        proc = _make_processor()
        s1 = _make_server(name="S1", headers="{}", prompt="p1")
        s2 = _make_server(name="S2", headers="{}", prompt="p2")
        _, _, prompt = await proc._configure_mcp_tools([s1, s2], None)
        assert "- p1" in prompt
        assert "- p2" in prompt

    @pytest.mark.asyncio
    async def test_oauth_no_token_adds_pending(self) -> None:
        proc = _make_processor()
        server = _make_server(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            headers="{}",
        )
        proc._mcp_token_service.get_valid_token = AsyncMock(return_value=None)
        _, configs, _ = await proc._configure_mcp_tools([server], 1)
        assert len(configs) == 1
        assert proc.pending_auth_servers


# ============================================================================
# process() full flow
# ============================================================================


class TestProcessFlow:
    @pytest.mark.asyncio
    async def test_process_validation_no_client(self) -> None:
        with patch(
            f"{_PATCH_PREFIX}.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            proc = ClaudeResponsesProcessor(models={"m": _model()}, api_key=None)
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in proc.process([], "m"):
                pass

    @pytest.mark.asyncio
    async def test_process_validation_unknown_model(self) -> None:
        proc = _make_processor()
        with pytest.raises(ValueError, match="not supported"):
            async for _ in proc.process([], "nonexistent"):
                pass

    @pytest.mark.asyncio
    async def test_process_streaming_basic(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]

        # Build mock streaming response
        message_start = SimpleNamespace(type="message_start")
        text_delta = SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="Response"),
        )
        message_stop = SimpleNamespace(
            type="message_stop",
            message=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            ),
        )

        async def _mock_events():
            for e in [message_start, text_delta, message_stop]:
                yield e

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_mock_events())
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        proc._create_messages_request = AsyncMock(return_value=mock_stream)

        chunks = [c async for c in proc.process(msgs, "claude-sonnet")]
        types_found = {c.type for c in chunks}
        assert ChunkType.LIFECYCLE in types_found
        assert ChunkType.TEXT in types_found
        assert ChunkType.COMPLETION in types_found

    @pytest.mark.asyncio
    async def test_process_with_cancellation(self) -> None:
        import asyncio

        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]
        cancel = asyncio.Event()

        call_count = 0

        async def _mock_events():
            nonlocal call_count
            yield SimpleNamespace(type="message_start")
            call_count += 1
            if call_count >= 1:
                cancel.set()
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(type="text_delta", text="Text"),
            )

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_mock_events())
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        proc._create_messages_request = AsyncMock(return_value=mock_stream)

        chunks = [
            c
            async for c in proc.process(
                msgs, "claude-sonnet", cancellation_token=cancel
            )
        ]
        # Should get message_start but stop before or at text_delta
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_process_with_mcp_warnings(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]

        async def _mock_events():
            yield SimpleNamespace(
                type="message_stop",
                message=SimpleNamespace(
                    usage=SimpleNamespace(input_tokens=0, output_tokens=0),
                ),
            )

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_mock_events())
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        # Simulate _create_messages_request setting warnings
        async def _create_request(*args, **kwargs):
            proc._mcp_warnings = ["Server X disabled"]
            return mock_stream

        proc._create_messages_request = AsyncMock(side_effect=_create_request)

        chunks = [c async for c in proc.process(msgs, "claude-sonnet")]
        warning_chunks = [c for c in chunks if "⚠️" in c.text]
        assert len(warning_chunks) == 1

    @pytest.mark.asyncio
    async def test_process_stream_error_yields_error_chunk(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]

        async def _fail_events():
            raise RuntimeError("stream broke")
            yield  # noqa: RET504

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_fail_events())
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        proc._create_messages_request = AsyncMock(return_value=mock_stream)

        chunks = [c async for c in proc.process(msgs, "claude-sonnet")]
        error_chunks = [c for c in chunks if c.type == ChunkType.ERROR]
        assert len(error_chunks) == 1

    @pytest.mark.asyncio
    async def test_process_stream_auth_error_no_error_chunk(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]

        async def _auth_error():
            raise RuntimeError("Unauthorized 401")
            yield  # noqa: RET504

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_auth_error())
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        proc._create_messages_request = AsyncMock(return_value=mock_stream)
        proc.auth_detector.is_auth_error = MagicMock(return_value=True)

        chunks = [c async for c in proc.process(msgs, "claude-sonnet")]
        error_chunks = [c for c in chunks if c.type == ChunkType.ERROR]
        assert len(error_chunks) == 0

    @pytest.mark.asyncio
    async def test_process_with_files(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Analyze")]

        proc._process_files = AsyncMock(
            return_value=[{"type": "image", "source": {"type": "base64"}}]
        )

        async def _mock_events():
            yield SimpleNamespace(
                type="message_stop",
                message=SimpleNamespace(
                    usage=SimpleNamespace(input_tokens=5, output_tokens=3),
                ),
            )

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=_mock_events())
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        proc._create_messages_request = AsyncMock(return_value=mock_stream)

        chunks = [
            c async for c in proc.process(msgs, "claude-sonnet", files=["test.png"])
        ]
        proc._process_files.assert_called_once_with(["test.png"])
        assert any(c.type == ChunkType.COMPLETION for c in chunks)


# ============================================================================
# _process_files
# ============================================================================


class TestProcessFiles:
    @pytest.mark.asyncio
    async def test_valid_file(self) -> None:
        proc = _make_processor()
        proc._file_validator.validate_file = MagicMock(return_value=(True, None))
        proc._create_file_content_block = AsyncMock(
            return_value={"type": "image", "source": {}}
        )

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.unlink = MagicMock()
            result = await proc._process_files(["/tmp/test.png"])  # noqa: S108

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invalid_file_skipped(self) -> None:
        proc = _make_processor()
        proc._file_validator.validate_file = MagicMock(
            return_value=(False, "Too large")
        )

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.unlink = MagicMock()
            result = await proc._process_files(["/tmp/bad.exe"])  # noqa: S108

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_file_processing_exception(self) -> None:
        proc = _make_processor()
        proc._file_validator.validate_file = MagicMock(return_value=(True, None))
        proc._create_file_content_block = AsyncMock(
            side_effect=RuntimeError("upload fail")
        )

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.unlink = MagicMock()
            result = await proc._process_files(["/tmp/test.pdf"])  # noqa: S108

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_file_cleanup_on_error(self) -> None:
        proc = _make_processor()
        proc._file_validator.validate_file = MagicMock(return_value=(True, None))
        proc._create_file_content_block = AsyncMock(return_value=None)

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_instance = MagicMock()
            mock_path.return_value = mock_instance
            await proc._process_files(["/tmp/test.txt"])  # noqa: S108
            mock_instance.unlink.assert_called_once_with(missing_ok=True)


# ============================================================================
# _create_file_content_block
# ============================================================================


class TestCreateFileContentBlock:
    @pytest.mark.asyncio
    async def test_image_file(self) -> None:
        proc = _make_processor()
        proc._file_validator.is_image_file = MagicMock(return_value=True)
        proc._file_validator.get_media_type = MagicMock(return_value="image/png")

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.read_bytes.return_value = b"PNG_DATA"
            result = await proc._create_file_content_block("/tmp/test.png")  # noqa: S108

        assert result is not None
        assert result["type"] == "image"
        assert result["source"]["type"] == "base64"
        assert result["source"]["media_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_document_file(self) -> None:
        proc = _make_processor()
        proc._file_validator.is_image_file = MagicMock(return_value=False)
        proc._file_validator.get_media_type = MagicMock(return_value="application/pdf")

        mock_upload = MagicMock()
        mock_upload.id = "file-123"
        proc.client.beta.files.upload = AsyncMock(return_value=mock_upload)

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.read_bytes.return_value = b"PDF_DATA"
            mock_path.return_value.name = "doc.pdf"
            result = await proc._create_file_content_block("/tmp/doc.pdf")  # noqa: S108

        assert result is not None
        assert result["type"] == "document"
        assert result["source"]["file_id"] == "file-123"
        assert result["citations"]["enabled"] is True
        assert "file-123" in proc._uploaded_file_ids

    @pytest.mark.asyncio
    async def test_document_upload_failure(self) -> None:
        proc = _make_processor()
        proc._file_validator.is_image_file = MagicMock(return_value=False)
        proc._file_validator.get_media_type = MagicMock(return_value="text/plain")
        proc.client.beta.files.upload = AsyncMock(
            side_effect=RuntimeError("Upload failed")
        )

        with patch(f"{_PATCH_PREFIX}.Path") as mock_path:
            mock_path.return_value.read_bytes.return_value = b"TEXT"
            mock_path.return_value.name = "file.txt"
            result = await proc._create_file_content_block("/tmp/file.txt")  # noqa: S108

        assert result is None


# ============================================================================
# _create_messages_request
# ============================================================================


class TestCreateMessagesRequest:
    @pytest.mark.asyncio
    async def test_basic_request(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]
        model = _model()

        proc._system_prompt_builder.build = AsyncMock(return_value="System prompt")
        proc.client.beta.messages.stream = MagicMock(return_value="stream_obj")

        result = await proc._create_messages_request(msgs, model)

        assert result == "stream_obj"
        call_kwargs = proc.client.beta.messages.stream.call_args
        params = call_kwargs.kwargs
        assert model.model in str(params)

    @pytest.mark.asyncio
    async def test_request_with_mcp_servers(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]
        model = _model()
        server = _make_server(headers="{}")

        proc._system_prompt_builder.build = AsyncMock(return_value="")
        proc.client.beta.messages.stream = MagicMock(return_value="stream_obj")

        await proc._create_messages_request(msgs, model, mcp_servers=[server])

        call_kwargs = proc.client.beta.messages.stream.call_args
        betas = call_kwargs.kwargs.get("betas", [])
        assert any("mcp" in b.lower() for b in betas)

    @pytest.mark.asyncio
    async def test_request_with_files(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Analyze")]
        model = _model()
        file_blocks = [{"type": "image", "source": {"type": "base64"}}]

        proc._system_prompt_builder.build = AsyncMock(return_value="")
        proc.client.beta.messages.stream = MagicMock(return_value="stream_obj")

        await proc._create_messages_request(
            msgs, model, file_content_blocks=file_blocks
        )

        call_kwargs = proc.client.beta.messages.stream.call_args
        betas = call_kwargs.kwargs.get("betas", [])
        assert any("file" in b.lower() for b in betas)

    @pytest.mark.asyncio
    async def test_request_with_payload(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]
        model = _model()

        proc._system_prompt_builder.build = AsyncMock(return_value="")
        proc.client.beta.messages.stream = MagicMock(return_value="stream_obj")

        await proc._create_messages_request(
            msgs, model, payload={"custom": "val", "thread_uuid": "skip-me"}
        )

        call_kwargs = proc.client.beta.messages.stream.call_args
        # thread_uuid should be filtered out
        assert "thread_uuid" not in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_request_with_temperature(self) -> None:
        proc = _make_processor()
        msgs = [Message(type=MessageType.HUMAN, text="Hello")]
        model = _model()
        model.temperature = 0.5

        proc._system_prompt_builder.build = AsyncMock(return_value="")
        proc.client.beta.messages.stream = MagicMock(return_value="stream_obj")

        await proc._create_messages_request(msgs, model)

        call_kwargs = proc.client.beta.messages.stream.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.5


# ============================================================================
# Text delta with citation content
# ============================================================================


class TestTextDeltaWithCitation:
    def test_citation_content(self) -> None:
        proc = _make_processor()
        delta = SimpleNamespace(
            type="citations_delta",
            citation=SimpleNamespace(
                cited_text="important fact",
                document_title="doc.pdf",
                start_char_index=0,
                end_char_index=14,
            ),
        )
        event = SimpleNamespace(type="content_block_delta", delta=delta)
        chunk = proc._handle_content_block_delta(event)
        # citations_delta should return an annotation or be handled
        if chunk is not None:
            assert chunk.type in {ChunkType.ANNOTATION, ChunkType.TEXT}

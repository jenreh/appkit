"""Tests for ClaudeResponsesProcessor.

Covers:
- Initialization (with/without API key, Azure mode, base_url)
- get_supported_models()
- _create_client() – standard, Azure, base_url variants
- _handle_event() dispatch (all event types via _get_event_handlers)
- _handle_message_start / delta / stop
- _handle_content_block_start (all block types)
- _handle_content_block_delta (text, thinking, input_json)
- _handle_content_block_stop (reasoning, tool context)
- _handle_text_block_start (separator logic)
- _handle_thinking_block_start
- _handle_tool_use_block_start, _handle_mcp_tool_use_block_start
- _handle_mcp_tool_result_block_start
- _extract_mcp_result_text
- _parse_mcp_headers() – auth token extraction, non-auth headers → query params
- _configure_mcp_tools() – no servers, no-auth server, OAuth with/without token
- _convert_messages_to_claude_format()
- _process_files() – file block creation
- process() – no client, unsupported model, cancellation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.claude_responses_processor import (
    ClaudeResponsesProcessor,
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


def _make_event(event_type: str, **kwargs) -> MagicMock:
    ev = MagicMock()
    ev.type = event_type
    for k, v in kwargs.items():
        setattr(ev, k, v)
    return ev


def _make_processor(
    api_key: str = "sk-ant-fake",
    base_url: str | None = None,
    on_azure: bool = False,
    model_id: str = "claude-test",
) -> ClaudeResponsesProcessor:
    model = AIModel(
        id=model_id,
        text="Claude Test",
        model="claude-3-5-sonnet-20241022",
        stream=True,
        temperature=1.0,
    )
    return ClaudeResponsesProcessor(
        models={model_id: model},
        api_key=api_key,
        base_url=base_url,
        on_azure=on_azure,
    )


# ── Initialization ─────────────────────────────────────────────────────────────


class TestClaudeProcessorInit:
    def test_init_with_api_key_creates_client(self):
        p = _make_processor()
        assert p.client is not None

    def test_init_without_api_key_no_client(self):
        model = AIModel(id="m", text="M", model="claude-3")
        p = ClaudeResponsesProcessor(models={"m": model}, api_key=None)
        assert p.client is None

    def test_init_empty_api_key_no_client(self):
        model = AIModel(id="m", text="M", model="claude-3")
        p = ClaudeResponsesProcessor(models={"m": model}, api_key="")
        assert p.client is None

    def test_processor_name(self):
        p = _make_processor()
        assert p._processor_name == "claude_responses"

    def test_initial_state(self):
        p = _make_processor()
        assert p._uploaded_file_ids == []
        assert p._current_tool_context is None
        assert p._needs_text_separator is False
        assert p._tool_name_map == {}
        assert p._mcp_warnings == []

    def test_get_supported_models_with_key(self):
        p = _make_processor()
        models = p.get_supported_models()
        assert "claude-test" in models

    def test_get_supported_models_without_key(self):
        model = AIModel(id="m", text="M", model="claude-3")
        p = ClaudeResponsesProcessor(models={"m": model}, api_key=None)
        assert p.get_supported_models() == {}


# ── _create_client() ──────────────────────────────────────────────────────────


class TestClaudeCreateClient:
    def test_standard_client(self):
        p = _make_processor()
        # Client already created in __init__ - just check type
        from anthropic import AsyncAnthropic
        assert isinstance(p.client, AsyncAnthropic)

    def test_azure_client(self):
        p = _make_processor(
            on_azure=True, api_key="key", base_url="https://resource.ai.azure.com"
        )
        from anthropic import AsyncAnthropicFoundry
        assert isinstance(p.client, AsyncAnthropicFoundry)

    def test_azure_with_base_url(self):
        p = _make_processor(
            on_azure=True, base_url="https://resource.ai.azure.com", api_key="key"
        )
        from anthropic import AsyncAnthropicFoundry
        assert isinstance(p.client, AsyncAnthropicFoundry)

    def test_base_url_client(self):
        p = _make_processor(base_url="https://proxy.example.com")
        from anthropic import AsyncAnthropic
        assert isinstance(p.client, AsyncAnthropic)

    def test_no_key_returns_none(self):
        model = AIModel(id="m", text="M", model="claude-3")
        p = ClaudeResponsesProcessor(models={"m": model}, api_key=None)
        p.api_key = None
        assert p._create_client() is None


# ── _handle_message_start / delta / stop ─────────────────────────────────────


class TestClaudeMessageHandlers:
    def test_message_start_yields_lifecycle(self):
        p = _make_processor()
        chunk = p._handle_message_start(MagicMock())
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE

    def test_message_delta_with_stop_reason(self):
        p = _make_processor()
        delta = MagicMock()
        delta.stop_reason = "end_turn"
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_message_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE
        assert "end_turn" in chunk.text

    def test_message_delta_no_delta(self):
        p = _make_processor()
        event = MagicMock()
        event.delta = None
        chunk = p._handle_message_delta(event)
        assert chunk is None

    def test_message_delta_no_stop_reason(self):
        p = _make_processor()
        delta = MagicMock()
        delta.stop_reason = None
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_message_delta(event)
        assert chunk is None

    def test_message_stop_yields_completion(self):
        p = _make_processor()
        p._reset_statistics("claude-test")
        usage = MagicMock()
        usage.input_tokens = 200
        usage.output_tokens = 80
        message = MagicMock()
        message.usage = usage
        event = MagicMock()
        event.message = message
        chunk = p._handle_message_stop(event)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION

    def test_message_stop_no_message(self):
        p = _make_processor()
        p._reset_statistics("claude-test")
        event = MagicMock()
        event.message = None
        chunk = p._handle_message_stop(event)
        assert chunk is not None
        assert chunk.type == ChunkType.COMPLETION


# ── _handle_content_block_start ───────────────────────────────────────────────


class TestClaudeContentBlockStart:
    def test_text_block_no_separator_needed(self):
        p = _make_processor()
        p._needs_text_separator = False
        block = MagicMock()
        block.type = "text"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is None  # no separator needed

    def test_text_block_with_separator(self):
        p = _make_processor()
        p._needs_text_separator = True
        block = MagicMock()
        block.type = "text"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TEXT
        assert p._needs_text_separator is False

    def test_thinking_block_start(self):
        p = _make_processor()
        block = MagicMock()
        block.type = "thinking"
        block.id = "think-1"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING
        assert p.current_reasoning_session == "think-1"
        assert p._needs_text_separator is True

    def test_tool_use_block_start(self):
        p = _make_processor()
        block = MagicMock()
        block.type = "tool_use"
        block.name = "my_function"
        block.id = "tool-1"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert "tool-1" in p._tool_name_map

    def test_mcp_tool_use_block_start(self):
        p = _make_processor()
        block = MagicMock()
        block.type = "mcp_tool_use"
        block.name = "mcp_tool"
        block.id = "mcp-1"
        block.server_name = "my-server"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert "my-server" in chunk.text or "mcp_tool" in chunk.text

    def test_mcp_tool_result_block_start_success(self):
        p = _make_processor()
        p._tool_name_map["mcp-1"] = ("mcp_tool", "server-1")
        block = MagicMock()
        block.type = "mcp_tool_result"
        block.tool_use_id = "mcp-1"
        block.is_error = False
        block.content = [{"type": "text", "text": "result text"}]
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT
        assert p._needs_text_separator is True

    def test_mcp_tool_result_block_start_error(self):
        p = _make_processor()
        block = MagicMock()
        block.type = "mcp_tool_result"
        block.tool_use_id = "unknown-id"
        block.is_error = True
        block.content = []
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_RESULT

    def test_unknown_block_type_returns_none(self):
        p = _make_processor()
        block = MagicMock()
        block.type = "unknown_block"
        event = MagicMock()
        event.content_block = block
        chunk = p._handle_content_block_start(event)
        assert chunk is None

    def test_no_content_block_returns_none(self):
        p = _make_processor()
        event = MagicMock()
        event.content_block = None
        chunk = p._handle_content_block_start(event)
        assert chunk is None


# ── _handle_content_block_delta ───────────────────────────────────────────────


class TestClaudeContentBlockDelta:
    def test_text_delta(self):
        p = _make_processor()
        delta = MagicMock()
        delta.type = "text_delta"
        delta.text = "hello world"
        event = MagicMock()
        event.delta = delta
        # Mock citation handler
        p._citation_handler.extract_citations = MagicMock(return_value=[])
        chunk = p._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TEXT
        assert chunk.text == "hello world"

    def test_text_delta_with_citations(self):
        p = _make_processor()
        delta = MagicMock()
        delta.type = "text_delta"
        delta.text = "see [1]"
        mock_citation = MagicMock()
        p._citation_handler.extract_citations = MagicMock(
            return_value=[mock_citation]
        )
        p._citation_handler.to_dict = MagicMock(
            return_value={"title": "Source", "url": "https://example.com"}
        )
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_content_block_delta(event)
        assert chunk is not None
        # Citations are serialized into the delta metadata value
        assert chunk.chunk_metadata is not None

    def test_thinking_delta(self):
        p = _make_processor()
        p.current_reasoning_session = "think-1"
        delta = MagicMock()
        delta.type = "thinking_delta"
        delta.thinking = "reasoning step..."
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING

    def test_input_json_delta(self):
        p = _make_processor()
        p._current_tool_context = {
            "tool_name": "my_tool",
            "tool_id": "t-1",
            "server_label": "srv",
        }
        delta = MagicMock()
        delta.type = "input_json_delta"
        delta.partial_json = '{"arg":'
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_input_json_delta_no_context(self):
        p = _make_processor()
        p._current_tool_context = None
        delta = MagicMock()
        delta.type = "input_json_delta"
        delta.partial_json = '{"arg":'
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_content_block_delta(event)
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL

    def test_no_delta_returns_none(self):
        p = _make_processor()
        event = MagicMock()
        event.delta = None
        chunk = p._handle_content_block_delta(event)
        assert chunk is None

    def test_unknown_delta_type_returns_none(self):
        p = _make_processor()
        delta = MagicMock()
        delta.type = "unknown_delta_type"
        event = MagicMock()
        event.delta = delta
        chunk = p._handle_content_block_delta(event)
        assert chunk is None


# ── _handle_content_block_stop ────────────────────────────────────────────────


class TestClaudeContentBlockStop:
    def test_stop_with_reasoning_session_yields_thinking_result(self):
        p = _make_processor()
        p.current_reasoning_session = "think-1"
        chunk = p._handle_content_block_stop(MagicMock())
        assert chunk is not None
        assert chunk.type == ChunkType.THINKING_RESULT
        assert p.current_reasoning_session is None

    def test_stop_with_tool_context_yields_tool_call(self):
        p = _make_processor()
        p.current_reasoning_session = None
        p._current_tool_context = {
            "tool_name": "my_tool",
            "tool_id": "t-1",
            "server_label": None,
        }
        chunk = p._handle_content_block_stop(MagicMock())
        assert chunk is not None
        assert chunk.type == ChunkType.TOOL_CALL
        assert p._current_tool_context is None

    def test_stop_no_context_returns_none(self):
        p = _make_processor()
        p.current_reasoning_session = None
        p._current_tool_context = None
        chunk = p._handle_content_block_stop(MagicMock())
        assert chunk is None


# ── _extract_mcp_result_text ──────────────────────────────────────────────────


class TestExtractMCPResultText:
    def test_none_content_returns_empty(self):
        p = _make_processor()
        assert p._extract_mcp_result_text(None) == ""

    def test_non_list_returns_str(self):
        p = _make_processor()
        assert p._extract_mcp_result_text("plain text") == "plain text"

    def test_list_of_dicts_joins_text(self):
        p = _make_processor()
        content = [{"text": "part1"}, {"text": "part2"}]
        result = p._extract_mcp_result_text(content)
        assert result == "part1part2"

    def test_list_of_objects_with_text_attr(self):
        p = _make_processor()
        item = MagicMock()
        item.text = "from object"
        result = p._extract_mcp_result_text([item])
        assert result == "from object"

    def test_empty_list_returns_empty(self):
        p = _make_processor()
        assert p._extract_mcp_result_text([]) == ""


# ── _parse_mcp_headers() ─────────────────────────────────────────────────────


class TestParseMCPHeaders:
    def test_no_headers_returns_empty(self, mcp_server_no_auth):
        p = _make_processor()
        token, query = p._parse_mcp_headers(mcp_server_no_auth)
        assert token is None
        assert query == ""

    def test_bearer_token_extracted(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server = MCPServer(
            name="s",
            url="https://x.com",
            headers='{"Authorization": "Bearer my-secret-token"}',
            auth_type="none",
        )
        token, query = p._parse_mcp_headers(server)
        assert token == "my-secret-token"
        assert query == ""

    def test_raw_auth_header_extracted(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server = MCPServer(
            name="s",
            url="https://x.com",
            headers='{"Authorization": "Basic dXNlcjpwYXNz"}',
            auth_type="none",
        )
        token, query = p._parse_mcp_headers(server)
        assert token == "Basic dXNlcjpwYXNz"

    def test_custom_headers_become_query_params(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server = MCPServer(
            name="s",
            url="https://x.com",
            headers='{"X-Project-ID": "proj-123", "X-Tenant": "t1"}',
            auth_type="none",
        )
        token, query = p._parse_mcp_headers(server)
        assert token is None
        assert "project_id=proj-123" in query
        assert "tenant=t1" in query

    def test_invalid_json_headers_returns_empty(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server = MCPServer(
            name="s", url="https://x.com", headers="INVALID{JSON}", auth_type="none"
        )
        token, query = p._parse_mcp_headers(server)
        assert token is None
        assert query == ""

    def test_empty_headers_string_returns_empty(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server = MCPServer(
            name="s", url="https://x.com", headers="{}", auth_type="none"
        )
        token, query = p._parse_mcp_headers(server)
        assert token is None
        assert query == ""


# ── _configure_mcp_tools() ────────────────────────────────────────────────────


class TestClaudeConfigureMCPTools:
    async def test_no_servers_returns_empty(self):
        p = _make_processor()
        tools, server_configs, prompt = await p._configure_mcp_tools(None, None)
        assert tools == []
        assert server_configs == []
        assert prompt == ""

    async def test_server_with_auth_token(self, mcp_server_with_headers):
        p = _make_processor()
        tools, server_configs, prompt = await p._configure_mcp_tools(
            [mcp_server_with_headers], user_id=None
        )
        assert len(tools) == 1
        assert tools[0]["type"] == "mcp_toolset"
        assert len(server_configs) == 1
        assert server_configs[0]["authorization_token"] == "static-token-123"

    async def test_server_with_query_suffix_is_skipped_with_warning(self):
        p = _make_processor()
        from appkit_assistant.backend.database.models import MCPServer
        server_with_custom_header = MCPServer(
            name="custom",
            url="https://x.com",
            headers='{"X-Custom": "value"}',
            auth_type="none",
        )
        tools, server_configs, prompt = await p._configure_mcp_tools(
            [server_with_custom_header], user_id=None
        )
        # Server with custom headers gets warned and skipped
        assert tools == []
        assert server_configs == []
        assert len(p._mcp_warnings) == 1

    async def test_oauth_server_with_token(self, mcp_server_oauth):
        p = _make_processor()
        fake_token = MagicMock()
        fake_token.access_token = "oauth-token-xyz"
        with patch.object(p, "get_valid_token", new=AsyncMock(return_value=fake_token)):
            tools, server_configs, prompt = await p._configure_mcp_tools(
                [mcp_server_oauth], user_id=42
            )
        assert len(server_configs) == 1
        assert server_configs[0]["authorization_token"] == "oauth-token-xyz"

    async def test_oauth_server_no_token_adds_pending(self, mcp_server_oauth):
        p = _make_processor()
        with patch.object(p, "get_valid_token", new=AsyncMock(return_value=None)):
            tools, server_configs, prompt = await p._configure_mcp_tools(
                [mcp_server_oauth], user_id=42
            )
        assert mcp_server_oauth in p.pending_auth_servers

    async def test_server_prompt_included(self, mcp_server_no_auth):
        p = _make_processor()
        tools, server_configs, prompt = await p._configure_mcp_tools(
            [mcp_server_no_auth], user_id=None
        )
        assert "Use this server" in prompt


# ── _convert_messages_to_claude_format() ─────────────────────────────────────


class TestConvertMessagesToClaudeFormat:
    async def test_human_message_converted(self):
        p = _make_processor()
        messages = [Message(text="Hello Claude", type=MessageType.HUMAN)]
        result = await p._convert_messages_to_claude_format(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    async def test_assistant_message_converted(self):
        p = _make_processor()
        messages = [Message(text="Hi there!", type=MessageType.ASSISTANT)]
        result = await p._convert_messages_to_claude_format(messages)
        assert result[0]["role"] == "assistant"

    async def test_system_message_skipped(self):
        p = _make_processor()
        messages = [
            Message(text="System instruction", type=MessageType.SYSTEM),
            Message(text="Hello", type=MessageType.HUMAN),
        ]
        result = await p._convert_messages_to_claude_format(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    async def test_file_blocks_attached_to_last_user_message(self):
        p = _make_processor()
        messages = [
            Message(text="msg1", type=MessageType.HUMAN),
            Message(text="msg2", type=MessageType.HUMAN),
        ]
        file_blocks = [{"type": "image", "source": {"type": "base64", "data": "..."}}]
        result = await p._convert_messages_to_claude_format(messages, file_blocks)
        # Last message should have a list of content blocks
        last_msg = result[-1]
        assert isinstance(last_msg["content"], list)
        # First element should be the file block
        assert last_msg["content"][0]["type"] == "image"

    async def test_no_files_produces_string_content(self):
        p = _make_processor()
        messages = [Message(text="No files", type=MessageType.HUMAN)]
        result = await p._convert_messages_to_claude_format(messages)
        assert result[0]["content"] == "No files"


# ── process() – error paths ───────────────────────────────────────────────────


class TestClaudeProcessErrors:
    async def test_no_client_raises_value_error(self):
        model = AIModel(id="m", text="M", model="claude-3")
        p = ClaudeResponsesProcessor(models={"m": model}, api_key=None)
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in p.process(messages, "m"):
                pass

    async def test_unsupported_model_raises(self):
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not supported"):
            async for _ in p.process(messages, "nonexistent-model-id"):
                pass

    async def test_cancellation_token_respected(self):
        p = _make_processor()
        cancel = asyncio.Event()
        cancel.set()

        async def fake_stream_events():
            for i in range(10):
                yield _make_event("message_start")

        messages = [Message(text="hi", type=MessageType.HUMAN)]

        async def fake_file_processing(*args, **kwargs):
            return []

        with (
            patch.object(
                p, "_process_files", new=AsyncMock(return_value=[])
            ),
            patch.object(
                p,
                "_create_messages_request",
                new=AsyncMock(),
            ) as mock_req,
        ):
            mock_stream = MagicMock()
            mock_stream.__aenter__ = AsyncMock(
                return_value=fake_stream_events()
            )
            mock_stream.__aexit__ = AsyncMock(return_value=False)
            mock_req.return_value = mock_stream

            chunks = []
            async for chunk in p.process(
                messages, "claude-test", cancellation_token=cancel
            ):
                chunks.append(chunk)

        lifecycle_chunks = [c for c in chunks if c.type == ChunkType.LIFECYCLE]
        # Cancelled immediately: 0 lifecycle chunks expected
        assert len(lifecycle_chunks) == 0

    async def test_process_yields_warnings(self, mcp_server_no_auth):
        """When _configure_mcp_tools produces warnings, process() yields them."""
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]

        async def fake_configure_mcp(*args, **kwargs):
            # Simulate a warning being added (mimics server with custom headers)
            p._mcp_warnings.append("Server X disabled: unsupported headers")
            return [], [], ""

        async def fake_gen():
            yield _make_event("message_stop")

        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=fake_gen())
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(p, "_process_files", new=AsyncMock(return_value=[])),
            patch.object(p, "_configure_mcp_tools", side_effect=fake_configure_mcp),
            patch.object(
                p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
            ),
            patch.object(p.client.beta.messages, "stream", return_value=mock_stream),
        ):
            chunks = []
            async for chunk in p.process(messages, "claude-test"):
                chunks.append(chunk)

        warning_chunks = [c for c in chunks if "disabled" in c.text]
        assert len(warning_chunks) >= 1


# ── _get_event_handlers() ─────────────────────────────────────────────────────


class TestClaudeEventHandlers:
    def test_all_expected_handlers_present(self):
        p = _make_processor()
        handlers = p._get_event_handlers()
        expected = {
            "message_start",
            "message_delta",
            "message_stop",
            "content_block_start",
            "content_block_delta",
            "content_block_stop",
        }
        assert expected.issubset(set(handlers.keys()))

    def test_handle_event_dispatches_message_start(self):
        p = _make_processor()
        ev = _make_event("message_start")
        chunk = p._handle_event(ev)
        assert chunk is not None
        assert chunk.type == ChunkType.LIFECYCLE

    def test_handle_event_unknown_returns_none(self):
        p = _make_processor()
        ev = _make_event("completely_unknown_event")
        chunk = p._handle_event(ev)
        assert chunk is None

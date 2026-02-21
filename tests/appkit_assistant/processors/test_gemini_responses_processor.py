"""Tests for GeminiResponsesProcessor.

Covers:
- Initialization (with/without API key, failed init)
- get_supported_models()
- _create_generation_config()
- _build_mcp_prompt()
- _convert_messages_to_gemini_format()
- _parse_unique_tool_name()
- _mcp_tool_to_gemini_function()
- _fix_schema_for_gemini() – all forbidden field removal paths, recursion
- _execute_mcp_tool()
- _handle_chunk()
- _extract_text_from_parts()
- _create_mcp_sessions() – no auth, OAuth with/without token
- process() – no client, unsupported model, cancellation
- _stream_with_mcp() – no sessions path
- _stream_generation() – basic streaming
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.gemini_responses_processor import (
    GEMINI_FORBIDDEN_SCHEMA_FIELDS,
    GeminiResponsesProcessor,
    MCPToolContext,
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


def _make_processor(
    api_key: str = "fake-gemini-key",
    model_id: str = "gemini-test",
) -> GeminiResponsesProcessor:
    model = AIModel(
        id=model_id,
        text="Gemini Test",
        model="gemini-2.0-flash-thinking-exp",
        stream=True,
        temperature=0.7,
    )
    return GeminiResponsesProcessor(
        models={model_id: model},
        api_key=api_key,
    )


def _make_processor_no_key() -> GeminiResponsesProcessor:
    model = AIModel(id="m", text="M", model="gemini-2.0-flash")
    return GeminiResponsesProcessor(models={"m": model}, api_key=None)


# ── Initialization ─────────────────────────────────────────────────────────────


class TestGeminiProcessorInit:
    def test_init_with_api_key_creates_client(self):
        p = _make_processor()
        assert p.client is not None

    def test_init_without_api_key_no_client(self):
        p = _make_processor_no_key()
        assert p.client is None

    def test_init_empty_api_key_no_client(self):
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        p = GeminiResponsesProcessor(models={"m": model}, api_key="")
        assert p.client is None

    def test_processor_name(self):
        p = _make_processor()
        assert p._processor_name == "gemini_responses"

    def test_get_supported_models_with_key(self):
        p = _make_processor()
        assert "gemini-test" in p.get_supported_models()

    def test_failed_client_init_logs_and_continues(self):
        """If genai.Client raises, processor still initializes (no client)."""
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        with patch(
            "appkit_assistant.backend.processors.gemini_responses_processor.genai.Client",
            side_effect=Exception("init error"),
        ):
            p = GeminiResponsesProcessor(models={"m": model}, api_key="key")
        assert p.client is None


# ── _get_event_handlers() ─────────────────────────────────────────────────────


class TestGeminiEventHandlers:
    def test_returns_empty_dict(self):
        p = _make_processor()
        handlers = p._get_event_handlers()
        assert handlers == {}


# ── _create_generation_config() ───────────────────────────────────────────────


class TestCreateGenerationConfig:
    def test_default_thinking_level_flash(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        config = p._create_generation_config(model, payload=None)
        assert config.thinking_config.thinking_level.value.lower() == "medium"

    def test_default_thinking_level_non_flash(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-pro")
        config = p._create_generation_config(model, payload=None)
        assert config.thinking_config.thinking_level.value.lower() == "high"

    def test_payload_overrides_thinking_level(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        config = p._create_generation_config(
            model, payload={"thinking_level": "low"}
        )
        assert config.thinking_config.thinking_level.value.lower() == "low"

    def test_payload_ignored_fields_filtered(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        # thread_uuid / user_id should be filtered out
        config = p._create_generation_config(
            model,
            payload={"thread_uuid": "abc", "user_id": 42, "thinking_level": "high"},
        )
        # Should not raise – filtered fields don't reach GenerateContentConfig
        assert config is not None

    def test_temperature_set(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-flash", temperature=0.5)
        config = p._create_generation_config(model, payload=None)
        assert config.temperature == 0.5

    def test_response_modalities_set(self):
        p = _make_processor()
        model = AIModel(id="m", text="M", model="gemini-2.0-flash")
        config = p._create_generation_config(model, payload=None)
        assert config.response_modalities == ["TEXT"]


# ── _build_mcp_prompt() ───────────────────────────────────────────────────────


class TestBuildMCPPrompt:
    def test_empty_servers(self):
        p = _make_processor()
        assert p._build_mcp_prompt([]) == ""

    def test_servers_with_prompts(self, mcp_server_no_auth, mcp_server_with_headers):
        p = _make_processor()
        prompt = p._build_mcp_prompt([mcp_server_no_auth, mcp_server_with_headers])
        assert "Use this server for testing." in prompt

    def test_servers_without_prompts(self, mcp_server_with_headers):
        p = _make_processor()
        # auth-server has no prompt
        prompt = p._build_mcp_prompt([mcp_server_with_headers])
        assert prompt == ""


# ── _convert_messages_to_gemini_format() ─────────────────────────────────────


class TestConvertMessagesToGeminiFormat:
    async def test_human_message_produces_user_content(self):
        p = _make_processor()
        messages = [Message(text="Hello Gemini", type=MessageType.HUMAN)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="sys")
        ):
            contents, sys_instr = await p._convert_messages_to_gemini_format(messages)
        assert len(contents) == 1
        assert contents[0].role == "user"
        assert sys_instr == "sys"

    async def test_assistant_message_produces_model_content(self):
        p = _make_processor()
        messages = [Message(text="Response", type=MessageType.ASSISTANT)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="")
        ):
            contents, _ = await p._convert_messages_to_gemini_format(messages)
        assert contents[0].role == "model"

    async def test_system_message_appended_to_instruction(self):
        p = _make_processor()
        messages = [Message(text="Extra instruction", type=MessageType.SYSTEM)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="base sys")
        ):
            contents, sys_instr = await p._convert_messages_to_gemini_format(messages)
        assert "Extra instruction" in sys_instr
        assert "base sys" in sys_instr

    async def test_system_message_only_no_base(self):
        p = _make_processor()
        messages = [Message(text="Only sys", type=MessageType.SYSTEM)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="")
        ):
            contents, sys_instr = await p._convert_messages_to_gemini_format(messages)
        assert sys_instr == "Only sys"

    async def test_mcp_prompt_passed_to_builder(self):
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with patch.object(
            p._system_prompt_builder, "build", new=AsyncMock(return_value="")
        ) as mock_build:
            await p._convert_messages_to_gemini_format(messages, mcp_prompt="tool hint")
        mock_build.assert_called_once_with("tool hint")


# ── _parse_unique_tool_name() ─────────────────────────────────────────────────


class TestParseUniqueToolName:
    def test_with_double_underscore(self):
        p = _make_processor()
        server, tool = p._parse_unique_tool_name("my_server__my_tool")
        assert server == "my_server"
        assert tool == "my_tool"

    def test_with_multiple_underscores_splits_on_first(self):
        p = _make_processor()
        server, tool = p._parse_unique_tool_name("my_server__tool__name")
        assert server == "my_server"
        assert tool == "tool__name"

    def test_without_double_underscore_fallback(self):
        p = _make_processor()
        server, tool = p._parse_unique_tool_name("simple_tool")
        assert server == "unknown"
        assert tool == "simple_tool"


# ── _fix_schema_for_gemini() ─────────────────────────────────────────────────


class TestFixSchemaForGemini:
    def test_removes_forbidden_fields(self):
        p = _make_processor()
        schema = {
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "MyTool",
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
        }
        result = p._fix_schema_for_gemini(schema)
        for field in GEMINI_FORBIDDEN_SCHEMA_FIELDS:
            assert field not in result

    def test_preserves_valid_fields(self):
        p = _make_processor()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        result = p._fix_schema_for_gemini(schema)
        assert result["type"] == "object"
        assert "properties" in result
        assert result["required"] == ["name"]

    def test_fixes_array_without_items(self):
        p = _make_processor()
        schema = {"type": "array"}
        result = p._fix_schema_for_gemini(schema)
        assert "items" in result
        assert result["items"] == {"type": "string"}

    def test_does_not_add_items_if_already_present(self):
        p = _make_processor()
        schema = {"type": "array", "items": {"type": "integer"}}
        result = p._fix_schema_for_gemini(schema)
        assert result["items"] == {"type": "integer"}

    def test_recursive_on_properties(self):
        p = _make_processor()
        schema = {
            "type": "object",
            "properties": {
                "child": {
                    "type": "object",
                    "additionalProperties": False,
                    "title": "Child",
                }
            },
        }
        result = p._fix_schema_for_gemini(schema)
        child = result["properties"]["child"]
        assert "additionalProperties" not in child
        assert "title" not in child

    def test_recursive_on_items(self):
        p = _make_processor()
        schema = {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False},
        }
        result = p._fix_schema_for_gemini(schema)
        assert "additionalProperties" not in result["items"]

    def test_recursive_on_any_of(self):
        p = _make_processor()
        schema = {
            "anyOf": [
                {"type": "string", "title": "Name"},
                {"type": "null"},
            ]
        }
        result = p._fix_schema_for_gemini(schema)
        assert "title" not in result["anyOf"][0]

    def test_non_dict_returned_as_is(self):
        p = _make_processor()
        assert p._fix_schema_for_gemini("string") == "string"
        assert p._fix_schema_for_gemini(42) == 42

    def test_deep_nesting(self):
        p = _make_processor()
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "deep": {
                            "type": "array",
                            "additionalProperties": False,
                        }
                    },
                }
            },
        }
        result = p._fix_schema_for_gemini(schema)
        deep = result["properties"]["nested"]["properties"]["deep"]
        assert "additionalProperties" not in deep


# ── _mcp_tool_to_gemini_function() ───────────────────────────────────────────


class TestMCPToolToGeminiFunction:
    def test_valid_tool_conversion(self):
        p = _make_processor()
        tool_def = {
            "description": "Search the web",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
        result = p._mcp_tool_to_gemini_function("web_search", tool_def)
        assert result is not None
        assert result.name == "web_search"
        assert "Search" in result.description

    def test_original_name_enhances_description(self):
        p = _make_processor()
        tool_def = {"description": "Do something", "inputSchema": {}}
        result = p._mcp_tool_to_gemini_function(
            "server__do_something", tool_def, original_name="do_something"
        )
        assert result is not None
        assert "[do_something]" in result.description

    def test_empty_schema_returns_none_parameters(self):
        p = _make_processor()
        tool_def = {"description": "Simple tool", "inputSchema": {}}
        result = p._mcp_tool_to_gemini_function("simple_tool", tool_def)
        assert result is not None
        assert result.parameters is None

    def test_invalid_tool_returns_none(self):
        p = _make_processor()
        # Simulate an exception during conversion
        with patch.object(
            p,
            "_fix_schema_for_gemini",
            side_effect=Exception("conversion error"),
        ):
            result = p._mcp_tool_to_gemini_function(
                "bad_tool", {"description": "x", "inputSchema": {"type": "object"}}
            )
        assert result is None


# ── _extract_text_from_parts() ────────────────────────────────────────────────


class TestExtractTextFromParts:
    def test_extracts_text_from_parts(self):
        p = _make_processor()
        part1 = MagicMock()
        part1.text = "Hello "
        part2 = MagicMock()
        part2.text = "World"
        result = p._extract_text_from_parts([part1, part2])
        assert result == "Hello World"

    def test_skips_parts_without_text(self):
        p = _make_processor()
        part1 = MagicMock()
        part1.text = ""
        part2 = MagicMock()
        part2.text = "content"
        result = p._extract_text_from_parts([part1, part2])
        assert result == "content"

    def test_empty_list(self):
        p = _make_processor()
        assert p._extract_text_from_parts([]) == ""


# ── _handle_chunk() ───────────────────────────────────────────────────────────


class TestHandleChunk:
    def test_chunk_with_text_returns_text_chunk(self):
        p = _make_processor()
        part = MagicMock()
        part.text = "streamed text"
        candidate = MagicMock()
        candidate.content.parts = [part]
        gemini_chunk = MagicMock()
        gemini_chunk.candidates = [candidate]
        gemini_chunk.usage_metadata = None
        result = p._handle_chunk(gemini_chunk)
        assert result is not None
        assert result.type == ChunkType.TEXT
        assert result.text == "streamed text"

    def test_chunk_with_usage_updates_statistics(self):
        p = _make_processor()
        p._reset_statistics("gemini-test")
        part = MagicMock()
        part.text = "text"
        candidate = MagicMock()
        candidate.content.parts = [part]
        usage = MagicMock()
        usage.prompt_token_count = 100
        usage.candidates_token_count = 50
        gemini_chunk = MagicMock()
        gemini_chunk.candidates = [candidate]
        gemini_chunk.usage_metadata = usage
        p._handle_chunk(gemini_chunk)
        stats = p._get_statistics()
        assert stats.input_tokens == 100
        assert stats.output_tokens == 50

    def test_empty_candidates_returns_none(self):
        p = _make_processor()
        gemini_chunk = MagicMock()
        gemini_chunk.candidates = []
        gemini_chunk.usage_metadata = None
        result = p._handle_chunk(gemini_chunk)
        assert result is None

    def test_no_content_returns_none(self):
        p = _make_processor()
        candidate = MagicMock()
        candidate.content = None
        gemini_chunk = MagicMock()
        gemini_chunk.candidates = [candidate]
        gemini_chunk.usage_metadata = None
        result = p._handle_chunk(gemini_chunk)
        assert result is None

    def test_no_text_in_parts_returns_none(self):
        p = _make_processor()
        part = MagicMock()
        part.text = ""
        candidate = MagicMock()
        candidate.content.parts = [part]
        gemini_chunk = MagicMock()
        gemini_chunk.candidates = [candidate]
        gemini_chunk.usage_metadata = None
        result = p._handle_chunk(gemini_chunk)
        assert result is None


# ── _create_mcp_sessions() ────────────────────────────────────────────────────


class TestCreateMCPSessions:
    async def test_no_auth_server_creates_session_wrapper(
        self, mcp_server_no_auth
    ):
        p = _make_processor()
        sessions, auth_required = await p._create_mcp_sessions(
            [mcp_server_no_auth], user_id=None
        )
        assert len(sessions) == 1
        assert sessions[0].name == "test-server"
        assert auth_required == []

    async def test_oauth_server_with_valid_token(self, mcp_server_oauth):
        p = _make_processor()
        fake_token = MagicMock()
        fake_token.access_token = "oauth-abc"
        with patch.object(p, "get_valid_token", new=AsyncMock(return_value=fake_token)):
            sessions, auth_required = await p._create_mcp_sessions(
                [mcp_server_oauth], user_id=42
            )
        assert len(sessions) == 1
        assert sessions[0].headers.get("Authorization") == "Bearer oauth-abc"
        assert auth_required == []

    async def test_oauth_server_no_token_requires_auth(self, mcp_server_oauth):
        p = _make_processor()
        with patch.object(p, "get_valid_token", new=AsyncMock(return_value=None)):
            sessions, auth_required = await p._create_mcp_sessions(
                [mcp_server_oauth], user_id=42
            )
        assert len(sessions) == 0
        assert mcp_server_oauth in auth_required

    async def test_server_connection_error_skips_server(self, mcp_server_no_auth):
        """If parsing headers raises, server is skipped gracefully."""
        p = _make_processor()
        with patch.object(p, "parse_mcp_headers", side_effect=Exception("conn error")):
            sessions, auth_required = await p._create_mcp_sessions(
                [mcp_server_no_auth], user_id=None
            )
        assert sessions == []

    async def test_server_with_bearer_header_included(
        self, mcp_server_with_headers
    ):
        p = _make_processor()
        sessions, _ = await p._create_mcp_sessions(
            [mcp_server_with_headers], user_id=None
        )
        assert len(sessions) == 1
        assert sessions[0].headers.get("Authorization") == "Bearer static-token-123"


# ── _execute_mcp_tool() ───────────────────────────────────────────────────────


class TestExecuteMCPTool:
    async def test_executes_tool_successfully(self):
        p = _make_processor()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        item = MagicMock()
        item.text = "tool result text"
        mock_result.content = [item]
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        ctx = MCPToolContext(
            session=mock_session,
            server_name="my_server",
            tools={"my_tool": {}},
        )
        result = await p._execute_mcp_tool("my_server__my_tool", {}, [ctx])
        assert result == "tool result text"

    async def test_tool_not_found_returns_message(self):
        p = _make_processor()
        result = await p._execute_mcp_tool("unknown__tool", {}, [])
        assert "not found" in result

    async def test_tool_execution_error_returns_error_message(self):
        p = _make_processor()
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("tool crashed"))

        ctx = MCPToolContext(
            session=mock_session,
            server_name="srv",
            tools={"failing_tool": {}},
        )
        result = await p._execute_mcp_tool("srv__failing_tool", {}, [ctx])
        assert "Error executing tool" in result

    async def test_result_without_content_attr(self):
        p = _make_processor()
        mock_session = AsyncMock()
        mock_result = MagicMock(spec=[])  # no 'content' attr
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        ctx = MCPToolContext(
            session=mock_session,
            server_name="srv",
            tools={"tool": {}},
        )
        result = await p._execute_mcp_tool("srv__tool", {}, [ctx])
        assert isinstance(result, str)


# ── process() – error paths ───────────────────────────────────────────────────


class TestGeminiProcessErrors:
    async def test_no_client_raises_value_error(self):
        p = _make_processor_no_key()
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in p.process(messages, "m"):
                pass

    async def test_unsupported_model_raises(self):
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]
        with pytest.raises(ValueError, match="not supported"):
            async for _ in p.process(messages, "nonexistent"):
                pass

    async def test_cancellation_immediately_stops(self):
        p = _make_processor()
        cancel = asyncio.Event()
        cancel.set()
        messages = [Message(text="hi", type=MessageType.HUMAN)]

        async def fake_stream(*args, **kwargs):
            # Should never be reached if cancelled early
            yield MagicMock()

        with (
            patch.object(p, "_create_mcp_sessions", new=AsyncMock(return_value=([], []))),
            patch.object(
                p._system_prompt_builder, "build", new=AsyncMock(return_value="")
            ),
            patch.object(p, "_stream_with_mcp", return_value=fake_stream()),
        ):
            chunks = []
            async for chunk in p.process(
                messages, "gemini-test", cancellation_token=cancel
            ):
                chunks.append(chunk)

        # Should have completion chunk + maybe auth chunks, but no text from streaming
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 0

    async def test_process_exception_yields_error_chunk(self):
        p = _make_processor()
        messages = [Message(text="hi", type=MessageType.HUMAN)]

        async def fake_stream_error(*args, **kwargs):
            raise RuntimeError("API error")

        with (
            patch.object(p, "_create_mcp_sessions", new=AsyncMock(return_value=([], []))),
            patch.object(
                p._system_prompt_builder, "build", new=AsyncMock(return_value="")
            ),
            patch.object(p, "_stream_with_mcp", return_value=fake_stream_error()),
        ):
            chunks = []
            async for chunk in p.process(messages, "gemini-test"):
                chunks.append(chunk)

        error_chunks = [c for c in chunks if c.type == ChunkType.ERROR]
        assert len(error_chunks) >= 1


# ── _stream_with_mcp() – no sessions ─────────────────────────────────────────


class TestStreamWithMCP:
    async def test_no_mcp_sessions_uses_stream_generation(self):
        p = _make_processor()

        async def fake_gen(*args, **kwargs):
            yield MagicMock(type=ChunkType.TEXT, text="direct text")

        from google.genai import types

        config = types.GenerateContentConfig(temperature=0.7)
        with patch.object(p, "_stream_generation", side_effect=fake_gen):
            chunks = []
            async for chunk in p._stream_with_mcp(
                "gemini-2.0-flash", [], config, []
            ):
                chunks.append(chunk)
        assert len(chunks) == 1


# ── _stream_generation() ─────────────────────────────────────────────────────


class TestStreamGeneration:
    async def test_basic_text_streaming(self):
        p = _make_processor()

        async def fake_stream_iter():
            for text in ["Hello ", "World"]:
                part = MagicMock()
                part.text = text
                part.function_call = None
                candidate = MagicMock()
                candidate.content.parts = [part]
                chunk = MagicMock()
                chunk.candidates = [candidate]
                chunk.usage_metadata = None
                yield chunk

        from google.genai import types

        config = types.GenerateContentConfig(temperature=0.7)
        with patch.object(
            p.client.aio.models,
            "generate_content_stream",
            new=AsyncMock(return_value=fake_stream_iter()),
        ):
            chunks = []
            async for chunk in p._stream_generation("gemini-2.0-flash", [], config):
                chunks.append(chunk)

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 2

    async def test_cancellation_during_stream(self):
        p = _make_processor()
        cancel = asyncio.Event()

        async def fake_stream_iter():
            for i in range(5):
                part = MagicMock()
                part.text = f"word{i}"
                part.function_call = None
                candidate = MagicMock()
                candidate.content.parts = [part]
                chunk = MagicMock()
                chunk.candidates = [candidate]
                chunk.usage_metadata = None
                if i == 2:
                    cancel.set()
                yield chunk

        from google.genai import types

        config = types.GenerateContentConfig(temperature=0.7)
        with patch.object(
            p.client.aio.models,
            "generate_content_stream",
            new=AsyncMock(return_value=fake_stream_iter()),
        ):
            chunks = []
            async for chunk in p._stream_generation(
                "gemini-2.0-flash", [], config, cancellation_token=cancel
            ):
                chunks.append(chunk)

        # Should stop after cancellation (at most 3 text chunks: word0, word1, word2)
        assert len(chunks) <= 3

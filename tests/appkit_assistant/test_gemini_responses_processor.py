# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for GeminiResponsesProcessor.

Covers init, model support, generation config, message conversion,
MCP session creation, schema fixing, tool name parsing, and chunk handling.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.gemini_responses_processor import (
    GEMINI_FORBIDDEN_SCHEMA_FIELDS,
    GeminiResponsesProcessor,
    MCPSessionWrapper,
    MCPToolContext,
)
from appkit_assistant.backend.schemas import (
    AIModel,
    ChunkType,
    MCPAuthType,
    Message,
    MessageType,
)

_PATCH = "appkit_assistant.backend.processors.gemini_responses_processor"


# ============================================================================
# Helpers
# ============================================================================


def _model(model_id: str = "gemini-2.5-flash") -> AIModel:
    return AIModel(
        id=model_id, text=model_id, model=model_id, stream=True, temperature=0.7
    )


def _make_processor(
    api_key: str = "test-key",
    models: dict[str, AIModel] | None = None,
) -> GeminiResponsesProcessor:
    if models is None:
        models = {"gemini-2.5-flash": _model()}
    with (
        patch(f"{_PATCH}.mcp_oauth_redirect_uri", return_value="https://t/cb"),
        patch(f"{_PATCH}.genai") as mock_genai,
    ):
        mock_genai.Client.return_value = MagicMock()
        return GeminiResponsesProcessor(models=models, api_key=api_key)


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
# Initialization
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = _make_processor()
        assert proc._processor_name == "gemini_responses"
        assert proc.client is not None

    def test_no_api_key(self) -> None:
        with patch(
            f"{_PATCH}.mcp_oauth_redirect_uri",
            return_value="https://t/cb",
        ):
            proc = GeminiResponsesProcessor(models={"m": _model()}, api_key=None)
        assert proc.client is None

    def test_get_event_handlers_empty(self) -> None:
        proc = _make_processor()
        assert proc._get_event_handlers() == {}


# ============================================================================
# _create_generation_config
# ============================================================================


class TestCreateGenerationConfig:
    def test_flash_model_default_thinking(self) -> None:
        proc = _make_processor()
        model = _model("gemini-2.5-flash")
        config = proc._create_generation_config(model, None)
        assert config.temperature == 0.7
        assert config.thinking_config.thinking_level.value == "MEDIUM"

    def test_pro_model_default_thinking(self) -> None:
        proc = _make_processor()
        model = _model("gemini-2.5-pro")
        config = proc._create_generation_config(model, None)
        assert config.thinking_config.thinking_level.value == "HIGH"

    def test_payload_override_thinking(self) -> None:
        proc = _make_processor()
        model = _model("gemini-2.5-flash")
        payload = {"thinking_level": "low"}
        config = proc._create_generation_config(model, payload)
        assert config.thinking_config.thinking_level.value == "LOW"

    def test_payload_filters_internal_keys(self) -> None:
        proc = _make_processor()
        model = _model()
        payload = {
            "thread_uuid": "abc",
            "user_id": 1,
            "thinking_level": "high",
        }
        # Should not raise even though internal keys are present
        config = proc._create_generation_config(model, payload)
        assert config is not None


# ============================================================================
# _build_mcp_prompt
# ============================================================================


class TestBuildMcpPrompt:
    def test_prompts(self) -> None:
        proc = _make_processor()
        servers = [
            _make_server(prompt="Use search"),
            _make_server(prompt="Use files"),
        ]
        result = proc._build_mcp_prompt(servers)
        assert "- Use search" in result
        assert "- Use files" in result

    def test_no_prompts(self) -> None:
        proc = _make_processor()
        servers = [_make_server(prompt=None)]
        assert proc._build_mcp_prompt(servers) == ""


# ============================================================================
# _fix_schema_for_gemini
# ============================================================================


class TestFixSchemaForGemini:
    def test_removes_forbidden_fields(self) -> None:
        proc = _make_processor()
        schema = {
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Test",
            "additionalProperties": False,
            "properties": {"q": {"type": "string"}},
        }
        result = proc._fix_schema_for_gemini(schema)
        for field in GEMINI_FORBIDDEN_SCHEMA_FIELDS:
            assert field not in result

    def test_fixes_array_without_items(self) -> None:
        proc = _make_processor()
        schema = {"type": "array"}
        result = proc._fix_schema_for_gemini(schema)
        assert result["items"] == {"type": "string"}

    def test_recurse_nested(self) -> None:
        proc = _make_processor()
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "title": "Tags",
                }
            },
        }
        result = proc._fix_schema_for_gemini(schema)
        assert "title" not in result["properties"]["tags"]
        assert result["properties"]["tags"]["items"] == {"type": "string"}

    def test_non_dict_passthrough(self) -> None:
        proc = _make_processor()
        assert proc._fix_schema_for_gemini("string") == "string"

    def test_anyof_recurse(self) -> None:
        proc = _make_processor()
        schema = {
            "anyOf": [
                {"type": "string", "title": "A"},
                {"type": "number", "title": "B"},
            ]
        }
        result = proc._fix_schema_for_gemini(schema)
        for item in result["anyOf"]:
            assert "title" not in item


# ============================================================================
# _parse_unique_tool_name
# ============================================================================


class TestParseUniqueToolName:
    def test_with_prefix(self) -> None:
        proc = _make_processor()
        server, tool = proc._parse_unique_tool_name("GitHub__search")
        assert server == "GitHub"
        assert tool == "search"

    def test_without_prefix(self) -> None:
        proc = _make_processor()
        server, tool = proc._parse_unique_tool_name("search")
        assert server == "unknown"
        assert tool == "search"

    def test_multiple_double_underscores(self) -> None:
        proc = _make_processor()
        server, tool = proc._parse_unique_tool_name("GH__tool__v2")
        assert server == "GH"
        assert tool == "tool__v2"


# ============================================================================
# _mcp_tool_to_gemini_function
# ============================================================================


class TestMcpToolToGeminiFunction:
    def test_basic(self) -> None:
        proc = _make_processor()
        tool_def = {
            "description": "Search tool",
            "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}},
        }
        result = proc._mcp_tool_to_gemini_function("test__search", tool_def)
        assert result is not None
        assert result.name == "test__search"

    def test_with_original_name(self) -> None:
        proc = _make_processor()
        tool_def = {"description": "Search", "inputSchema": {}}
        result = proc._mcp_tool_to_gemini_function(
            "GH__search", tool_def, original_name="search"
        )
        assert result is not None
        assert "[search]" in result.description

    def test_empty_schema(self) -> None:
        proc = _make_processor()
        tool_def = {"description": "No params"}
        result = proc._mcp_tool_to_gemini_function("tool", tool_def)
        assert result is not None
        assert result.parameters is None or result.parameters == {}


# ============================================================================
# _handle_chunk
# ============================================================================


class TestHandleChunk:
    def test_text_chunk(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gemini-2.5-flash")
        part = SimpleNamespace(text="hello", function_call=None)
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        chunk = SimpleNamespace(candidates=[candidate], usage_metadata=None)
        result = proc._handle_chunk(chunk)
        assert result is not None
        assert result.type == ChunkType.TEXT
        assert result.text == "hello"

    def test_no_candidates(self) -> None:
        proc = _make_processor()
        chunk = SimpleNamespace(candidates=None, usage_metadata=None)
        assert proc._handle_chunk(chunk) is None

    def test_no_parts(self) -> None:
        proc = _make_processor()
        content = SimpleNamespace(parts=None)
        candidate = SimpleNamespace(content=content)
        chunk = SimpleNamespace(candidates=[candidate], usage_metadata=None)
        assert proc._handle_chunk(chunk) is None

    def test_usage_metadata(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("gemini-2.5-flash")
        usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=50)
        part = SimpleNamespace(text="data", function_call=None)
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        chunk = SimpleNamespace(candidates=[candidate], usage_metadata=usage)
        proc._handle_chunk(chunk)
        # Statistics should be updated (no crash)

    def test_empty_text(self) -> None:
        proc = _make_processor()
        part = SimpleNamespace(text="", function_call=None)
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        chunk = SimpleNamespace(candidates=[candidate], usage_metadata=None)
        assert proc._handle_chunk(chunk) is None


# ============================================================================
# _extract_text_from_parts
# ============================================================================


class TestExtractTextFromParts:
    def test_joins_text(self) -> None:
        proc = _make_processor()
        parts = [
            SimpleNamespace(text="a"),
            SimpleNamespace(text="b"),
            SimpleNamespace(text=None),
        ]
        assert proc._extract_text_from_parts(parts) == "ab"


# ============================================================================
# Message conversion
# ============================================================================


class TestConvertMessages:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.HUMAN, text="Hello"),
            Message(type=MessageType.ASSISTANT, text="Hi"),
        ]
        with patch.object(
            proc._system_prompt_builder,
            "build",
            new_callable=AsyncMock,
            return_value="sys",
        ):
            contents, sys_instr = await proc._convert_messages_to_gemini_format(msgs)
        assert len(contents) == 2
        assert contents[0].role == "user"
        assert contents[1].role == "model"
        assert sys_instr is not None

    @pytest.mark.asyncio
    async def test_system_messages_merged(self) -> None:
        proc = _make_processor()
        msgs = [
            Message(type=MessageType.SYSTEM, text="extra context"),
            Message(type=MessageType.HUMAN, text="Hello"),
        ]
        with patch.object(
            proc._system_prompt_builder,
            "build",
            new_callable=AsyncMock,
            return_value="base",
        ):
            contents, sys_instr = await proc._convert_messages_to_gemini_format(msgs)
        assert len(contents) == 1  # only HUMAN
        assert "base" in sys_instr
        assert "extra context" in sys_instr


# ============================================================================
# MCP session creation
# ============================================================================


class TestCreateMcpSessions:
    @pytest.mark.asyncio
    async def test_basic_session(self) -> None:
        proc = _make_processor()
        server = _make_server(headers="{}")
        sessions, auth = await proc._create_mcp_sessions([server], None)
        assert len(sessions) == 1
        assert isinstance(sessions[0], MCPSessionWrapper)
        assert auth == []

    @pytest.mark.asyncio
    async def test_oauth_no_token_skipped(self) -> None:
        proc = _make_processor()
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY, headers="{}")
        proc._mcp_token_service.get_valid_token = AsyncMock(return_value=None)
        sessions, auth = await proc._create_mcp_sessions([server], 1)
        assert len(sessions) == 0
        assert len(auth) == 1

    @pytest.mark.asyncio
    async def test_oauth_with_token(self) -> None:
        proc = _make_processor()
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY, headers="{}")
        tok = MagicMock()
        tok.access_token = "ok"
        proc._mcp_token_service.get_valid_token = AsyncMock(return_value=tok)
        sessions, auth = await proc._create_mcp_sessions([server], 1)
        assert len(sessions) == 1
        assert auth == []
        assert sessions[0].headers["Authorization"] == "Bearer ok"


# ============================================================================
# MCPToolContext / MCPSessionWrapper data classes
# ============================================================================


class TestDataClasses:
    def test_mcp_tool_context(self) -> None:
        ctx = MCPToolContext(session=MagicMock(), server_name="test", tools={"a": {}})
        assert ctx.server_name == "test"
        assert "a" in ctx.tools

    def test_mcp_session_wrapper(self) -> None:
        w = MCPSessionWrapper(url="https://test", headers={"X": "1"}, name="s")
        assert w.url == "https://test"
        assert w.name == "s"

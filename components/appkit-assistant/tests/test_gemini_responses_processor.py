# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for GeminiResponsesProcessor.

Covers init, model support, generation config, message conversion,
MCP session creation, schema fixing, tool name parsing, and chunk handling.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

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
    inject_user_id: bool = False,
) -> MagicMock:
    server = MagicMock()
    server.name = name
    server.url = url
    server.headers = headers
    server.auth_type = auth_type
    server.prompt = prompt
    server.inject_user_id = inject_user_id
    return server


def _msgs() -> list[Message]:
    return [
        Message(type=MessageType.HUMAN, text="Hello"),
        Message(type=MessageType.ASSISTANT, text="Hi"),
        Message(type=MessageType.HUMAN, text="Test question"),
    ]


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

    @pytest.mark.asyncio
    async def test_inject_user_id_header(self) -> None:
        proc = _make_processor()
        proc.current_user_id = 42
        server = _make_server(headers="{}", inject_user_id=True)
        sessions, _ = await proc._create_mcp_sessions([server], None)
        assert sessions[0].headers["x-user-id"] == "42"

    @pytest.mark.asyncio
    async def test_inject_user_id_skipped_when_disabled(self) -> None:
        proc = _make_processor()
        proc.current_user_id = 42
        server = _make_server(headers="{}", inject_user_id=False)
        sessions, _ = await proc._create_mcp_sessions([server], None)
        assert "x-user-id" not in sessions[0].headers

    @pytest.mark.asyncio
    async def test_inject_user_id_skipped_when_no_user(self) -> None:
        proc = _make_processor()
        proc.current_user_id = None
        server = _make_server(headers="{}", inject_user_id=True)
        sessions, _ = await proc._create_mcp_sessions([server], None)
        assert "x-user-id" not in sessions[0].headers


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


# ============================================================================
# process() full flow
# ============================================================================

_PATCH = "appkit_assistant.backend.processors.gemini_responses_processor"


class TestProcessFlow:
    @pytest.mark.asyncio
    async def test_validation_no_client(self) -> None:
        proc = _make_processor(api_key=None)
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in proc.process([], "gemini-2.5-flash"):
                pass

    @pytest.mark.asyncio
    async def test_validation_unknown_model(self) -> None:
        proc = _make_processor()
        with pytest.raises(ValueError, match="not supported"):
            async for _ in proc.process([], "nonexistent"):
                pass

    @pytest.mark.asyncio
    async def test_basic_streaming(self) -> None:
        proc = _make_processor()
        msgs = _msgs()

        async def _mock_stream(
            model_name, contents, config, mcp_sessions, cancel_token=None
        ):
            yield proc.chunk_factory.text("Hello", delta="Hello")

        proc._stream_with_mcp = _mock_stream
        proc._convert_messages_to_gemini_format = AsyncMock(return_value=([], None))

        chunks = [c async for c in proc.process(msgs, "gemini-2.5-flash")]
        types_found = {c.type for c in chunks}
        assert ChunkType.TEXT in types_found
        assert ChunkType.COMPLETION in types_found

    @pytest.mark.asyncio
    async def test_process_with_mcp_servers(self) -> None:
        proc = _make_processor()
        msgs = _msgs()
        server = _make_server(headers="{}", prompt="search tool")

        async def _mock_stream(
            model_name, contents, config, mcp_sessions, cancel_token=None
        ):
            yield proc.chunk_factory.text("Result", delta="Result")

        proc._stream_with_mcp = _mock_stream
        proc._create_mcp_sessions = AsyncMock(return_value=([MagicMock()], []))
        proc._convert_messages_to_gemini_format = AsyncMock(return_value=([], None))

        chunks = [
            c
            async for c in proc.process(msgs, "gemini-2.5-flash", mcp_servers=[server])
        ]
        types_found = {c.type for c in chunks}
        assert ChunkType.TEXT in types_found
        assert ChunkType.COMPLETION in types_found

    @pytest.mark.asyncio
    async def test_process_error_yields_error_chunk(self) -> None:
        proc = _make_processor()
        msgs = _msgs()

        async def _mock_stream(
            model_name, contents, config, mcp_sessions, cancel_token=None
        ):
            raise RuntimeError("API error")
            yield  # noqa: RET504

        proc._stream_with_mcp = _mock_stream
        proc._convert_messages_to_gemini_format = AsyncMock(return_value=([], None))

        chunks = [c async for c in proc.process(msgs, "gemini-2.5-flash")]
        error_chunks = [c for c in chunks if c.type == ChunkType.ERROR]
        assert len(error_chunks) == 1

    @pytest.mark.asyncio
    async def test_process_with_auth_required(self) -> None:
        proc = _make_processor()
        msgs = _msgs()
        server = _make_server(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            headers="{}",
        )

        async def _mock_stream(
            model_name, contents, config, mcp_sessions, cancel_token=None
        ):
            yield proc.chunk_factory.text("Result", delta="Result")

        proc._stream_with_mcp = _mock_stream
        proc._create_mcp_sessions = AsyncMock(return_value=([], [server]))
        proc._convert_messages_to_gemini_format = AsyncMock(return_value=([], None))

        chunks = [
            c
            async for c in proc.process(msgs, "gemini-2.5-flash", mcp_servers=[server])
        ]
        # Should still get text and completion
        assert any(c.type == ChunkType.TEXT for c in chunks)
        assert any(c.type == ChunkType.COMPLETION for c in chunks)


# ============================================================================
# _stream_with_mcp
# ============================================================================


class TestStreamWithMcp:
    @pytest.mark.asyncio
    async def test_no_mcp_sessions_direct_stream(self) -> None:
        proc = _make_processor()

        async def _mock_gen(model_name, contents, config, cancel=None):
            yield proc.chunk_factory.text("Direct", delta="Direct")

        proc._stream_generation = _mock_gen

        chunks = [
            c
            async for c in proc._stream_with_mcp(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [],
                None,
            )
        ]
        assert len(chunks) == 1
        assert chunks[0].type == ChunkType.TEXT

    @pytest.mark.asyncio
    async def test_with_mcp_sessions(self) -> None:
        proc = _make_processor()

        # Mock the context manager
        tool_ctx = MCPToolContext(
            session=MagicMock(),
            server_name="TestServer",
            tools={
                "search": {
                    "description": "Search tool",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            },
        )

        @asynccontextmanager
        async def _mock_ctx(wrappers):
            yield [tool_ctx]

        proc._mcp_context_manager = _mock_ctx

        async def _mock_tool_loop(
            model_name, contents, config, tool_contexts, cancel=None
        ):
            yield proc.chunk_factory.text("With tools", delta="With tools")

        proc._stream_with_tool_loop = _mock_tool_loop

        wrapper = MCPSessionWrapper("https://test", {}, "TestServer")
        chunks = [
            c
            async for c in proc._stream_with_mcp(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [wrapper],
                None,
            )
        ]
        assert any(c.type == ChunkType.TEXT for c in chunks)


# ============================================================================
# _stream_with_tool_loop
# ============================================================================


class TestStreamWithToolLoop:
    @pytest.mark.asyncio
    async def test_text_only_no_tools(self) -> None:
        proc = _make_processor()

        # Mock stream that returns text only
        chunk_response = MagicMock()
        chunk_response.usage_metadata = MagicMock(
            prompt_token_count=10, candidates_token_count=5
        )
        chunk_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="Answer text", function_call=None)]
                )
            )
        ]

        async def _mock_stream():
            yield chunk_response

        proc.client.aio.models.generate_content_stream = AsyncMock(
            return_value=_mock_stream()
        )

        chunks = [
            c
            async for c in proc._stream_with_tool_loop(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [],
                None,
            )
        ]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 1
        assert "Answer text" in text_chunks[0].text

    @pytest.mark.asyncio
    async def test_with_function_calls(self) -> None:
        proc = _make_processor()

        # First round: model returns function call
        fc_part = types.Part(
            function_call=types.FunctionCall(
                name="TestServer__search",
                args={"query": "test"},
            ),
        )

        chunk1 = MagicMock()
        chunk1.usage_metadata = MagicMock(
            prompt_token_count=10, candidates_token_count=5
        )
        chunk1.candidates = [MagicMock(content=MagicMock(parts=[fc_part]))]

        # Second round: model returns text
        text_part = types.Part(text="Final answer")
        chunk2 = MagicMock()
        chunk2.usage_metadata = MagicMock(
            prompt_token_count=15, candidates_token_count=10
        )
        chunk2.candidates = [MagicMock(content=MagicMock(parts=[text_part]))]

        call_count = 0

        async def _mock_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield chunk1
            else:
                yield chunk2

        proc.client.aio.models.generate_content_stream = AsyncMock(
            side_effect=_mock_stream
        )

        # Mock _execute_mcp_tool
        proc._execute_mcp_tool = AsyncMock(return_value="search results")

        ctx = MCPToolContext(
            session=MagicMock(),
            server_name="TestServer",
            tools={"search": {"description": "Search"}},
        )

        chunks = [
            c
            async for c in proc._stream_with_tool_loop(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [ctx],
                None,
            )
        ]

        tool_calls = [c for c in chunks if c.type == ChunkType.TOOL_CALL]
        tool_results = [c for c in chunks if c.type == ChunkType.TOOL_RESULT]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]

        assert len(tool_calls) >= 1
        assert len(tool_results) >= 1
        assert len(text_chunks) >= 1

    @pytest.mark.asyncio
    async def test_cancellation_during_streaming(self) -> None:
        proc = _make_processor()
        cancel = asyncio.Event()

        text_part = MagicMock(text="answer", function_call=None)
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = [MagicMock(content=MagicMock(parts=[text_part]))]

        async def _mock_stream(**kwargs):
            yield chunk
            cancel.set()
            yield chunk

        proc.client.aio.models.generate_content_stream = AsyncMock(
            side_effect=_mock_stream
        )

        chunks = [
            c
            async for c in proc._stream_with_tool_loop(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [],
                cancel,
            )
        ]
        # Should get at least 1 text chunk before cancellation stopped
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_empty_candidates_skipped(self) -> None:
        proc = _make_processor()

        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = []

        async def _mock_stream(**kwargs):
            yield chunk

        proc.client.aio.models.generate_content_stream = AsyncMock(
            side_effect=_mock_stream
        )

        chunks = [
            c
            async for c in proc._stream_with_tool_loop(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                [],
                None,
            )
        ]
        assert len(chunks) == 0


# ============================================================================
# _execute_mcp_tool
# ============================================================================


class TestExecuteMcpTool:
    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        proc = _make_processor()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="result text")]
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        ctx = MCPToolContext(
            session=mock_session,
            server_name="TestServer",
            tools={"search": {}},
        )

        result = await proc._execute_mcp_tool(
            "TestServer__search", {"q": "test"}, [ctx]
        )
        assert result == "result text"

    @pytest.mark.asyncio
    async def test_tool_not_found(self) -> None:
        proc = _make_processor()
        ctx = MCPToolContext(
            session=MagicMock(),
            server_name="Other",
            tools={"search": {}},
        )

        result = await proc._execute_mcp_tool("TestServer__search", {}, [ctx])
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_execution_error(self) -> None:
        proc = _make_processor()
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=RuntimeError("fail"))

        ctx = MCPToolContext(
            session=mock_session,
            server_name="TestServer",
            tools={"search": {}},
        )

        result = await proc._execute_mcp_tool("TestServer__search", {}, [ctx])
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_no_content_result(self) -> None:
        proc = _make_processor()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = []
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        ctx = MCPToolContext(
            session=mock_session,
            server_name="TestServer",
            tools={"search": {}},
        )

        result = await proc._execute_mcp_tool("TestServer__search", {}, [ctx])
        # Falls through to str(result)
        assert result is not None


# ============================================================================
# _stream_generation
# ============================================================================


class TestStreamGeneration:
    @pytest.mark.asyncio
    async def test_basic_generation(self) -> None:
        proc = _make_processor()

        text_part = MagicMock(text="Hello world")
        chunk = MagicMock()
        chunk.usage_metadata = MagicMock(
            prompt_token_count=10, candidates_token_count=5
        )
        chunk.candidates = [MagicMock(content=MagicMock(parts=[text_part]))]

        async def _mock_stream():
            yield chunk

        proc.client.aio.models.generate_content_stream = AsyncMock(
            return_value=_mock_stream()
        )

        proc._reset_statistics("gemini-2.5-flash")
        chunks = [
            c
            async for c in proc._stream_generation(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
            )
        ]
        assert len(chunks) == 1
        assert chunks[0].type == ChunkType.TEXT

    @pytest.mark.asyncio
    async def test_generation_with_cancellation(self) -> None:
        proc = _make_processor()
        cancel = asyncio.Event()
        cancel.set()

        text_part = MagicMock(text="Hello")
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = [MagicMock(content=MagicMock(parts=[text_part]))]

        async def _mock_stream():
            yield chunk

        proc.client.aio.models.generate_content_stream = AsyncMock(
            return_value=_mock_stream()
        )

        chunks = [
            c
            async for c in proc._stream_generation(
                "gemini-2.5-flash",
                [types.Content(role="user", parts=[types.Part(text="Hi")])],
                types.GenerateContentConfig(temperature=0.7),
                cancel,
            )
        ]
        # Should be empty or minimal since cancelled
        assert len(chunks) == 0


# ============================================================================
# _mcp_context_manager
# ============================================================================


class TestMcpContextManager:
    @pytest.mark.asyncio
    async def test_empty_wrappers(self) -> None:
        proc = _make_processor()
        async with proc._mcp_context_manager([]) as contexts:
            assert contexts == []

    @pytest.mark.asyncio
    async def test_connection_failure_skipped(self) -> None:
        proc = _make_processor()
        wrapper = MCPSessionWrapper("https://invalid", {}, "FailServer")

        with patch(f"{_PATCH}.httpx.AsyncClient", side_effect=RuntimeError("oops")):
            async with proc._mcp_context_manager([wrapper]) as contexts:
                # Should continue with empty contexts
                assert len(contexts) == 0


# ============================================================================
# Init error handling
# ============================================================================


class TestInitErrors:
    def test_api_key_none_disables_client(self) -> None:
        proc = _make_processor(api_key=None)
        assert proc.client is None

    def test_client_creation_error(self) -> None:
        with patch(f"{_PATCH}.genai.Client", side_effect=RuntimeError("bad key")):
            proc = GeminiResponsesProcessor(
                models={"m": _model()},
                api_key="test-key",
                oauth_redirect_uri="https://test/cb",
            )
        assert proc.client is None

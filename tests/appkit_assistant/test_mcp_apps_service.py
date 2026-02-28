"""Tests for McpAppsService.

Covers UI tool discovery, resource fetching, tool call proxying,
app support detection, and caching.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.schemas import (
    McpAppToolInfo,
    MCPAuthType,
)
from appkit_assistant.backend.services.mcp_apps_service import (
    McpAppsService,
    _call_tool_result_to_dict,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_server(
    server_id: int = 1,
    server_name: str = "TestServer",
    url: str = "https://mcp.test/sse",
    auth_type: str = MCPAuthType.NONE,
    headers: str = "{}",
) -> MagicMock:
    server = MagicMock()
    server.id = server_id
    server.name = server_name
    server.url = url
    server.auth_type = auth_type
    server.headers = headers
    return server


def _make_tool(
    name: str = "qr_code",
    meta: dict | None = None,
    input_schema: dict | None = None,
) -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.meta = meta
    tool.inputSchema = input_schema or {"type": "object"}
    return tool


def _make_tool_with_ui(
    name: str = "qr_code",
    resource_uri: str = "ui://qr_code/view",
    visibility: list[str] | None = None,
) -> MagicMock:
    return _make_tool(
        name=name,
        meta={
            "ui": {
                "resourceUri": resource_uri,
                "visibility": visibility or [],
            }
        },
    )


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_defaults(self) -> None:
        service = McpAppsService()
        assert service._token_service is None
        assert service._tool_cache == {}
        assert service._apps_support_cache == {}

    def test_with_token_service(self) -> None:
        token_service = MagicMock()
        service = McpAppsService(token_service=token_service)
        assert service._token_service is token_service


# ============================================================================
# _extract_ui_tool_info
# ============================================================================


class TestExtractUiToolInfo:
    def test_tool_with_ui_metadata(self) -> None:
        service = McpAppsService()
        server = _make_server()
        tool = _make_tool_with_ui(
            name="qr_code",
            resource_uri="ui://qr_code/view",
            visibility=["app"],
        )

        result = service._extract_ui_tool_info(tool, server)

        assert result is not None
        assert result.tool_name == "qr_code"
        assert result.resource_uri == "ui://qr_code/view"
        assert result.visibility == ["app"]
        assert result.server_id == 1
        assert result.server_label == "TestServer"

    def test_tool_without_ui_metadata(self) -> None:
        service = McpAppsService()
        server = _make_server()
        tool = _make_tool(name="plain_tool", meta={})

        result = service._extract_ui_tool_info(tool, server)
        assert result is None

    def test_tool_with_no_meta(self) -> None:
        service = McpAppsService()
        server = _make_server()
        tool = _make_tool(name="plain_tool", meta=None)

        result = service._extract_ui_tool_info(tool, server)
        assert result is None

    def test_tool_with_empty_resource_uri(self) -> None:
        service = McpAppsService()
        server = _make_server()
        tool = _make_tool(
            name="tool",
            meta={"ui": {"resourceUri": ""}},
        )

        result = service._extract_ui_tool_info(tool, server)
        assert result is None

    def test_tool_with_input_schema(self) -> None:
        service = McpAppsService()
        server = _make_server()
        schema = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        }
        tool = _make_tool_with_ui(name="gen")
        tool.inputSchema = schema

        result = service._extract_ui_tool_info(tool, server)
        assert result is not None
        assert result.input_schema == schema


# ============================================================================
# discover_ui_tools
# ============================================================================


class TestDiscoverUiTools:
    @pytest.mark.asyncio
    async def test_returns_empty_for_none_server_id(self) -> None:
        service = McpAppsService()
        server = _make_server(server_id=None)

        result = await service.discover_ui_tools(server, user_id=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_cached_tools(self) -> None:
        service = McpAppsService()
        cached_tools = [
            McpAppToolInfo(
                tool_name="cached_tool",
                resource_uri="ui://test",
                server_id=1,
                server_label="Test",
            )
        ]
        service._tool_cache[(1, 1)] = (cached_tools, time.monotonic())

        result = await service.discover_ui_tools(_make_server(), user_id=1)
        assert len(result) == 1
        assert result[0].tool_name == "cached_tool"

    @pytest.mark.asyncio
    async def test_expired_cache_triggers_refetch(self) -> None:
        service = McpAppsService()
        # Set expired cache
        service._tool_cache[(1, 1)] = (
            [],
            time.monotonic() - 400,  # expired
        )

        with patch.object(
            service,
            "_fetch_ui_tools",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_fetch:
            result = await service.discover_ui_tools(_make_server(), user_id=1)
            assert result == []
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with patch.object(
            service,
            "_fetch_ui_tools",
            new_callable=AsyncMock,
            side_effect=ConnectionError("fail"),
        ):
            result = await service.discover_ui_tools(_make_server(), user_id=1)
            assert result == []


# ============================================================================
# fetch_resource
# ============================================================================


class TestFetchResource:
    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with patch(
            "appkit_assistant.backend.services.mcp_apps_service.streamablehttp_client",
            side_effect=ConnectionError("fail"),
        ):
            result = await service.fetch_resource(
                _make_server(),
                user_id=1,
                resource_uri="ui://test",
            )
            assert result is None


# ============================================================================
# proxy_tool_call
# ============================================================================


class TestProxyToolCall:
    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with patch(
            "appkit_assistant.backend.services.mcp_apps_service.streamablehttp_client",
            side_effect=ConnectionError("fail"),
        ):
            result = await service.proxy_tool_call(
                _make_server(),
                user_id=1,
                tool_name="test_tool",
                arguments={"key": "value"},
            )
            assert result == {"isError": True, "content": []}


# ============================================================================
# is_apps_supported
# ============================================================================


class TestIsAppsSupported:
    @pytest.mark.asyncio
    async def test_returns_false_for_none_server_id(self) -> None:
        service = McpAppsService()
        server = _make_server(server_id=None)

        result = await service.is_apps_supported(server, user_id=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_cached_result(self) -> None:
        service = McpAppsService()
        service._apps_support_cache[(1, 1)] = (
            True,
            time.monotonic(),
        )

        result = await service.is_apps_supported(_make_server(), user_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_checks_ui_tools(self) -> None:
        service = McpAppsService()

        with patch.object(
            service,
            "discover_ui_tools",
            new_callable=AsyncMock,
            return_value=[
                McpAppToolInfo(
                    tool_name="tool",
                    resource_uri="ui://test",
                    server_id=1,
                    server_label="Test",
                )
            ],
        ):
            result = await service.is_apps_supported(_make_server(), user_id=1)
            assert result is True


# ============================================================================
# get_cached_ui_tools
# ============================================================================


class TestGetCachedUiTools:
    def test_returns_empty_when_no_cache(self) -> None:
        service = McpAppsService()
        result = service.get_cached_ui_tools(1, 1)
        assert result == []

    def test_returns_cached_tools(self) -> None:
        service = McpAppsService()
        tools = [
            McpAppToolInfo(
                tool_name="cached",
                resource_uri="ui://test",
                server_id=1,
                server_label="Test",
            )
        ]
        service._tool_cache[(1, 1)] = (tools, time.monotonic())

        result = service.get_cached_ui_tools(1, 1)
        assert len(result) == 1
        assert result[0].tool_name == "cached"

    def test_returns_empty_for_expired_cache(self) -> None:
        service = McpAppsService()
        tools = [
            McpAppToolInfo(
                tool_name="expired",
                resource_uri="ui://test",
                server_id=1,
                server_label="Test",
            )
        ]
        service._tool_cache[(1, 1)] = (
            tools,
            time.monotonic() - 400,
        )

        result = service.get_cached_ui_tools(1, 1)
        assert result == []


# ============================================================================
# build_ui_tool_registry
# ============================================================================


class TestBuildUiToolRegistry:
    def test_builds_mapping(self) -> None:
        service = McpAppsService()
        tools = [
            McpAppToolInfo(
                tool_name="tool_a",
                resource_uri="ui://a",
                server_id=1,
                server_label="Server",
            ),
            McpAppToolInfo(
                tool_name="tool_b",
                resource_uri="ui://b",
                server_id=1,
                server_label="Server",
            ),
        ]

        registry = service.build_ui_tool_registry(tools)
        assert "tool_a" in registry
        assert "tool_b" in registry
        assert registry["tool_a"].resource_uri == "ui://a"

    def test_empty_list(self) -> None:
        service = McpAppsService()
        registry = service.build_ui_tool_registry([])
        assert registry == {}


# ============================================================================
# _get_auth_headers
# ============================================================================


class TestGetAuthHeaders:
    @pytest.mark.asyncio
    async def test_no_auth_type(self) -> None:
        service = McpAppsService()
        server = _make_server(auth_type=MCPAuthType.NONE)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {}

    @pytest.mark.asyncio
    async def test_oauth_with_token(self) -> None:
        token_service = AsyncMock()
        token = MagicMock()
        token.access_token = "test-token-123"
        token_service.get_valid_token = AsyncMock(return_value=token)

        service = McpAppsService(token_service=token_service)
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers["Authorization"] == "Bearer test-token-123"

    @pytest.mark.asyncio
    async def test_oauth_without_token(self) -> None:
        token_service = AsyncMock()
        token_service.get_valid_token = AsyncMock(return_value=None)

        service = McpAppsService(token_service=token_service)
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {}

    @pytest.mark.asyncio
    async def test_oauth_without_token_service(self) -> None:
        service = McpAppsService(token_service=None)
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {}


# ============================================================================
# _call_tool_result_to_dict
# ============================================================================


class TestCallToolResultToDict:
    def test_success_result(self) -> None:
        result = MagicMock()
        result.isError = False
        content_item = MagicMock()
        content_item.model_dump.return_value = {
            "type": "text",
            "text": "hello",
        }
        result.content = [content_item]

        converted = _call_tool_result_to_dict(result)
        assert converted["isError"] is False
        assert len(converted["content"]) == 1
        assert converted["content"][0]["text"] == "hello"

    def test_error_result(self) -> None:
        result = MagicMock()
        result.isError = True
        result.content = []

        converted = _call_tool_result_to_dict(result)
        assert converted["isError"] is True
        assert converted["content"] == []

    def test_none_is_error(self) -> None:
        result = MagicMock()
        result.isError = None
        result.content = []

        converted = _call_tool_result_to_dict(result)
        assert converted["isError"] is False

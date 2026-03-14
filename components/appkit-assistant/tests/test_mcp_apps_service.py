"""Tests for McpAppsService.

Covers UI tool discovery, resource fetching, tool call proxying,
app support detection, caching, auth headers, and session initialization.
"""

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.schemas import (
    McpAppToolInfo,
    MCPAuthType,
)
from appkit_assistant.backend.services.mcp_apps_service import (
    McpAppsService,
    _call_tool_result_to_dict,
    _McpAppsClientSession,
)


@pytest.fixture(autouse=True)
def _clear_tool_cache() -> None:
    """Reset the class-level tool cache between tests."""
    McpAppsService._tool_cache.clear()


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


@asynccontextmanager
async def _mock_streamable_http_client(
    session_mock: AsyncMock | None = None,
):
    """Create a mock context manager for streamable_http_client.

    Yields (read_stream, write_stream, _) triple.
    When combined with _McpAppsClientSession patching, allows
    testing the full connection flow.
    """
    read_stream = AsyncMock()
    write_stream = AsyncMock()
    yield read_stream, write_stream, None


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_defaults(self) -> None:
        service = McpAppsService()
        assert service._token_service is None
        assert McpAppsService._tool_cache == {}

    def test_with_token_service(self) -> None:
        token_service = MagicMock()
        service = McpAppsService(token_service=token_service)
        assert service._token_service is token_service


# ============================================================================
# _McpAppsClientSession.initialize
# ============================================================================


class TestMcpAppsClientSession:
    @pytest.mark.asyncio
    async def test_initialize_sends_request_and_notification(self) -> None:
        # Create a mock result for the initialize response
        init_result = MagicMock()
        init_result.capabilities = MagicMock()
        init_result.protocolVersion = "2025-11-25"

        with (
            patch.object(
                _McpAppsClientSession,
                "send_request",
                new_callable=AsyncMock,
                return_value=init_result,
            ) as mock_send_req,
            patch.object(
                _McpAppsClientSession,
                "send_notification",
                new_callable=AsyncMock,
            ) as mock_send_notif,
        ):
            session = _McpAppsClientSession.__new__(_McpAppsClientSession)
            result = await session.initialize()

            assert result is init_result
            mock_send_req.assert_called_once()
            mock_send_notif.assert_called_once()

            # Verify the request includes the UI extension
            call_args = mock_send_req.call_args
            request = call_args[0][0]
            caps = request.root.params.capabilities
            assert "extensions" in caps.experimental
            ext = caps.experimental["extensions"]
            assert "io.modelcontextprotocol/ui" in ext

    @pytest.mark.asyncio
    async def test_initialize_stores_server_capabilities(self) -> None:
        init_result = MagicMock()
        init_result.capabilities = MagicMock(spec=["tools"])
        init_result.protocolVersion = "2025-11-25"

        with (
            patch.object(
                _McpAppsClientSession,
                "send_request",
                new_callable=AsyncMock,
                return_value=init_result,
            ),
            patch.object(
                _McpAppsClientSession,
                "send_notification",
                new_callable=AsyncMock,
            ),
        ):
            session = _McpAppsClientSession.__new__(_McpAppsClientSession)
            await session.initialize()

            assert session._server_capabilities is init_result.capabilities


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

    def test_tool_with_no_meta_attribute(self) -> None:
        """Tool object without meta attribute at all."""
        service = McpAppsService()
        server = _make_server()
        tool = MagicMock(spec=[])
        tool.name = "no_meta"
        # no meta attribute
        result = service._extract_ui_tool_info(tool, server)
        assert result is None


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
        service._tool_cache[(1, 1)] = (
            [],
            time.monotonic() - 400,
        )

        with (
            patch.object(
                service,
                "_list_ui_tools",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_list,
            patch.object(service, "_connect_for_apps") as mock_connect,
        ):
            mock_connect.return_value.__aenter__.return_value = AsyncMock()

            result = await service.discover_ui_tools(_make_server(), user_id=1)
            assert result == []
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with patch.object(
            service,
            "_connect_for_apps",
            side_effect=ConnectionError("fail"),
        ):
            result = await service.discover_ui_tools(_make_server(), user_id=1)
            assert result == []

    @pytest.mark.asyncio
    async def test_successful_fetch_caches_result(self) -> None:
        service = McpAppsService()
        tools = [
            McpAppToolInfo(
                tool_name="discovered",
                resource_uri="ui://test",
                server_id=1,
                server_label="Test",
            )
        ]

        with (
            patch.object(
                service,
                "_list_ui_tools",
                new_callable=AsyncMock,
                return_value=tools,
            ),
            patch.object(service, "_connect_for_apps") as mock_connect,
        ):
            mock_connect.return_value.__aenter__.return_value = AsyncMock()

            result = await service.discover_ui_tools(_make_server(), user_id=1)
            assert len(result) == 1
            # Verify cache was populated
            assert (1, 1) in service._tool_cache
            cached_tools, _ = service._tool_cache[(1, 1)]
            assert cached_tools[0].tool_name == "discovered"

    @pytest.mark.asyncio
    async def test_cache_shared_across_instances(self) -> None:
        """Cache survives across McpAppsService instances."""
        tools = [
            McpAppToolInfo(
                tool_name="shared",
                resource_uri="ui://test",
                server_id=1,
                server_label="Test",
            )
        ]
        service1 = McpAppsService()

        with (
            patch.object(
                service1,
                "_list_ui_tools",
                new_callable=AsyncMock,
                return_value=tools,
            ),
            patch.object(service1, "_connect_for_apps") as mock_connect,
        ):
            mock_connect.return_value.__aenter__.return_value = AsyncMock()
            await service1.discover_ui_tools(_make_server(), user_id=1)

        # A new instance should see the cached tools without connecting
        service2 = McpAppsService()
        result = await service2.discover_ui_tools(_make_server(), user_id=1)
        assert len(result) == 1
        assert result[0].tool_name == "shared"


# ============================================================================
# _fetch_ui_tools
# ============================================================================


class TestFetchUiTools:
    @pytest.mark.asyncio
    async def test_fetches_and_filters_ui_tools(self) -> None:
        service = McpAppsService()
        server = _make_server()

        ui_tool = _make_tool_with_ui(name="qr_code", resource_uri="ui://qr/view")
        plain_tool = _make_tool(name="plain", meta={})

        mock_list_result = MagicMock()
        mock_list_result.tools = [ui_tool, plain_tool]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_list_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.discover_ui_tools(server, 1)

        assert len(result) == 1
        assert result[0].tool_name == "qr_code"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_ui_tools(self) -> None:
        service = McpAppsService()
        server = _make_server()

        plain_tool = _make_tool(name="plain", meta={})

        mock_list_result = MagicMock()
        mock_list_result.tools = [plain_tool]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_list_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.discover_ui_tools(server, 1)

        assert result == []


# ============================================================================
# fetch_resource
# ============================================================================


class TestFetchResource:
    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with (
            patch.object(
                service,
                "_get_auth_headers",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient",
                side_effect=ConnectionError("fail"),
            ),
        ):
            result = await service.fetch_resource(
                _make_server(),
                user_id=1,
                resource_uri="ui://test",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_resource_with_html_content(self) -> None:
        service = McpAppsService()
        server = _make_server()

        content_item = MagicMock()
        content_item.text = "<h1>Hello World</h1>"
        content_item._meta = None

        mock_read_result = MagicMock()
        mock_read_result.contents = [content_item]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.read_resource = AsyncMock(return_value=mock_read_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.fetch_resource(server, 1, "ui://test/view")

        assert result is not None
        assert result.html_content == "<h1>Hello World</h1>"
        assert result.uri == "ui://test/view"
        assert result.csp is None
        assert result.prefers_border is None

    @pytest.mark.asyncio
    async def test_returns_resource_with_ui_meta(self) -> None:
        service = McpAppsService()
        server = _make_server()

        content_item = MagicMock()
        content_item.text = "<div>Styled</div>"
        content_item._meta = {
            "ui": {
                "csp": {"default-src": "'self'"},
                "permissions": {"allow-scripts": True},
                "prefersBorder": True,
            }
        }

        mock_read_result = MagicMock()
        mock_read_result.contents = [content_item]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.read_resource = AsyncMock(return_value=mock_read_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.fetch_resource(server, 1, "ui://styled/view")

        assert result is not None
        assert result.csp == {"default-src": "'self'"}
        assert result.permissions == {"allow-scripts": True}
        assert result.prefers_border is True

    @pytest.mark.asyncio
    async def test_concatenates_multiple_content_parts(self) -> None:
        service = McpAppsService()
        server = _make_server()

        part1 = MagicMock()
        part1.text = "<h1>Title</h1>"
        part1._meta = None

        part2 = MagicMock()
        part2.text = "<p>Body</p>"
        part2._meta = None

        mock_read_result = MagicMock()
        mock_read_result.contents = [part1, part2]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.read_resource = AsyncMock(return_value=mock_read_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.fetch_resource(server, 1, "ui://multi")

        assert result is not None
        assert result.html_content == "<h1>Title</h1><p>Body</p>"


# ============================================================================
# proxy_tool_call
# ============================================================================


class TestProxyToolCall:
    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        service = McpAppsService()

        with (
            patch.object(
                service,
                "_get_auth_headers",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient",
                side_effect=ConnectionError("fail"),
            ),
        ):
            result = await service.proxy_tool_call(
                _make_server(),
                user_id=1,
                tool_name="test_tool",
                arguments={"key": "value"},
            )
            assert result == {"isError": True, "content": []}

    @pytest.mark.asyncio
    async def test_successful_tool_call(self) -> None:
        service = McpAppsService()
        server = _make_server()

        content_item = MagicMock()
        content_item.model_dump.return_value = {
            "type": "text",
            "text": "result data",
        }

        mock_call_result = MagicMock()
        mock_call_result.isError = False
        mock_call_result.content = [content_item]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_call_result)

        @asynccontextmanager
        async def mock_http_client(url, http_client=None):
            yield AsyncMock(), AsyncMock(), None

        with (
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.httpx.AsyncClient"
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service.streamable_http_client",
                side_effect=mock_http_client,
            ),
            patch(
                "appkit_assistant.backend.services.mcp_apps_service._McpAppsClientSession",
            ) as mock_session_cls,
        ):
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_ctx

            result = await service.proxy_tool_call(
                server, 1, "gen_qr", {"text": "hello"}
            )

        assert result["isError"] is False
        assert len(result["content"]) == 1
        assert result["content"][0]["text"] == "result data"
        mock_session.call_tool.assert_called_once_with("gen_qr", {"text": "hello"})


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
    async def test_returns_true_if_tools_found(self) -> None:
        service = McpAppsService()

        with patch.object(
            service, "discover_ui_tools", new_callable=AsyncMock
        ) as mock_disc:
            mock_disc.return_value = [
                McpAppToolInfo(
                    tool_name="x", resource_uri="y", server_id=1, server_label="z"
                )
            ]
            result = await service.is_apps_supported(_make_server(), user_id=1)
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_if_no_tools(self) -> None:
        service = McpAppsService()

        with patch.object(
            service, "discover_ui_tools", new_callable=AsyncMock
        ) as mock_disc:
            mock_disc.return_value = []
            result = await service.is_apps_supported(_make_server(), user_id=1)
            assert result is False


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
        assert headers == {"x-user-id": "1"}

    @pytest.mark.asyncio
    async def test_api_key_headers_from_json(self) -> None:
        service = McpAppsService()
        server = _make_server(
            auth_type=MCPAuthType.API_KEY,
            headers='{"X-Api-Key": "secret-123"}',
        )

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers["X-Api-Key"] == "secret-123"

    @pytest.mark.asyncio
    async def test_api_key_invalid_json(self) -> None:
        service = McpAppsService()
        server = _make_server(
            auth_type=MCPAuthType.API_KEY,
            headers="not-valid-json",
        )

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {"x-user-id": "1"}

    @pytest.mark.asyncio
    async def test_api_key_empty_json(self) -> None:
        service = McpAppsService()
        server = _make_server(
            auth_type=MCPAuthType.API_KEY,
            headers="{}",
        )

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {"x-user-id": "1"}

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
        assert headers == {"x-user-id": "1"}

    @pytest.mark.asyncio
    async def test_oauth_without_token_service(self) -> None:
        service = McpAppsService(token_service=None)
        server = _make_server(auth_type=MCPAuthType.OAUTH_DISCOVERY)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {"x-user-id": "1"}

    @pytest.mark.asyncio
    async def test_none_headers_field(self) -> None:
        service = McpAppsService()
        server = _make_server(headers=None)

        headers = await service._get_auth_headers(server, user_id=1)
        assert headers == {"x-user-id": "1"}


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

    def test_multiple_content_items(self) -> None:
        result = MagicMock()
        result.isError = False
        item1 = MagicMock()
        item1.model_dump.return_value = {"type": "text", "text": "a"}
        item2 = MagicMock()
        item2.model_dump.return_value = {"type": "text", "text": "b"}
        result.content = [item1, item2]

        converted = _call_tool_result_to_dict(result)
        assert len(converted["content"]) == 2

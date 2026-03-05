"""Tests for MCP Apps API endpoints.

Covers resource fetching, tool call proxying, UI tool listing,
lazy service initialization, server lookup, and schema validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import appkit_assistant.backend.api.mcp_apps_api as api_module
from appkit_assistant.backend.api.mcp_apps_api import (
    ToolCallRequest,
    _extract_user_id,
    _get_mcp_apps_service,
    _get_server,
    call_tool,
    get_resource,
    list_ui_tools,
)
from appkit_assistant.backend.schemas import (
    McpAppResource,
    McpAppToolInfo,
    McpAppViewData,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_server_mock(
    server_id: int = 1,
    name: str = "TestServer",
) -> MagicMock:
    server = MagicMock()
    server.id = server_id
    server.name = name
    server.model_dump.return_value = {
        "id": server_id,
        "name": name,
        "url": "https://mcp.test/sse",
        "auth_type": "none",
        "headers": "{}",
    }
    return server


# ============================================================================
# ToolCallRequest schema
# ============================================================================


class TestToolCallRequest:
    def test_default_arguments(self) -> None:
        req = ToolCallRequest(tool_name="test")
        assert req.tool_name == "test"
        assert req.arguments == {}

    def test_with_arguments(self) -> None:
        req = ToolCallRequest(
            tool_name="gen",
            arguments={"text": "hello"},
        )
        assert req.arguments == {"text": "hello"}


# ============================================================================
# User ID extraction
# ============================================================================


class TestExtractUserId:
    def test_no_session_returns_default(self) -> None:
        assert _extract_user_id(None) == 0

    def test_empty_session_returns_default(self) -> None:
        assert _extract_user_id("") == 0

    def test_with_session_returns_default(self) -> None:
        assert _extract_user_id("some-session-token") == 0


# ============================================================================
# Lazy service initialization
# ============================================================================


class TestGetMcpAppsService:
    def test_creates_service_on_first_call(self) -> None:
        original = api_module._mcp_apps_service
        try:
            api_module._mcp_apps_service = None
            service = _get_mcp_apps_service()
            assert service is not None
            assert service._token_service is not None
        finally:
            api_module._mcp_apps_service = original

    def test_returns_cached_service_on_second_call(self) -> None:
        original = api_module._mcp_apps_service
        try:
            api_module._mcp_apps_service = None
            first = _get_mcp_apps_service()
            second = _get_mcp_apps_service()
            assert first is second
        finally:
            api_module._mcp_apps_service = original


# ============================================================================
# get_resource endpoint
# ============================================================================


class TestGetResourceEndpoint:
    @pytest.mark.asyncio
    async def test_returns_html_response(self) -> None:
        resource = McpAppResource(
            uri="ui://test/view",
            html_content="<h1>Hello</h1>",
        )
        mock_service = AsyncMock()
        mock_service.fetch_resource = AsyncMock(return_value=resource)

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            response = await get_resource(server_id=1, uri="ui://test/view")
            assert response.status_code == 200
            assert response.body == b"<h1>Hello</h1>"

    @pytest.mark.asyncio
    async def test_returns_resource_headers(self) -> None:
        resource = McpAppResource(
            uri="ui://test/view",
            html_content="<div>OK</div>",
            csp={"default-src": "'self'"},
            permissions={"allow-scripts": True},
            prefers_border=True,
        )
        mock_service = AsyncMock()
        mock_service.fetch_resource = AsyncMock(return_value=resource)

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            response = await get_resource(server_id=1, uri="ui://test/view")
            assert response.headers["x-mcp-resource-uri"] == "ui://test/view"
            assert "x-mcp-csp" in response.headers
            assert "x-mcp-permissions" in response.headers
            assert response.headers["x-mcp-prefers-border"] == "true"

    @pytest.mark.asyncio
    async def test_returns_502_when_resource_is_none(self) -> None:
        mock_service = AsyncMock()
        mock_service.fetch_resource = AsyncMock(return_value=None)

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
            pytest.raises(Exception) as exc_info,
        ):
            await get_resource(server_id=1, uri="ui://broken")
        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_omits_optional_headers_when_none(self) -> None:
        resource = McpAppResource(
            uri="ui://test/view",
            html_content="<p>No extras</p>",
        )
        mock_service = AsyncMock()
        mock_service.fetch_resource = AsyncMock(return_value=resource)

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            response = await get_resource(server_id=1, uri="ui://test/view")
            assert "x-mcp-csp" not in response.headers
            assert "x-mcp-permissions" not in response.headers
            assert "x-mcp-prefers-border" not in response.headers


# ============================================================================
# call_tool endpoint
# ============================================================================


class TestCallToolEndpoint:
    @pytest.mark.asyncio
    async def test_proxies_tool_call(self) -> None:
        mock_service = AsyncMock()
        mock_service.proxy_tool_call = AsyncMock(
            return_value={"isError": False, "content": [{"type": "text", "text": "ok"}]}
        )

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            request = ToolCallRequest(tool_name="gen", arguments={"text": "hi"})
            result = await call_tool(server_id=1, request=request)
            assert result["isError"] is False
            mock_service.proxy_tool_call.assert_called_once()


# ============================================================================
# list_ui_tools endpoint
# ============================================================================


class TestListUiToolsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_tool_list(self) -> None:
        tool_info = McpAppToolInfo(
            tool_name="qr_code",
            resource_uri="ui://qr/view",
            server_id=1,
            server_label="Server",
        )
        mock_service = AsyncMock()
        mock_service.discover_ui_tools = AsyncMock(return_value=[tool_info])

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            result = await list_ui_tools(server_id=1)
            assert len(result) == 1
            assert result[0]["tool_name"] == "qr_code"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        mock_service = AsyncMock()
        mock_service.discover_ui_tools = AsyncMock(return_value=[])

        with (
            patch.object(
                api_module, "_get_mcp_apps_service", return_value=mock_service
            ),
            patch(
                "appkit_assistant.backend.api.mcp_apps_api._get_server",
                new_callable=AsyncMock,
                return_value=_make_server_mock(),
            ),
        ):
            result = await list_ui_tools(server_id=1)
            assert result == []


# ============================================================================
# _get_server helper
# ============================================================================


class TestGetServer:
    @pytest.mark.asyncio
    async def test_returns_server_when_found(self) -> None:
        server_mock = _make_server_mock()

        mock_session = AsyncMock()
        with (
            patch(
                "appkit_assistant.backend.api.mcp_apps_api.get_asyncdb_session",
            ) as mock_ctx,
            patch(
                "appkit_assistant.backend.api.mcp_apps_api.mcp_server_repo",
            ) as mock_repo,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=server_mock)

            result = await _get_server(1)
            assert result is not None

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self) -> None:
        mock_session = AsyncMock()
        with (
            patch(
                "appkit_assistant.backend.api.mcp_apps_api.get_asyncdb_session",
            ) as mock_ctx,
            patch(
                "appkit_assistant.backend.api.mcp_apps_api.mcp_server_repo",
            ) as mock_repo,
            pytest.raises(Exception) as exc_info,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            await _get_server(999)
        assert exc_info.value.status_code == 404


# ============================================================================
# Pydantic schemas
# ============================================================================


class TestSchemas:
    def test_mcp_app_tool_info(self) -> None:
        tool = McpAppToolInfo(
            tool_name="test",
            resource_uri="ui://test",
            server_id=1,
            server_label="Server",
        )
        assert tool.tool_name == "test"
        assert tool.visibility == []
        assert tool.input_schema == {}

    def test_mcp_app_resource(self) -> None:
        resource = McpAppResource(
            uri="ui://test",
            html_content="<h1>Hello</h1>",
        )
        assert resource.html_content == "<h1>Hello</h1>"
        assert resource.csp is None
        assert resource.permissions is None
        assert resource.prefers_border is None

    def test_mcp_app_view_data(self) -> None:
        view = McpAppViewData(
            server_id=1,
            server_name="Server",
            resource_uri="ui://test",
            tool_name="test",
        )
        assert view.id  # UUID generated
        assert view.server_id == 1
        assert view.tool_input == {}
        assert view.tool_result is None
        assert view.html_content is None

    def test_mcp_app_view_data_with_all_fields(self) -> None:
        view = McpAppViewData(
            server_id=2,
            server_name="QR",
            resource_uri="ui://qr/view",
            tool_name="gen_qr",
            tool_input={"text": "hello"},
            tool_result={"status": "ok"},
            html_content="<div>QR</div>",
            csp={"default-src": "'self'"},
            permissions={"allow-scripts": True},
            prefers_border=True,
        )
        assert view.tool_input == {"text": "hello"}
        assert view.tool_result == {"status": "ok"}
        assert view.html_content == "<div>QR</div>"
        assert view.prefers_border is True

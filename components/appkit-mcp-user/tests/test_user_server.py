"""Tests for MCP User server tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp.client import Client
from starlette.requests import Request

from appkit_mcp_commons.context import UserContext
from appkit_mcp_commons.exceptions import AuthenticationError
from appkit_mcp_user.server import (
    _get_openai_client,
    _get_user_context,
    create_user_mcp_server,
)


async def test_query_users_tool(user_client: Client) -> None:
    """Test query_users tool calls service and returns JSON."""
    with (
        patch(
            "appkit_mcp_user.server._get_user_context",
            return_value=UserContext(user_id=1),
        ),
        patch(
            "appkit_mcp_user.server.query_users_table",
            new_callable=AsyncMock,
        ) as mock_query,
        patch(
            "appkit_mcp_user.server._get_openai_client",
            return_value=AsyncMock(),
        ),
    ):
        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.data = [{"id": 1, "email": "test@example.com"}]
        mock_result.columns = ["id", "email"]
        mock_result.row_count = 1
        mock_result.error = None
        mock_query.return_value = mock_result

        result = await user_client.call_tool(
            "query_users", arguments={"question": "Count users"}
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["row_count"] == 1
        assert response["data"][0]["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# create_user_mcp_server tests
# ---------------------------------------------------------------------------


class TestCreateUserMcpServer:
    def test_creates_server(self) -> None:
        """Server instance is created successfully."""
        mcp = create_user_mcp_server()
        assert mcp is not None

    def test_custom_name(self) -> None:
        """Server respects custom name."""
        mcp = create_user_mcp_server(name="custom-user")
        assert mcp.name == "custom-user"

    async def test_lists_tools(self, user_client: Client) -> None:
        """Server registers query_users tool."""
        tools = await user_client.list_tools()
        tool_names = {t.name for t in tools}
        assert "query_users" in tool_names


# ---------------------------------------------------------------------------
# _get_user_context tests
# ---------------------------------------------------------------------------


class TestGetUserContext:
    def test_no_session_cookie(self) -> None:
        """Request without session cookie returns default."""
        req = MagicMock(spec=Request)
        with patch(
            "appkit_mcp_user.server.extract_session_id",
            return_value=None,
        ):
            result = _get_user_context(req)
        assert result.user_id == 0

    def test_successful_auth(self) -> None:
        """Valid session ID returns authenticated context."""
        expected = UserContext(user_id=5, is_admin=True)
        req = MagicMock(spec=Request)
        with (
            patch(
                "appkit_mcp_user.server.extract_session_id",
                return_value="valid-session",
            ),
            patch(
                "appkit_mcp_user.server.authenticate_user",
                return_value=expected,
            ),
        ):
            result = _get_user_context(req)
        assert result.user_id == 5
        assert result.is_admin is True

    def test_auth_failure(self) -> None:
        """Authentication failure falls back to default context."""
        req = MagicMock(spec=Request)
        with (
            patch(
                "appkit_mcp_user.server.extract_session_id",
                return_value="bad-session",
            ),
            patch(
                "appkit_mcp_user.server.authenticate_user",
                side_effect=AuthenticationError("expired"),
            ),
        ):
            result = _get_user_context(req)
        assert result.user_id == 0
        assert result.is_admin is False


# ---------------------------------------------------------------------------
# _get_openai_client tests
# ---------------------------------------------------------------------------


class TestGetOpenaiClient:
    def test_success(self) -> None:
        """Returns client when service is available."""
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.create_client.return_value = mock_client

        with patch(
            "appkit_mcp_user.server.get_openai_client_service",
            return_value=mock_service,
        ):
            result = _get_openai_client()
        assert result is mock_client

    def test_failure(self) -> None:
        """Returns None when service is unavailable."""
        with patch(
            "appkit_mcp_user.server.get_openai_client_service",
            side_effect=RuntimeError("not registered"),
        ):
            result = _get_openai_client()
        assert result is None

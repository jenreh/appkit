"""Tests for MCP User server tools."""

import json
from unittest.mock import AsyncMock, patch

from fastmcp.client import Client

from appkit_mcp_user.server import (
    create_user_mcp_server,
)


async def test_query_users_tool(user_client: Client) -> None:
    """Test query_users tool calls service and returns JSON."""
    with (
        patch(
            "appkit_mcp_user.server.extract_user_id",
            return_value=1,
        ),
        patch(
            "appkit_mcp_user.server.query_users_table",
            new_callable=AsyncMock,
        ) as mock_query,
        patch(
            "appkit_mcp_user.server.get_openai_client",
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

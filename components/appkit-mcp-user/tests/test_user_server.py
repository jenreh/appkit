"""Tests for MCP User server tools."""

import json
from unittest.mock import AsyncMock, patch

from fastmcp.client import Client


async def test_query_users_tool(user_client: Client) -> None:
    """Test query_users tool calls service and returns JSON."""
    with (
        patch(
            "appkit_mcp_user.server.query_users_table", new_callable=AsyncMock
        ) as mock_query,
        patch("appkit_mcp_user.server._get_openai_client", return_value=AsyncMock()),
    ):
        # Define return structure matching what query_users expects
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

"""Unit tests for MCP server initialization and configuration."""

from unittest.mock import AsyncMock

from server.backend.generators.openai import OpenAIImageGenerator
from server.mcp_server import get_mcp_server


class TestMCPServerInitialization:
    """Test MCP server initialization and configuration."""

    def test_get_mcp_server_returns_fastmcp_instance(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test that get_mcp_server returns a FastMCP instance."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url="https://test.openai.azure.com",
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        mcp = get_mcp_server(generator)
        assert mcp is not None
        assert hasattr(mcp, "tool")

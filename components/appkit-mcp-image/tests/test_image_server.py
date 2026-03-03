"""Tests for the MCP Image server."""

from fastmcp.client import Client

from appkit_mcp_image.server import create_image_mcp_server


def test_creates_server() -> None:
    """Server instance is created successfully."""
    mcp = create_image_mcp_server()
    assert mcp is not None


def test_custom_name() -> None:
    """Server respects custom name parameter."""
    mcp = create_image_mcp_server(name="custom-image")
    assert mcp.name == "custom-image"


async def test_list_tools_empty(image_client: Client) -> None:
    """Server starts with no tools registered."""
    tools = await image_client.list_tools()
    assert tools == []

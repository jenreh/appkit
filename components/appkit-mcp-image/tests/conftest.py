"""Pytest fixtures for appkit-mcp-image tests."""

from collections.abc import AsyncIterator

import pytest
from fastmcp.client import Client

from appkit_mcp_image.server import create_image_mcp_server

pytest_plugins = ["appkit_commons.testing"]


@pytest.fixture
async def image_client() -> AsyncIterator[Client]:
    """Fixture providing a FastMCP Client for the Image server."""
    mcp = create_image_mcp_server()
    async with Client(mcp) as client:
        yield client

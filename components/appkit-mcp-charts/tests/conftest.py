"""Pytest fixtures for appkit-mcp-charts tests."""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import pytest
from fastmcp.client import Client
from starlette.requests import Request

from appkit_mcp_charts.server import create_charts_mcp_server

pytest_plugins = ["appkit_commons.testing"]


@pytest.fixture
def mock_request() -> Request:
    """Mock Starlette request."""
    req = Mock(spec=Request)
    req.cookies = {}
    return req


@pytest.fixture
async def charts_client() -> AsyncIterator[Client]:
    """Fixture providing a FastMCP Client for the Charts server."""
    mcp = create_charts_mcp_server()
    async with Client(mcp) as client:
        yield client

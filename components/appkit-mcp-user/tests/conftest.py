"""Pytest fixtures for appkit-mcp-user tests."""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import pytest
from fastmcp.client import Client
from starlette.requests import Request

from appkit_mcp_user.server import create_user_mcp_server

pytest_plugins = ["appkit_commons.testing"]


@pytest.fixture
def mock_request() -> Request:
    """Mock Starlette request."""
    req = Mock(spec=Request)
    req.cookies = {}
    return req


@pytest.fixture
def mock_auth_service() -> None:
    """Mock auth service."""
    # Service uses module-level functions, so just return None or mock the import
    return


@pytest.fixture
async def user_client(mock_auth_service: None) -> AsyncIterator[Client]:  # noqa: ARG001
    """Fixture providing a FastMCP Client for the User server."""
    mcp = create_user_mcp_server()
    async with Client(mcp) as client:
        yield client

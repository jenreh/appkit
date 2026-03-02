"""Pytest fixtures for appkit-mcp-user tests."""

from unittest.mock import Mock

import pytest
from starlette.requests import Request

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

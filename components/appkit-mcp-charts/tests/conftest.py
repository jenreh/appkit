"""Pytest fixtures for appkit-mcp-charts tests."""

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

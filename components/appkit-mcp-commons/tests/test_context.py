from unittest.mock import Mock

from starlette.requests import Request

from appkit_mcp_commons.context import (  # noqa: I001
    extract_session_id,
    get_user_context_default,
)


class MockFastMCPContext:
    def __init__(self, request: Request) -> None:
        self.request = request


def test_user_context_default() -> None:
    """Test default user context factory."""
    ctx = get_user_context_default()
    assert ctx.user_id == 0
    assert not ctx.is_admin
    assert ctx.roles == []


def test_extract_session_id_none() -> None:
    """Test extract session id from None."""
    session = extract_session_id(None)
    assert session is None


def test_extract_session_id_starlette_request() -> None:
    """Test extract from direct Starlette request."""
    req = Mock(spec=Request)
    req.cookies = {"reflex_session": "sess_123"}

    session = extract_session_id(req)
    assert session == "sess_123"


def test_extract_session_id_fastmcp_context() -> None:
    """Test extract from FastMCP context wrapper."""
    req = Mock(spec=Request)
    req.cookies = {"reflex_session": "sess_456"}
    ctx = MockFastMCPContext(request=req)

    session = extract_session_id(ctx)
    assert session == "sess_456"


def test_extract_session_no_cookie() -> None:
    """Test extract when no session cookie present."""
    req = Mock(spec=Request)
    req.cookies = {"other": "value"}

    session = extract_session_id(req)
    assert session is None

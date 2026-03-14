from unittest.mock import Mock

from starlette.requests import Request

from appkit_mcp_commons.context import (
    extract_session_id,
    extract_user_id,
    get_user_context_default,
)


def test_user_context_default() -> None:
    """Test default user context factory."""
    ctx = get_user_context_default()
    assert ctx.user_id == 0
    assert not ctx.is_admin
    assert ctx.roles == []


# ---------------------------------------------------------------------------
# extract_session_id
# ---------------------------------------------------------------------------


def test_extract_session_id_with_cookie() -> None:
    """Extract session from request with reflex_session cookie."""
    req = Mock(spec=Request)
    req.cookies = {"reflex_session": "sess_123"}

    assert extract_session_id(req) == "sess_123"


def test_extract_session_id_no_cookie() -> None:
    """Return None when no reflex_session cookie present."""
    req = Mock(spec=Request)
    req.cookies = {"other": "value"}

    assert extract_session_id(req) is None


def test_extract_session_id_no_cookies_attr() -> None:
    """Return None when request has no cookies attribute."""
    req = Mock(spec=[])  # no attributes

    assert extract_session_id(req) is None


# ---------------------------------------------------------------------------
# extract_user_id
# ---------------------------------------------------------------------------


def test_extract_user_id_from_header() -> None:
    """Extract user ID from x-user-id header."""
    req = Mock(spec=Request)
    req.headers = {"x-user-id": "42"}
    req.query_params = {}

    assert extract_user_id(req) == 42


def test_extract_user_id_from_query_param() -> None:
    """Fall back to URL query parameter when header is absent."""
    req = Mock(spec=Request)
    req.headers = {}
    req.query_params = {"x-user-id": "99"}

    assert extract_user_id(req) == 99


def test_extract_user_id_header_takes_precedence() -> None:
    """Header value wins over query parameter."""
    req = Mock(spec=Request)
    req.headers = {"x-user-id": "10"}
    req.query_params = {"x-user-id": "20"}

    assert extract_user_id(req) == 10


def test_extract_user_id_missing() -> None:
    """Return -1 when x-user-id is not present anywhere."""
    req = Mock(spec=Request)
    req.headers = {}
    req.query_params = {}

    assert extract_user_id(req) == -1


def test_extract_user_id_invalid() -> None:
    """Return -1 when x-user-id is not a valid integer."""
    req = Mock(spec=Request)
    req.headers = {"x-user-id": "not-a-number"}
    req.query_params = {}

    assert extract_user_id(req) == -1

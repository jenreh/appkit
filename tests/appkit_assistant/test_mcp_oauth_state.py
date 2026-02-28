# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for MCPOAuthState.

Covers handle_mcp_oauth_callback, _do_token_exchange,
_get_current_user_id, _build_redirect_uri.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.mcp_oauth_state import MCPOAuthState

_PATCH = "appkit_assistant.state.mcp_oauth_state"

_CV = MCPOAuthState.__dict__


def _unwrap(name: str):
    entry = MCPOAuthState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _sync_ctx(session: MagicMock | None = None):
    """Return a context-manager mock for sync sessions."""
    s = session or MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=s)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


class _StubMCPOAuthState:
    def __init__(self) -> None:
        self.status: str = "processing"
        self.message: str = "Verarbeite Anmeldung..."
        self.server_name: str = ""
        self._code: str = ""
        self._state: str = ""
        self._server_id: int | None = None
        self.router = MagicMock()
        self.router.url.query_parameters = {}

    handle_mcp_oauth_callback = _unwrap("handle_mcp_oauth_callback")
    _do_token_exchange = _unwrap("_do_token_exchange")
    _get_current_user_id = _unwrap("_get_current_user_id")
    _build_redirect_uri = _unwrap("_build_redirect_uri")

    async def get_state(self, cls: type) -> Any:
        return self._mock_user_session


def _make_state(
    params: dict[str, str] | None = None,
) -> _StubMCPOAuthState:
    s = _StubMCPOAuthState()
    if params:
        s.router.url.query_parameters = params
    return s


# ============================================================================
# _build_redirect_uri
# ============================================================================


class TestBuildRedirectUri:
    def test_delegates(self) -> None:
        state = _make_state()
        with patch(
            f"{_PATCH}.mcp_oauth_redirect_uri",
            return_value="http://localhost/cb",
        ):
            result = state._build_redirect_uri()
        assert result == "http://localhost/cb"


# ============================================================================
# _get_current_user_id
# ============================================================================


def _user_session(user_id: int | None):
    """Create a user session mock with awaitable property."""
    import asyncio

    future: asyncio.Future[None] = asyncio.Future()
    future.set_result(None)

    session = MagicMock()
    session.user_id = user_id
    session.authenticated_user = future
    return session


class TestGetCurrentUserId:
    @pytest.mark.asyncio
    async def test_valid_user(self) -> None:
        state = _make_state()
        state._mock_user_session = _user_session(42)
        result = await state._get_current_user_id()
        assert result == 42

    @pytest.mark.asyncio
    async def test_no_user_id(self) -> None:
        state = _make_state()
        state._mock_user_session = _user_session(0)
        result = await state._get_current_user_id()
        assert result is None

    @pytest.mark.asyncio
    async def test_none_user_id(self) -> None:
        state = _make_state()
        state._mock_user_session = _user_session(None)
        result = await state._get_current_user_id()
        assert result is None


# ============================================================================
# handle_mcp_oauth_callback
# ============================================================================


class TestHandleMcpOauthCallback:
    @pytest.mark.asyncio
    async def test_no_code(self) -> None:
        state = _make_state({"code": "", "state": "s1"})
        _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state.status == "error"
        assert "Autorisierungscode" in state.message

    @pytest.mark.asyncio
    async def test_missing_server_id_no_state(self) -> None:
        state = _make_state({"code": "abc123"})
        with patch(f"{_PATCH}.get_session_manager") as gsm:
            sess = MagicMock()
            gsm.return_value.session.return_value = _sync_ctx(sess)
            result = MagicMock()
            result.scalars.return_value.first.return_value = None
            sess.execute.return_value = result
            _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state.status == "error"
        assert "Server-ID" in state.message

    @pytest.mark.asyncio
    async def test_invalid_server_id(self) -> None:
        state = _make_state(
            {
                "code": "abc123",
                "state": "s1",
                "server_id": "not_int",
            }
        )
        _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state.status == "error"
        assert "Ungültige" in state.message

    @pytest.mark.asyncio
    async def test_server_not_found(self) -> None:
        state = _make_state({"code": "abc", "server_id": "1"})
        rx_session = _sync_ctx(MagicMock())
        rx_sess_mock = MagicMock()
        rx_sess_mock.exec.return_value.first.return_value = None
        rx_session.__enter__ = MagicMock(return_value=rx_sess_mock)
        with patch(f"{_PATCH}.rx.session", return_value=rx_session):
            _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state.status == "error"
        assert "nicht gefunden" in state.message

    @pytest.mark.asyncio
    async def test_not_logged_in(self) -> None:
        state = _make_state({"code": "abc", "server_id": "1"})

        server = MagicMock()
        server.name = "TestServer"
        server.id = 1

        rx_sess_mock = MagicMock()
        rx_sess_mock.exec.return_value.first.return_value = server
        rx_session = _sync_ctx(rx_sess_mock)

        state._mock_user_session = _user_session(0)

        with patch(f"{_PATCH}.rx.session", return_value=rx_session):
            _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state.status == "error"
        assert "angemeldet" in state.message

    @pytest.mark.asyncio
    async def test_recover_server_id_from_state(self) -> None:
        """When server_id is missing but state param present,
        recover from OAuthStateEntity."""
        state = _make_state({"code": "abc123", "state": "s1"})
        oauth_entity = MagicMock()
        oauth_entity.provider = "mcp:42"
        gsm = MagicMock()
        sess = MagicMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = oauth_entity
        sess.execute.return_value = result
        gsm.session.return_value = _sync_ctx(sess)

        server = MagicMock()
        server.name = "Recovered"
        server.id = 42
        rx_sess = MagicMock()
        rx_sess.exec.return_value.first.return_value = server

        state._mock_user_session = _user_session(1)

        async def fake_exchange(*a, **kw):
            state.status = "success"
            yield

        with (
            patch(
                f"{_PATCH}.get_session_manager",
                return_value=gsm,
            ),
            patch(
                f"{_PATCH}.rx.session",
                return_value=_sync_ctx(rx_sess),
            ),
            patch.object(
                _StubMCPOAuthState,
                "_do_token_exchange",
                new=fake_exchange,
            ),
        ):
            _ = [c async for c in state.handle_mcp_oauth_callback()]
        assert state._server_id == 42
        assert state.server_name == "Recovered"


# ============================================================================
# _do_token_exchange
# ============================================================================


class TestDoTokenExchange:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        session = MagicMock()
        server = MagicMock()
        server.name = "TestSrv"
        server.id = 1

        token_result = MagicMock()
        token_result.error = None

        auth_service = AsyncMock()
        auth_service.exchange_code_for_tokens = AsyncMock(return_value=token_result)
        auth_service.save_user_token = MagicMock()
        auth_service.close = AsyncMock()

        with (
            patch(
                f"{_PATCH}.mcp_oauth_redirect_uri",
                return_value="http://localhost/cb",
            ),
            patch(
                f"{_PATCH}.MCPAuthService",
                return_value=auth_service,
            ),
        ):
            _ = [
                c
                async for c in state._do_token_exchange(session, server, 1, "code", "s")
            ]
        assert state.status == "success"
        auth_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_error(self) -> None:
        state = _make_state()
        session = MagicMock()
        server = MagicMock()
        server.name = "TestSrv"
        server.id = 1

        token_result = MagicMock()
        token_result.error = "invalid_grant"
        token_result.error_description = "Bad grant"

        auth_service = AsyncMock()
        auth_service.exchange_code_for_tokens = AsyncMock(return_value=token_result)
        auth_service.close = AsyncMock()

        with (
            patch(
                f"{_PATCH}.mcp_oauth_redirect_uri",
                return_value="http://localhost",
            ),
            patch(
                f"{_PATCH}.MCPAuthService",
                return_value=auth_service,
            ),
        ):
            _ = [
                c
                async for c in state._do_token_exchange(session, server, 1, "code", "s")
            ]
        assert state.status == "error"
        assert "Bad grant" in state.message
        auth_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _make_state()
        session = MagicMock()
        server = MagicMock()
        server.name = "TestSrv"
        server.id = 1

        auth_service = AsyncMock()
        auth_service.exchange_code_for_tokens = AsyncMock(
            side_effect=RuntimeError("net error")
        )
        auth_service.close = AsyncMock()

        with (
            patch(
                f"{_PATCH}.mcp_oauth_redirect_uri",
                return_value="http://localhost",
            ),
            patch(
                f"{_PATCH}.MCPAuthService",
                return_value=auth_service,
            ),
        ):
            _ = [
                c
                async for c in state._do_token_exchange(session, server, 1, "code", "s")
            ]
        assert state.status == "error"
        assert "net error" in state.message
        auth_service.close.assert_called_once()

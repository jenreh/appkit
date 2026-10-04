# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for LoginState flows.

Covers the OAuth callback-path helper, computed vars, the session expiry
cache, password and provider login, OAuth callback handling, logout and
redirect logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _auth_state_stubs import (
    _LS_CV,
    _PATCH,
    _StubLoginState,
    _StubUserSession,
    _user,
    _user_entity,
)

from appkit_commons.testing import set_public_path_prefix
from appkit_user.authentication.session_validation import (
    SessionStatus,
    SessionValidationResult,
)
from appkit_user.authentication.states import LoginState, _session_monitor_interval

# The cache is capped at this, so a revoked session is picked up within it.
_MONITOR_INTERVAL = _session_monitor_interval()

# ============================================================================
# LoginState tests
# ============================================================================


class TestIsOAuthCallbackPath:
    def test_valid_callback(self) -> None:
        assert LoginState._is_oauth_callback_path("/oauth/azure/callback")

    def test_trailing_slash(self) -> None:
        assert LoginState._is_oauth_callback_path("/oauth/github/callback/")

    def test_not_callback(self) -> None:
        assert not LoginState._is_oauth_callback_path("/login")

    def test_incomplete_path(self) -> None:
        assert not LoginState._is_oauth_callback_path("/oauth/azure")


class TestComputedVars:
    def test_enable_azure_oauth(self) -> None:
        state = _StubLoginState()
        state._oauth_service.azure_enabled = True
        result = _LS_CV["enable_azure_oauth"].fget(state)
        assert result is True

    def test_enable_github_oauth(self) -> None:
        state = _StubLoginState()
        state._oauth_service.github_enabled = False
        result = _LS_CV["enable_github_oauth"].fget(state)
        assert result is False


class TestSessionExpiryCache:
    """Successor to the 60s ``_should_skip_auth_check`` clock throttle.

    The throttle skipped revalidation for a fixed interval regardless of when
    the session actually expired, so a session could stay usable for up to a
    minute past its expiry. The cache keys off the real expiry instant instead:
    authoritative until it, revalidating from it.
    """

    def test_no_cache_forces_validation(self) -> None:
        state = _StubLoginState()
        assert state._has_unexpired_cache() is False

    def test_future_expiry_is_authoritative(self) -> None:
        state = _StubLoginState()
        state._session_expires_at = datetime.now(UTC) + timedelta(minutes=5)
        assert state._has_unexpired_cache() is True

    def test_expiry_instant_ends_the_cache(self) -> None:
        """One microsecond past expiry the cache no longer answers."""
        state = _StubLoginState()
        state._session_expires_at = datetime.now(UTC) - timedelta(microseconds=1)
        assert state._has_unexpired_cache() is False

    def test_cache_session_adopts_valid_result(self) -> None:
        state = _StubUserSession()
        expires_at = datetime.now(UTC) + timedelta(minutes=25)

        state._cache_session(
            SessionValidationResult(
                SessionStatus.VALID, user=_user(7, "bob"), expires_at=expires_at
            )
        )

        assert state.user is not None
        assert state.user.name == "bob"
        assert state.user_id == 7
        # Capped at the monitor interval, NOT the session's own expiry: a
        # session revoked server-side must not stay usable for 25 minutes.
        assert state._session_expires_at is not None
        assert state._session_expires_at < expires_at
        assert state._session_expires_at <= datetime.now(UTC) + _MONITOR_INTERVAL

    def test_cache_session_uses_expiry_when_it_precedes_the_cap(self) -> None:
        """A session about to expire is trusted only until it actually does."""
        state = _StubUserSession()
        expires_at = datetime.now(UTC) + timedelta(seconds=5)

        state._cache_session(
            SessionValidationResult(
                SessionStatus.VALID, user=_user(7, "bob"), expires_at=expires_at
            )
        )

        assert state._session_expires_at == expires_at

    @pytest.mark.parametrize(
        "status", [SessionStatus.EXPIRED, SessionStatus.ABSENT, SessionStatus.ERROR]
    )
    def test_cache_session_ignores_denied_result(self, status: SessionStatus) -> None:
        """A denial must never prime the cache that lets the guards pass."""
        state = _StubUserSession()

        state._cache_session(SessionValidationResult(status))

        assert state.user is None
        assert state.user_id == 0
        assert state._session_expires_at is None


class TestLoginWithPassword:
    @pytest.mark.asyncio
    async def test_successful_login(self) -> None:
        state = _StubLoginState()
        entity = _user_entity(1, "alice")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.user_repo") as mock_u_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_u_repo.get_login_status_by_credentials = AsyncMock(
                return_value=(entity, "success")
            )
            mock_s_repo.save = AsyncMock()
            mock_s_repo.delete_by_user_and_session_id = AsyncMock()

            [
                c
                async for c in state.login_with_password(
                    {"username": "alice", "password": "pass"}
                )
            ]

        assert state.is_loading is False
        assert state.user is not None

    @pytest.mark.asyncio
    async def test_invalid_credentials(self) -> None:
        state = _StubLoginState()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.user_repo") as mock_u_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_u_repo.get_login_status_by_credentials = AsyncMock(
                return_value=(None, "invalid_credentials")
            )
            mock_s_repo.delete_by_user_and_session_id = AsyncMock()

            [
                c
                async for c in state.login_with_password(
                    {"username": "bad", "password": "bad"}
                )
            ]

        assert state.is_loading is False
        assert state.error_message != ""

    @pytest.mark.asyncio
    async def test_inactive_account(self) -> None:
        state = _StubLoginState()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.user_repo") as mock_u_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_u_repo.get_login_status_by_credentials = AsyncMock(
                return_value=(None, "inactive")
            )
            mock_s_repo.delete_by_user_and_session_id = AsyncMock()

            [
                c
                async for c in state.login_with_password(
                    {"username": "u", "password": "p"}
                )
            ]

        assert "deaktiviert" in state.error_message
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_exception_handled(self) -> None:
        state = _StubLoginState()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.user_repo") as mock_u_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_u_repo.get_login_status_by_credentials = AsyncMock(
                side_effect=RuntimeError("db crash")
            )
            mock_s_repo.delete_by_user_and_session_id = AsyncMock()

            [
                c
                async for c in state.login_with_password(
                    {"username": "u", "password": "p"}
                )
            ]

        assert state.is_loading is False
        # Raw exception text must not leak to the user; a generic message shows.
        assert "db crash" not in state.error_message
        assert state.error_message != ""


class TestLoginWithProvider:
    @pytest.mark.asyncio
    async def test_unsupported_provider(self) -> None:
        state = _StubLoginState()
        state._oauth_service.provider_supported.return_value = False

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            result = await state.login_with_provider("unknown")

        assert "unknown" in state.error_message.lower() or result is not None

    @pytest.mark.asyncio
    async def test_supported_provider(self) -> None:
        state = _StubLoginState()
        state._oauth_service.provider_supported.return_value = True
        state._oauth_service.get_auth_url.return_value = (
            "https://auth.example.com",
            "state123",
            "verifier",
        )

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.oauth_state_repo") as mock_o_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_s_repo.delete_by_user_and_session_id = AsyncMock()
            mock_o_repo.delete_expired = AsyncMock()
            mock_o_repo.delete_by_session_id = AsyncMock()
            mock_o_repo.create = AsyncMock()

            result = await state.login_with_provider("azure")

        assert result is not None  # redirect to auth URL

    @pytest.mark.asyncio
    async def test_exception_handled(self) -> None:
        state = _StubLoginState()
        state._oauth_service.provider_supported.side_effect = RuntimeError("boom")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            result = await state.login_with_provider("azure")

        assert state.is_loading is False
        assert result is None


class TestHandleOAuthCallback:
    @pytest.mark.asyncio
    async def test_error_param(self) -> None:
        state = _StubLoginState()
        state.router.url.query_parameters = {"error": "access_denied"}

        chunks = [c async for c in state.handle_oauth_callback("azure")]

        assert state.error_message == "access_denied"
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_missing_code(self) -> None:
        state = _StubLoginState()
        state.router.url.query_parameters = {"state": "abc"}

        chunks = [c async for c in state.handle_oauth_callback("azure")]

        assert len(chunks) >= 1  # error toast

    @pytest.mark.asyncio
    async def test_state_not_issued_by_this_browser_is_rejected(self) -> None:
        """A state this browser never stored must not complete a login.

        Regression guard for login CSRF: an attacker who replays their own
        (code, state) pair into a victim's browser would otherwise sign the
        victim into the attacker's account.
        """
        state = _StubLoginState()
        state.oauth_state = ""
        state.router.url.query_parameters = {
            "code": "attacker-code",
            "state": "attacker-state",
        }

        with patch(f"{_PATCH}.oauth_state_repo") as mock_o_repo:
            mock_o_repo.find_valid_by_state_and_provider = AsyncMock()
            chunks = [c async for c in state.handle_oauth_callback("azure")]

        assert state.user is None
        assert len(chunks) >= 1  # error toast
        mock_o_repo.find_valid_by_state_and_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_state_mismatch_is_rejected(self) -> None:
        """A state that does not match the stored one is refused."""
        state = _StubLoginState()
        state.oauth_state = "state-we-issued"
        state.router.url.query_parameters = {
            "code": "auth-code",
            "state": "some-other-state",
        }

        with patch(f"{_PATCH}.oauth_state_repo") as mock_o_repo:
            mock_o_repo.find_valid_by_state_and_provider = AsyncMock()
            [c async for c in state.handle_oauth_callback("azure")]

        assert state.user is None
        # the single-use state is cleared even on a failed attempt
        assert state.oauth_state == ""
        mock_o_repo.find_valid_by_state_and_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubLoginState()
        state.oauth_state = "state123"
        state.router.url.query_parameters = {
            "code": "auth-code",
            "state": "state123",
        }
        entity = _user_entity(1, "alice")
        oauth_state_obj = MagicMock(code_verifier="cv", session_id="test-token")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_s_repo,
            patch(f"{_PATCH}.oauth_state_repo") as mock_o_repo,
            patch(f"{_PATCH}.user_repo") as mock_u_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_o_repo.delete_expired = AsyncMock()
            mock_o_repo.find_valid_by_state_and_provider = AsyncMock(
                return_value=oauth_state_obj
            )
            mock_o_repo.delete = AsyncMock()
            mock_s_repo.save = AsyncMock()

            state._oauth_service.exchange_code_for_token.return_value = "token"
            state._oauth_service.get_user_info.return_value = {"email": "a@b.com"}
            mock_u_repo.get_or_create_oauth_user = AsyncMock(return_value=entity)

            [c async for c in state.handle_oauth_callback("azure")]

        assert state.is_loading is False
        assert state.user is not None
        # the browser-bound state is single-use
        assert state.oauth_state == ""


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout(self) -> None:
        state = _StubLoginState()
        state.auth_token = "token"
        state.user_id = 1

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            result = await state.logout()

        assert state.auth_token == ""
        assert result is not None  # redirect


class TestRedir:
    @pytest.mark.asyncio
    async def test_not_hydrated(self) -> None:
        state = _StubLoginState()
        state.is_hydrated = False
        result = await state.redir()
        # Returns event to call redir again
        assert result is not None

    @pytest.mark.asyncio
    async def test_not_authenticated_redirects_to_login(self) -> None:
        state = _StubLoginState()
        state.router.url.path = "/dashboard"
        # Not authenticated
        state.auth_token = ""
        state.user_id = 0

        # Make is_authenticated an awaitable returning False
        async def _not_auth():
            return False

        state.is_authenticated = _not_auth()

        result = await state.redir()

        assert state.redirect_to == "/dashboard"
        assert result is not None  # redirect to login

    @pytest.mark.asyncio
    async def test_not_authenticated_under_prefix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_public_path_prefix(monkeypatch, "/knai")

        async def _not_auth():
            return False

        at_login = _StubLoginState()
        at_login.router.url.path = "/knai/login"
        at_login.is_authenticated = _not_auth()
        assert await at_login.redir() is None

        elsewhere = _StubLoginState()
        elsewhere.router.url.path = "/knai/dashboard"
        elsewhere.is_authenticated = _not_auth()
        assert await elsewhere.redir() is not None
        assert elsewhere.redirect_to == "/dashboard"

    @pytest.mark.asyncio
    async def test_not_authenticated_at_login_route(self) -> None:
        state = _StubLoginState()
        state.router.url.path = "/login"

        async def _not_auth():
            return False

        state.is_authenticated = _not_auth()
        result = await state.redir()
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticated_with_redirect_to(self) -> None:
        state = _StubLoginState()
        state.redirect_to = "/dashboard"
        state.router.url.path = "/login"

        async def _auth():
            return True

        state.is_authenticated = _auth()
        result = await state.redir()
        assert state.redirect_to == ""
        assert result is not None

    @pytest.mark.asyncio
    async def test_authenticated_at_login_route(self) -> None:
        state = _StubLoginState()
        state.redirect_to = ""
        state.router.url.path = "/login"

        async def _auth():
            return True

        state.is_authenticated = _auth()
        result = await state.redir()
        assert result is not None  # redirect to homepage

    @pytest.mark.asyncio
    async def test_authenticated_at_oauth_callback(self) -> None:
        state = _StubLoginState()
        state.redirect_to = ""
        state.router.url.path = "/oauth/azure/callback"

        async def _auth():
            return True

        state.is_authenticated = _auth()
        result = await state.redir()
        assert result is not None  # redirect to homepage

    @pytest.mark.asyncio
    async def test_authenticated_at_regular_page(self) -> None:
        state = _StubLoginState()
        state.redirect_to = ""
        state.router.url.path = "/dashboard"

        async def _auth():
            return True

        state.is_authenticated = _auth()
        result = await state.redir()
        assert result is None


class TestCookieBackfill:
    """Sessions created before the cookie existed must keep working."""

    def test_valid_result_backfills_the_cookie_mirror(self) -> None:
        # The state a user logged in at deploy time arrives with: a token in
        # local storage and no cookie. Without the backfill they keep a working
        # socket but get 401s from every REST route and a 302 from the page
        # guard, because those transports can only read the cookie.
        state = _StubUserSession()
        state.auth_token = "pre-existing-token"
        state.session_cookie = ""

        state._cache_session(
            SessionValidationResult(
                SessionStatus.VALID,
                user=_user(7, "bob"),
                expires_at=datetime.now(UTC) + timedelta(minutes=25),
            )
        )

        assert state.session_cookie == "pre-existing-token"

    def test_existing_cookie_is_not_overwritten(self) -> None:
        state = _StubUserSession()
        state.auth_token = "stale-local-storage"
        state.session_cookie = "current-cookie"

        state._cache_session(
            SessionValidationResult(
                SessionStatus.VALID,
                user=_user(7, "bob"),
                expires_at=datetime.now(UTC) + timedelta(minutes=25),
            )
        )

        assert state.session_cookie == "current-cookie"

# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for UserSession and LoginState.

Covers session management, authentication checks, login flows,
OAuth callback handling, redirect logic, and error paths.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_user.authentication.backend.models import User
from appkit_user.authentication.states import LoginState, UserSession

_PATCH = "appkit_user.authentication.states"

# Access computed-var descriptors via __dict__.
_US_CV = UserSession.__dict__
_LS_CV = LoginState.__dict__


def _unwrap(cls: type, name: str):
    """Get the raw function from an EventHandler in __dict__."""
    entry = cls.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _user(
    user_id: int = 1,
    name: str = "testuser",
    email: str = "test@example.com",
    is_active: bool = True,
    is_verified: bool = True,
) -> User:
    return User(
        user_id=user_id,
        name=name,
        email=email,
        is_active=is_active,
        is_verified=is_verified,
    )


def _user_entity(
    user_id: int = 1,
    name: str = "testuser",
    email: str = "test@example.com",
) -> MagicMock:
    entity = MagicMock()
    entity.id = user_id
    entity.to_dict.return_value = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_active": True,
        "is_verified": True,
    }
    return entity


# ============================================================================
# UserSession stub
# ============================================================================


class _StubUserSession:
    """Plain stub for UserSession."""

    def __init__(self) -> None:
        self.auth_token: str = ""
        self.user_id: int = 0
        self.user: User | None = None

    _execute_db_operation = _unwrap(UserSession, "_execute_db_operation")
    _find_valid_session = _unwrap(UserSession, "_find_valid_session")
    _create_session = _unwrap(UserSession, "_create_session")
    terminate_session = _unwrap(UserSession, "terminate_session")
    prolong_session = _unwrap(UserSession, "prolong_session")

    def reset(self) -> None:
        self.auth_token = ""
        self.user_id = 0
        self.user = None


# ============================================================================
# LoginState stub
# ============================================================================


class _StubLoginState:
    """Plain stub for LoginState."""

    # Class-level attrs accessed by the real methods
    _LOGIN_ERROR_MESSAGES: dict[str, str] = {
        "invalid_credentials": "Ungültiger Benutzername oder Passwort.",
        "inactive": (
            "Ihr Konto wurde deaktiviert. Bitte wenden Sie sich an einen Administrator."
        ),
        "not_verified": (
            "Ihr Konto wurde noch nicht verifiziert. "
            "Bitte wenden Sie sich an einen Administrator."
        ),
    }

    def __init__(self) -> None:
        self.auth_token: str = ""
        self.user_id: int = 0
        self.user: User | None = None
        self.redirect_to: str = ""
        self.homepage: str = "/"
        self.login_route: str = "/login"
        self.logout_route: str = "/login"
        self.is_loading: bool = False
        self.error_message: str = ""
        self.is_hydrated: bool = True
        self._last_auth_check: datetime | None = None
        self._oauth_service = MagicMock()

        # Mock router for OAuth tests
        self.router = SimpleNamespace(
            url=SimpleNamespace(
                path="/",
                query_parameters={},
            ),
            session=SimpleNamespace(client_token="test-token"),
        )

    # Bind from both parent and child __dict__
    _execute_db_operation = _unwrap(UserSession, "_execute_db_operation")
    _find_valid_session = _unwrap(UserSession, "_find_valid_session")
    _create_session = _unwrap(UserSession, "_create_session")
    terminate_session = _unwrap(UserSession, "terminate_session")
    prolong_session = _unwrap(UserSession, "prolong_session")
    _prepare_login = _unwrap(LoginState, "_prepare_login")
    login_with_password = _unwrap(LoginState, "login_with_password")
    login_with_provider = _unwrap(LoginState, "login_with_provider")
    _store_oauth_state = _unwrap(LoginState, "_store_oauth_state")
    handle_oauth_callback = _unwrap(LoginState, "handle_oauth_callback")
    _exchange_oauth_and_get_user = _unwrap(LoginState, "_exchange_oauth_and_get_user")
    logout = _unwrap(LoginState, "logout")
    redir = _unwrap(LoginState, "redir")
    check_auth = _unwrap(LoginState, "check_auth")
    _should_skip_auth_check = _unwrap(LoginState, "_should_skip_auth_check")
    _is_oauth_callback_path = _unwrap(LoginState, "_is_oauth_callback_path")

    async def get_state(self, cls: type) -> MagicMock:
        return MagicMock(user_id=0, user=None)

    def reset(self) -> None:
        self.auth_token = ""
        self.user_id = 0
        self.user = None


# ============================================================================
# UserSession tests
# ============================================================================


class TestSessionCreation:
    @pytest.mark.asyncio
    async def test_create_session_sets_token_and_user(self) -> None:
        state = _StubUserSession()
        entity = _user_entity(42, "alice")

        mock_session = AsyncMock()
        with patch(f"{_PATCH}.session_repo") as mock_repo:
            mock_repo.save = AsyncMock()
            await state._create_session(mock_session, entity)

        assert state.auth_token != ""
        assert len(state.auth_token) == 64
        assert state.user_id == 42
        assert state.user is not None
        assert state.user.name == "alice"


class TestFindValidSession:
    @pytest.mark.asyncio
    async def test_by_user_and_token(self) -> None:
        state = _StubUserSession()
        state.user_id = 1
        state.auth_token = "token-abc"

        mock_db = AsyncMock()
        with patch(f"{_PATCH}.session_repo") as mock_repo:
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value="session-obj"
            )
            result = await state._find_valid_session(mock_db)

        assert result == "session-obj"

    @pytest.mark.asyncio
    async def test_fallback_to_token_only(self) -> None:
        state = _StubUserSession()
        state.user_id = 0
        state.auth_token = "token-abc"

        mock_db = AsyncMock()
        with patch(f"{_PATCH}.session_repo") as mock_repo:
            mock_repo.find_by_session_id = AsyncMock(return_value="session-obj")
            result = await state._find_valid_session(mock_db)

        assert result == "session-obj"

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        state = _StubUserSession()
        state.user_id = 0
        state.auth_token = ""

        mock_db = AsyncMock()
        result = await state._find_valid_session(mock_db)
        assert result is None


class TestExecuteDbOperation:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubUserSession()

        with patch(f"{_PATCH}.get_asyncdb_session") as mock_session:
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await state._execute_db_operation(AsyncMock(return_value="ok"))

        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retries_on_error(self) -> None:
        state = _StubUserSession()
        state.user_id = 1

        call_count = 0

        async def flaky_op(_db):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("SSL closed")
            return "recovered"

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.asyncio.sleep", new_callable=AsyncMock),
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await state._execute_db_operation(flaky_op)

        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_all_retries(self) -> None:
        state = _StubUserSession()
        state.user_id = 1

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.asyncio.sleep", new_callable=AsyncMock),
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="permanent"):
                await state._execute_db_operation(
                    AsyncMock(side_effect=RuntimeError("permanent"))
                )


class TestTerminateSession:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubUserSession()
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

            await state.terminate_session()

        assert state.auth_token == ""
        assert state.user_id == 0

    @pytest.mark.asyncio
    async def test_error_still_resets(self) -> None:
        state = _StubUserSession()
        state.auth_token = "token"
        state.user_id = 1

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.asyncio.sleep", new_callable=AsyncMock),
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.delete_by_user_and_session_id = AsyncMock(
                side_effect=RuntimeError("fail")
            )

            await state.terminate_session()

        # State should still be reset
        assert state.auth_token == ""
        assert state.user_id == 0


class TestProlongSession:
    @pytest.mark.asyncio
    async def test_skip_when_not_authenticated(self) -> None:
        state = _StubUserSession()
        state.user_id = 0
        state.auth_token = ""

        # Should return early without DB call
        await state.prolong_session()

    @pytest.mark.asyncio
    async def test_prolongs_valid_session(self) -> None:
        state = _StubUserSession()
        state.user_id = 1
        state.auth_token = "token"

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = False

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )

            await state.prolong_session()


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


class TestShouldSkipAuthCheck:
    def test_none_last_check(self) -> None:
        state = _StubLoginState()
        state._last_auth_check = None
        assert state._should_skip_auth_check() is False

    def test_recent_check_skips(self) -> None:
        state = _StubLoginState()
        state._last_auth_check = datetime.now(UTC) - timedelta(seconds=1)
        assert state._should_skip_auth_check() is True

    def test_old_check_does_not_skip(self) -> None:
        state = _StubLoginState()
        state._last_auth_check = datetime.now(UTC) - timedelta(hours=1)
        assert state._should_skip_auth_check() is False


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
        assert "db crash" in state.error_message


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
    async def test_success(self) -> None:
        state = _StubLoginState()
        state.router.url.query_parameters = {
            "code": "auth-code",
            "state": "state123",
        }
        entity = _user_entity(1, "alice")
        oauth_state_obj = MagicMock(code_verifier="cv")

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


# ============================================================================
# Supplementary tests for uncovered code paths
# ============================================================================


class TestAuthenticatedUserCV:
    @pytest.mark.asyncio
    async def test_valid_session(self) -> None:
        """authenticated_user returns user when session is valid."""
        state = _StubUserSession()
        state.auth_token = "token"
        state.user_id = 1

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = False
        mock_user_session.user = _user_entity(1, "alice")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )

            result = await _US_CV["authenticated_user"].fget(state)

        assert result is not None
        assert result.name == "alice"
        assert state.user_id == 1

    @pytest.mark.asyncio
    async def test_expired_session(self) -> None:
        """authenticated_user returns None when session expired."""
        state = _StubUserSession()
        state.auth_token = "token"
        state.user_id = 1

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = True

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )

            result = await _US_CV["authenticated_user"].fget(state)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_session(self) -> None:
        """authenticated_user returns None when no session found."""
        state = _StubUserSession()
        state.auth_token = ""
        state.user_id = 0

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_session_id = AsyncMock(return_value=None)

            result = await _US_CV["authenticated_user"].fget(state)

        assert result is None

    @pytest.mark.asyncio
    async def test_db_exception_returns_none(self) -> None:
        """authenticated_user returns None on DB exception."""
        state = _StubUserSession()
        state.auth_token = "token"
        state.user_id = 1

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(
                f"{_PATCH}.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                side_effect=RuntimeError("db down")
            )

            result = await _US_CV["authenticated_user"].fget(state)

        assert result is None

    @pytest.mark.asyncio
    async def test_session_without_user(self) -> None:
        """authenticated_user returns None when session.user is None."""
        state = _StubUserSession()
        state.auth_token = "token"
        state.user_id = 1

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = False
        mock_user_session.user = None

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )

            result = await _US_CV["authenticated_user"].fget(state)

        assert result is None


class TestIsAuthenticatedCV:
    @pytest.mark.asyncio
    async def test_true_when_authenticated(self) -> None:
        """is_authenticated returns True when user found."""
        state = _StubUserSession()

        async def _get_user():
            return _user_entity(1, "alice")

        state.authenticated_user = _get_user()

        result = await _US_CV["is_authenticated"].fget(state)
        assert result is True

    @pytest.mark.asyncio
    async def test_false_when_not_authenticated(self) -> None:
        """is_authenticated returns False when no valid session."""
        state = _StubUserSession()

        async def _get_none():
            return None

        state.authenticated_user = _get_none()

        result = await _US_CV["is_authenticated"].fget(state)
        assert result is False


class TestCheckAuth:
    @pytest.mark.asyncio
    async def test_valid_user_syncs_state(self) -> None:
        """check_auth syncs user state when valid session found."""
        state = _StubLoginState()
        state._last_auth_check = None
        state.auth_token = "token"
        state.user_id = 1

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = False
        mock_user_session.user = _user_entity(42, "bob")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )

            result = await state.check_auth()

        assert result is None
        assert state.user is not None
        assert state.user.user_id == 42
        assert state.user_id == 42

    @pytest.mark.asyncio
    async def test_skipped_when_recent(self) -> None:
        """check_auth skips when last check was recent."""
        state = _StubLoginState()
        state._last_auth_check = datetime.now(UTC) - timedelta(seconds=1)

        result = await state.check_auth()
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_session_terminates(self) -> None:
        """check_auth terminates session when expired."""
        state = _StubLoginState()
        state._last_auth_check = None
        state.auth_token = "token"
        state.user_id = 1
        state.is_hydrated = True
        state.router.url.path = "/dashboard"

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = True

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            await state.check_auth()

        # Should have called terminate_session + redir
        assert state.auth_token == ""
        assert state._last_auth_check is None

    @pytest.mark.asyncio
    async def test_no_session_terminates(self) -> None:
        """check_auth terminates session when no session found."""
        state = _StubLoginState()
        state._last_auth_check = None
        state.auth_token = "token"
        state.user_id = 1
        state.is_hydrated = True
        state.router.url.path = "/dashboard"

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(return_value=None)
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            await state.check_auth()

        assert state.auth_token == ""

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        """check_auth returns None on exception."""
        state = _StubLoginState()
        state._last_auth_check = None
        state.auth_token = "token"
        state.user_id = 1

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(
                f"{_PATCH}.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                side_effect=RuntimeError("db crash")
            )

            result = await state.check_auth()

        assert result is None

    @pytest.mark.asyncio
    async def test_session_without_user(self) -> None:
        """check_auth terminates when session has no user."""
        state = _StubLoginState()
        state._last_auth_check = None
        state.auth_token = "token"
        state.user_id = 1
        state.is_hydrated = True
        state.router.url.path = "/dashboard"

        mock_user_session = MagicMock()
        mock_user_session.is_expired.return_value = False
        mock_user_session.user = None

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
            patch(f"{_PATCH}.session_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=mock_user_session
            )
            mock_repo.delete_by_user_and_session_id = AsyncMock()

            await state.check_auth()

        assert state.auth_token == ""

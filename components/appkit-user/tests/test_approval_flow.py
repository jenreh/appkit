# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for the admin approval gate of new OAuth users.

Covers the post-login redirect to the welcome page, the welcome page guard,
the handler decorators, the shared pending helpers, the admin notification
and the configuration defaults.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _auth_state_stubs import _PATCH, _StubLoginState, _user, _user_entity
from reflex_base.event import EventSpec

from appkit_user.authentication import decorators
from appkit_user.authentication.backend.database import OAuthUserResult
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.backend.services import approval_notification
from appkit_user.authentication.session_validation import (
    SessionStatus,
    SessionValidationResult,
    is_pending_approval,
    is_route_allowed_for_pending,
)
from appkit_user.configuration import AuthenticationConfiguration

_NOTIFY = "appkit_user.authentication.backend.services.approval_notification"


def _redirect_path(spec: Any) -> str | None:
    """Target path of an ``rx.redirect`` spec, or None for anything else."""
    if not isinstance(spec, EventSpec) or spec.handler.fn.__qualname__ != "_redirect":
        return None
    args = {str(name): value for name, value in spec.args}
    return args["path"]._var_value


async def _authenticated(value: bool = True) -> bool:
    return value


# ============================================================================
# Shared helpers
# ============================================================================


class TestPendingHelpers:
    def test_unverified_user_is_pending(self) -> None:
        assert is_pending_approval(_user(is_verified=False)) is True

    def test_verified_user_is_not_pending(self) -> None:
        assert is_pending_approval(_user(is_verified=True)) is False

    def test_anonymous_is_not_pending(self) -> None:
        assert is_pending_approval(None) is False

    @pytest.mark.parametrize(
        ("path", "allowed"),
        [
            ("/welcome", True),
            ("/welcome/", True),
            ("/welcome?x=1", True),
            ("/login", True),
            ("/oauth/github/callback", True),
            ("/", False),
            ("/admin/users", False),
            ("/welcome-other", False),
        ],
    )
    def test_routes_allowed_for_pending(self, path: str, allowed: bool) -> None:
        assert is_route_allowed_for_pending(path) is allowed


class TestConfigurationDefaults:
    def test_approval_on_by_default(self) -> None:
        config = AuthenticationConfiguration(server_url="http://x", server_port=0)

        assert config.require_admin_approval is True
        assert config.welcome_route == "/welcome"
        assert config.user_admin_route == "/admin/users"


# ============================================================================
# OAuth callback
# ============================================================================


async def _run_callback(
    entity: MagicMock, created: bool
) -> tuple[_StubLoginState, list[Any], MagicMock]:
    state = _StubLoginState()
    state.oauth_state = "state123"
    state.router.url.query_parameters = {"code": "auth-code", "state": "state123"}
    oauth_state_obj = MagicMock(code_verifier="cv", session_id="test-token")

    with (
        patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
        patch(f"{_PATCH}.session_repo") as mock_s_repo,
        patch(f"{_PATCH}.oauth_state_repo") as mock_o_repo,
        patch(f"{_PATCH}.user_repo") as mock_u_repo,
        patch(f"{_PATCH}.schedule_pending_user_notification") as mock_notify,
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
        mock_u_repo.resolve_oauth_user = AsyncMock(
            return_value=OAuthUserResult(user=entity, created=created)
        )

        events = [e async for e in state.handle_oauth_callback("github")]

    return state, events, mock_notify


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_new_pending_user_notifies_admins(self) -> None:
        state, _, notify = await _run_callback(
            _user_entity(5, "neu", is_verified=False), created=True
        )

        assert state.user is not None
        assert state.user.is_verified is False
        notify.assert_called_once()
        assert notify.call_args.args[0].user_id == 5

    @pytest.mark.asyncio
    async def test_returning_pending_user_does_not_notify_again(self) -> None:
        _, _, notify = await _run_callback(
            _user_entity(5, "neu", is_verified=False), created=False
        )

        notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_user_without_approval_gate_does_not_notify(self) -> None:
        _, _, notify = await _run_callback(_user_entity(5, "neu"), created=True)

        notify.assert_not_called()


# ============================================================================
# redir
# ============================================================================


class TestRedirPending:
    @pytest.mark.asyncio
    async def test_pending_user_goes_to_welcome_and_drops_redirect_to(self) -> None:
        state = _StubLoginState()
        state.user = _user(is_verified=False)
        state.redirect_to = "/admin/users"
        state.router.url.path = "/oauth/github/callback"
        state.is_authenticated = _authenticated()

        result = await state.redir()

        assert _redirect_path(result) == "/welcome"
        assert state.redirect_to == ""

    @pytest.mark.asyncio
    async def test_pending_user_on_welcome_page_stays(self) -> None:
        state = _StubLoginState()
        state.user = _user(is_verified=False)
        state.router.url.path = "/welcome"
        state.is_authenticated = _authenticated()

        assert await state.redir() is None

    @pytest.mark.asyncio
    async def test_approved_user_follows_redirect_to(self) -> None:
        state = _StubLoginState()
        state.user = _user(is_verified=True)
        state.redirect_to = "/admin/users"
        state.router.url.path = "/login"
        state.is_authenticated = _authenticated()

        assert _redirect_path(await state.redir()) == "/admin/users"


# ============================================================================
# Welcome page guard
# ============================================================================


def _validation(user: User | None) -> SessionValidationResult:
    if user is None:
        return SessionValidationResult(SessionStatus.ABSENT)
    return SessionValidationResult(
        SessionStatus.VALID,
        user=user,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


class TestLeaveWelcomeIfApproved:
    @staticmethod
    async def _run(user: User | None) -> tuple[_StubLoginState, Any]:
        state = _StubLoginState()
        state.session_cookie = "tok"
        validator = MagicMock()
        validator.validate = AsyncMock(return_value=_validation(user))
        with patch(f"{_PATCH}._SESSION_VALIDATOR", validator):
            result = await state.leave_welcome_if_approved()
        return state, result

    @pytest.mark.asyncio
    async def test_anonymous_goes_to_login(self) -> None:
        _, result = await self._run(None)

        assert _redirect_path(result) == "/login"

    @pytest.mark.asyncio
    async def test_pending_user_stays(self) -> None:
        state, result = await self._run(_user(is_verified=False))

        assert result is None
        assert state.user is not None

    @pytest.mark.asyncio
    async def test_approved_user_goes_home(self) -> None:
        state, result = await self._run(_user(is_verified=True))

        assert _redirect_path(result) == "/"
        assert state.user is not None
        assert state.user.is_verified is True


# ============================================================================
# Handler decorators
# ============================================================================


class _LoginStateStub:
    """Awaitable vars are built on access, so none is left un-awaited."""

    def __init__(self, user: User | None) -> None:
        self.user = user
        self.redir = AsyncMock(return_value=None)

    @property
    def is_authenticated(self) -> Any:
        return _authenticated(self.user is not None)

    @property
    def authenticated_user(self) -> Any:
        async def _user_var() -> User | None:
            return self.user

        return _user_var()


class _DecoratedState:
    """Minimal state the decorators can resolve ``LoginState`` from."""

    def __init__(self, user: User | None) -> None:
        self.login_state = _LoginStateStub(user)
        self.ran = False

    async def get_state(self, cls: type) -> _LoginStateStub:
        return self.login_state

    @decorators.is_authenticated
    async def handler(self) -> str:
        self.ran = True
        return "done"

    @decorators.is_authenticated
    async def gen_handler(self) -> Any:
        self.ran = True
        yield "done"

    @decorators.requires_admin
    async def admin_handler(self) -> str:
        self.ran = True
        return "done"


class TestDecorators:
    @pytest.mark.asyncio
    async def test_pending_user_is_sent_to_welcome(self) -> None:
        state = _DecoratedState(_user(is_verified=False))

        result = await state.handler()

        assert state.ran is False
        assert _redirect_path(result) == "/welcome"

    @pytest.mark.asyncio
    async def test_pending_user_generator_handler_is_blocked(self) -> None:
        state = _DecoratedState(_user(is_verified=False))

        events = [e async for e in state.gen_handler()]

        assert state.ran is False
        assert _redirect_path(events[0]) == "/welcome"

    @pytest.mark.asyncio
    async def test_anonymous_is_blocked_even_without_redirect(self) -> None:
        state = _DecoratedState(None)

        result = await state.handler()

        assert state.ran is False
        assert result is None

    @pytest.mark.asyncio
    async def test_approved_user_runs_the_handler(self) -> None:
        state = _DecoratedState(_user(is_verified=True))

        assert await state.handler() == "done"
        assert state.ran is True

    @pytest.mark.asyncio
    async def test_pending_admin_is_denied_admin_action(self) -> None:
        pending_admin = User(user_id=3, is_admin=True, is_verified=False)
        state = _DecoratedState(pending_admin)

        await state.admin_handler()

        assert state.ran is False

    @pytest.mark.asyncio
    async def test_approved_admin_runs_admin_action(self) -> None:
        admin = User(user_id=3, is_admin=True, is_verified=True)
        state = _DecoratedState(admin)

        assert await state.admin_handler() == "done"


# ============================================================================
# Admin notification
# ============================================================================


def _admin(email: str | None, name: str | None = "Admin") -> MagicMock:
    admin = MagicMock()
    admin.email = email
    admin.name = name
    return admin


class TestNotifyAdmins:
    _PENDING = User(user_id=9, name="Neu", email="neu@example.com")

    @pytest.mark.asyncio
    async def test_without_email_provider_sends_nothing(self) -> None:
        with patch(f"{_NOTIFY}.get_email_service", return_value=None):
            sent = await approval_notification.notify_admins_of_pending_user(
                self._PENDING
            )

        assert sent == 0

    @pytest.mark.asyncio
    async def test_emails_every_admin_with_an_address(self) -> None:
        service = MagicMock()
        service.send_new_user_pending_email = AsyncMock(side_effect=[True, False])
        admins = [_admin("a@example.com"), _admin(None), _admin("b@example.com", None)]

        with (
            patch(f"{_NOTIFY}.get_email_service", return_value=service),
            patch(f"{_NOTIFY}.get_asyncdb_session") as mock_session,
            patch(f"{_NOTIFY}.user_repo") as mock_repo,
            patch(f"{_NOTIFY}._admin_url", return_value="http://x/admin/users"),
        ):
            mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_active_admins = AsyncMock(return_value=admins)

            sent = await approval_notification.notify_admins_of_pending_user(
                self._PENDING
            )

        assert sent == 1
        calls = service.send_new_user_pending_email.await_args_list
        assert [c.kwargs["to_email"] for c in calls] == [
            "a@example.com",
            "b@example.com",
        ]
        # An admin without a name is greeted by address.
        assert calls[1].kwargs["admin_name"] == "b@example.com"
        assert calls[0].kwargs["user_email"] == "neu@example.com"
        assert calls[0].kwargs["admin_url"] == "http://x/admin/users"

    @pytest.mark.asyncio
    async def test_database_failure_is_swallowed(self) -> None:
        with (
            patch(f"{_NOTIFY}.get_email_service", return_value=MagicMock()),
            patch(f"{_NOTIFY}.get_asyncdb_session", side_effect=RuntimeError("db")),
        ):
            sent = await approval_notification.notify_admins_of_pending_user(
                self._PENDING
            )

        assert sent == 0

    def test_admin_url_uses_public_base_url(self) -> None:
        config = AuthenticationConfiguration(
            server_url="https://app.example.com", server_port=443
        )
        registry = MagicMock()
        registry.get.return_value = config
        with patch(f"{_NOTIFY}.service_registry", return_value=registry):
            assert (
                approval_notification._admin_url()
                == "https://app.example.com/admin/users"
            )

    @pytest.mark.asyncio
    async def test_schedule_runs_in_background_and_is_released(self) -> None:
        notify = AsyncMock(return_value=1)
        with patch(f"{_NOTIFY}.notify_admins_of_pending_user", notify):
            approval_notification.schedule_pending_user_notification(self._PENDING)
            assert len(approval_notification._BACKGROUND_TASKS) == 1
            await asyncio.gather(*approval_notification._BACKGROUND_TASKS)
            await asyncio.sleep(0)

        notify.assert_awaited_once_with(self._PENDING)
        assert not approval_notification._BACKGROUND_TASKS

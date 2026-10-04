# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for the SessionFilter WebSocket middleware.

Covers the allow/deny decision for every case the filter can see: internal
bootstrap events, public routes, the cached-expiry fast path, database-backed
denial, the fail-closed error paths, the kill switch and installation.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from reflex.state import State, StateUpdate, UpdateVarsInternalState

from appkit_commons.testing import set_public_path_prefix
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.session_filter import (
    SessionFilter,
    install_session_filter,
)
from appkit_user.authentication.session_validation import (
    SessionStatus,
    SessionValidationResult,
    SessionValidator,
    _auth_config,
)
from appkit_user.authentication.states import (
    LoginState,
    UserSession,
    _session_monitor_interval,
)

_VALIDATION_PATCH = "appkit_user.authentication.session_validation"

# Derived from the classes exactly the way the implementation derives them.
# Hardcoding the strings would not catch a Reflex rename — which is precisely
# the regression that bricks the app.
HYDRATE = f"{State.get_full_name()}.hydrate"
SET_IS_HYDRATED = f"{State.get_full_name()}.set_is_hydrated"
UPDATE_VARS_INTERNAL = f"{UpdateVarsInternalState.get_full_name()}.update_vars_internal"

# The exact short-circuit payload. A short-circuit emits no delta, so a session
# proven dead has its browser-side credentials dropped by explicit events before
# the redirect; then set_is_hydrated unblocks the client.
DENIAL_EVENT_NAMES = [
    "_remove_local_storage",
    "_remove_cookie",
    "_redirect",
    SET_IS_HYDRATED,
]
# On SessionStatus.ERROR the database is what failed, so the credential was
# never shown to be bad and must survive the denial.
ERROR_DENIAL_EVENT_NAMES = ["_redirect", SET_IS_HYDRATED]

PROTECTED_PATH = "/dashboard"


def _unwrap(cls: type, name: str) -> Any:
    """Get the raw function from an EventHandler in __dict__."""
    entry = cls.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _user(user_id: int = 7) -> User:
    return User(
        user_id=user_id,
        name="testuser",
        email="test@example.com",
        is_active=True,
        is_verified=True,
    )


# ============================================================================
# Stubs
# ============================================================================


class _StubUserSession:
    """Plain stub for UserSession with the real cache helpers bound."""

    def __init__(
        self,
        session_cookie: str = "",
        auth_token: str = "",
        user_id: int = 0,
        expires_at: datetime | None = None,
    ) -> None:
        self.session_cookie = session_cookie
        self.auth_token = auth_token
        self.user_id = user_id
        self.user: User | None = None
        self._session_expires_at = expires_at
        self.terminate_session = AsyncMock()

    # Real implementations — the cache decision must not be re-invented here.
    _has_unexpired_cache = _unwrap(UserSession, "_has_unexpired_cache")
    _cache_session = _unwrap(UserSession, "_cache_session")
    _trust_session_until = _unwrap(UserSession, "_trust_session_until")


class _StubLoginState:
    """Plain stub for LoginState."""

    def __init__(self) -> None:
        self.redirect_to = ""


class _StubRootState:
    """Stub for the session root state handed to ``preprocess``."""

    def __init__(
        self,
        path: str = PROTECTED_PATH,
        user_session: _StubUserSession | None = None,
        login_state: _StubLoginState | None = None,
    ) -> None:
        self.router = SimpleNamespace(url=SimpleNamespace(path=path))
        self.user_session = user_session or _StubUserSession()
        self.login_state = login_state or _StubLoginState()
        self.get_state = AsyncMock(side_effect=self._resolve)

    async def _resolve(self, state_cls: type) -> Any:
        # LoginState first: it is a subclass of UserSession.
        if state_cls is LoginState:
            return self.login_state
        if state_cls is UserSession:
            return self.user_session
        raise AssertionError(f"unexpected get_state({state_cls!r})")


def _event(name: str = "some_state.some_handler") -> SimpleNamespace:
    return SimpleNamespace(name=name, router_data={})


def _validator(
    result: SessionValidationResult | None = None,
    exc: Exception | None = None,
) -> MagicMock:
    validator = MagicMock(spec=SessionValidator)
    validator.validate = AsyncMock(
        return_value=result or SessionValidationResult(SessionStatus.ABSENT),
        side_effect=exc,
    )
    return validator


async def _run(
    validator: MagicMock | SessionValidator,
    state: _StubRootState,
    event: SimpleNamespace,
) -> StateUpdate | None:
    """Drive the filter the way Reflex does — by keyword."""
    session_filter = SessionFilter(validator)  # type: ignore[arg-type]
    return await session_filter.preprocess(app=MagicMock(), state=state, event=event)  # type: ignore[arg-type]


def _assert_denied(
    update: StateUpdate | None, expected: list[str] | None = None
) -> None:
    assert update is not None, "filter must deny, not fall open"
    assert [e.name for e in update.events] == (expected or DENIAL_EVENT_NAMES)


@pytest.fixture
def filter_disabled() -> Iterator[None]:
    """Flip the real kill switch on the registered configuration."""
    config = _auth_config()
    config.session_filter_enabled = False
    try:
        yield
    finally:
        config.session_filter_enabled = True


# ============================================================================
# Bootstrap events (regression guard)
# ============================================================================


class TestBootstrapEvents:
    """Blocking these bricks the app: the session cookie only reaches the
    backend inside the hydrate event, and set_is_hydrated is what clears the
    client's loading cursor."""

    @pytest.mark.parametrize(
        "event_name", [HYDRATE, SET_IS_HYDRATED, UPDATE_VARS_INTERNAL]
    )
    @pytest.mark.asyncio
    async def test_passes_without_any_session(self, event_name: str) -> None:
        validator = _validator()
        state = _StubRootState(path=PROTECTED_PATH)

        result = await _run(validator, state, _event(event_name))

        assert result is None
        validator.validate.assert_not_awaited()
        state.get_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ordinary_event_on_same_path_is_denied(self) -> None:
        # Proves the pass above comes from the event name, not the setup.
        state = _StubRootState(path=PROTECTED_PATH)

        _assert_denied(await _run(_validator(), state, _event()))


# ============================================================================
# Public routes
# ============================================================================


class TestPublicRoutes:
    @pytest.mark.asyncio
    async def test_login_without_session_passes(self) -> None:
        validator = _validator()
        state = _StubRootState(path="/login")

        assert await _run(validator, state, _event()) is None
        validator.validate.assert_not_awaited()

    @pytest.mark.parametrize(
        "path", ["/oauth/github/callback", "/oauth/azure/callback"]
    )
    @pytest.mark.asyncio
    async def test_oauth_callbacks_pass_through_the_glob(self, path: str) -> None:
        validator = _validator()

        assert await _run(validator, _StubRootState(path=path), _event()) is None
        validator.validate.assert_not_awaited()


# ============================================================================
# Expiry cache
# ============================================================================


class TestExpiryCache:
    @pytest.mark.asyncio
    async def test_unexpired_cache_passes_without_consulting_validator(self) -> None:
        validator = _validator()
        session = _StubUserSession(
            session_cookie="tok-123",
            user_id=7,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        state = _StubRootState(user_session=session)

        assert await _run(validator, state, _event()) is None
        validator.validate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpired_cache_touches_no_database(self) -> None:
        # Same claim, asserted one layer deeper: a REAL validator plus mocked
        # persistence, so nothing can reach the session store behind our back.
        session = _StubUserSession(
            session_cookie="tok-123",
            user_id=7,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        state = _StubRootState(user_session=session)

        with (
            patch(f"{_VALIDATION_PATCH}.get_asyncdb_session") as mock_db,
            patch(f"{_VALIDATION_PATCH}.session_repo") as mock_repo,
        ):
            assert await _run(SessionValidator(), state, _event()) is None

        mock_db.assert_not_called()
        mock_repo.find_by_user_and_session_id.assert_not_called()
        mock_repo.find_by_session_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_expired_in_the_past_consults_validator(self) -> None:
        validator = _validator(
            SessionValidationResult(
                SessionStatus.VALID,
                user=_user(),
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        session = _StubUserSession(
            session_cookie="tok-123",
            user_id=7,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        result = await _run(validator, _StubRootState(user_session=session), _event())

        assert result is None
        validator.validate.assert_awaited_once_with(session_id="tok-123", user_id=7)

    @pytest.mark.asyncio
    async def test_valid_result_is_cached(self) -> None:
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        validator = _validator(
            SessionValidationResult(
                SessionStatus.VALID, user=_user(42), expires_at=expires_at
            )
        )
        session = _StubUserSession(session_cookie="tok-123")

        assert (
            await _run(validator, _StubRootState(user_session=session), _event())
            is None
        )
        # Trust is capped at the monitor interval rather than the session's own
        # expiry, so a revocation is noticed within that window.
        assert session._session_expires_at is not None
        assert session._session_expires_at < expires_at
        assert session._session_expires_at <= (
            datetime.now(UTC) + _session_monitor_interval()
        )
        assert session.user_id == 42
        assert session.user is not None


# ============================================================================
# Denial
# ============================================================================


class TestDenial:
    @pytest.mark.asyncio
    async def test_expired_session_redirects_and_remembers_path(self) -> None:
        validator = _validator(SessionValidationResult(SessionStatus.EXPIRED))
        session = _StubUserSession(session_cookie="tok-123", user_id=7)
        state = _StubRootState(path=PROTECTED_PATH, user_session=session)

        update = await _run(validator, state, _event())

        _assert_denied(update)
        assert state.login_state.redirect_to == PROTECTED_PATH
        session.terminate_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_absent_session_redirects(self) -> None:
        session = _StubUserSession(session_cookie="tok-123", user_id=7)
        state = _StubRootState(user_session=session)

        _assert_denied(
            await _run(
                _validator(SessionValidationResult(SessionStatus.ABSENT)),
                state,
                _event(),
            )
        )
        session.terminate_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_home_route_is_not_remembered(self) -> None:
        state = _StubRootState(path="/")

        _assert_denied(
            await _run(
                _validator(SessionValidationResult(SessionStatus.EXPIRED)),
                state,
                _event(),
            )
        )
        assert state.login_state.redirect_to == ""

    @pytest.mark.asyncio
    async def test_redirect_targets_the_login_page(self) -> None:
        update = await _run(_validator(), _StubRootState(), _event())

        assert update is not None
        redirect, hydrated = update.events[-2], update.events[-1]
        assert redirect.payload["path"] == "/login"
        assert hydrated.payload["value"] is True


# ============================================================================
# Fail-closed behaviour
# ============================================================================


class TestFailClosed:
    @pytest.mark.asyncio
    async def test_error_status_denies(self) -> None:
        session = _StubUserSession(
            session_cookie="tok-123",
            auth_token="tok-123",
            user_id=7,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        state = _StubRootState(user_session=session)

        _assert_denied(
            await _run(
                _validator(SessionValidationResult(SessionStatus.ERROR)),
                state,
                _event(),
            ),
            ERROR_DENIAL_EVENT_NAMES,
        )
        # The database is what just failed, so the session was never *shown* to
        # be invalid. Access is denied, but the credential survives on both
        # sides so a retry can succeed — otherwise one transient error logs
        # every active user out.
        session.terminate_session.assert_not_awaited()
        assert session.session_cookie == "tok-123"
        assert session.auth_token == "tok-123"
        assert session.user_id == 7

    @pytest.mark.asyncio
    async def test_validator_raising_denies(self) -> None:
        # The unexpected-error path cannot know the session is bad either, so
        # it denies without dropping the credential.
        _assert_denied(
            await _run(
                _validator(exc=RuntimeError("boom")), _StubRootState(), _event()
            ),
            ERROR_DENIAL_EVENT_NAMES,
        )

    @pytest.mark.asyncio
    async def test_unreadable_router_denies(self) -> None:
        state = _StubRootState()
        router = MagicMock()
        type(router).url = PropertyMock(side_effect=RuntimeError("no router"))
        state.router = router

        _assert_denied(
            await _run(_validator(), state, _event()), ERROR_DENIAL_EVENT_NAMES
        )

    @pytest.mark.asyncio
    async def test_failing_teardown_still_denies(self) -> None:
        session = _StubUserSession(session_cookie="tok-123", user_id=7)
        session.terminate_session = AsyncMock(side_effect=RuntimeError("db down"))

        _assert_denied(
            await _run(
                _validator(SessionValidationResult(SessionStatus.EXPIRED)),
                _StubRootState(user_session=session),
                _event(),
            )
        )


# ============================================================================
# Kill switch
# ============================================================================


class TestKillSwitch:
    @pytest.mark.usefixtures("filter_disabled")
    @pytest.mark.asyncio
    async def test_disabled_filter_passes_everything(self) -> None:
        validator = _validator()
        state = _StubRootState(path=PROTECTED_PATH)

        assert await _run(validator, state, _event()) is None
        validator.validate.assert_not_awaited()
        state.get_state.assert_not_awaited()


# ============================================================================
# Token resolution
# ============================================================================


class TestTokenResolution:
    @pytest.mark.asyncio
    async def test_falls_back_to_local_storage_token(self) -> None:
        # Sessions created before the cookie existed must keep working.
        validator = _validator()
        session = _StubUserSession(session_cookie="", auth_token="ls-token", user_id=3)

        await _run(validator, _StubRootState(user_session=session), _event())

        validator.validate.assert_awaited_once_with(session_id="ls-token", user_id=3)

    @pytest.mark.asyncio
    async def test_cookie_wins_over_local_storage(self) -> None:
        validator = _validator()
        session = _StubUserSession(
            session_cookie="cookie-token", auth_token="ls-token", user_id=3
        )

        await _run(validator, _StubRootState(user_session=session), _event())

        validator.validate.assert_awaited_once_with(
            session_id="cookie-token", user_id=3
        )

    @pytest.mark.asyncio
    async def test_empty_token_bypasses_the_cache(self) -> None:
        # A stale expiry cache with no token must not authorize anything.
        validator = _validator()
        session = _StubUserSession(
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

        _assert_denied(
            await _run(validator, _StubRootState(user_session=session), _event())
        )
        validator.validate.assert_awaited_once_with(session_id="", user_id=0)


# ============================================================================
# Installation
# ============================================================================


class TestInstall:
    def test_install_registers_a_session_filter(self) -> None:
        app = MagicMock()

        install_session_filter(app)

        app.add_middleware.assert_called_once()
        (middleware,) = app.add_middleware.call_args.args
        assert isinstance(middleware, SessionFilter)


class TestRedirectTargetSanitisation:
    """`redirect_to` feeds rx.redirect() after login; it must stay local."""

    @pytest.mark.asyncio
    async def test_off_site_attempted_path_is_not_remembered(self) -> None:
        # A victim following https://app.example.com//evil.com/pwn produces
        # this path; storing it would make the post-login redirect leave the
        # site entirely.
        state = _StubRootState(path="//evil.com/pwn")

        _assert_denied(await _run(_validator(), state, _event()))
        assert state.login_state.redirect_to == ""

    @pytest.mark.asyncio
    async def test_local_attempted_path_is_remembered(self) -> None:
        state = _StubRootState(path="/reports/42")

        _assert_denied(await _run(_validator(), state, _event()))
        assert state.login_state.redirect_to == "/reports/42"


class TestUnderPathPrefix:
    """With frontend_path set, router.url.path carries the app prefix."""

    @pytest.fixture(autouse=True)
    def _prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_public_path_prefix(monkeypatch, "/knai")

    @pytest.mark.asyncio
    async def test_prefixed_login_page_passes(self) -> None:
        state = _StubRootState(path="/knai/login")

        assert await _run(_validator(), state, _event()) is None

    @pytest.mark.asyncio
    async def test_remembered_path_has_no_prefix(self) -> None:
        validator = _validator(SessionValidationResult(SessionStatus.EXPIRED))
        session = _StubUserSession(session_cookie="tok-123", user_id=7)
        state = _StubRootState(path=f"/knai{PROTECTED_PATH}", user_session=session)

        _assert_denied(await _run(validator, state, _event()))
        # navigate() adds the basename again, so a prefixed target would
        # end up at /knai/knai/dashboard.
        assert state.login_state.redirect_to == PROTECTED_PATH

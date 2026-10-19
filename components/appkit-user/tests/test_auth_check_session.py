# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for authentication checks and session invalidation.

Covers the ``authenticated_user`` / ``is_authenticated`` computed vars, the
``check_auth`` guard against the shared SessionValidator, and logout against
a real Reflex state tree.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import reflex as rx
from _auth_state_stubs import (
    _PATCH,
    _US_CV,
    _VPATCH,
    _handler_names,
    _prime_is_authenticated,
    _session_row,
    _StubLoginState,
    _StubUserSession,
    _user_entity,
    _validating_db,
)

from appkit_user.authentication.states import LoginState, UserSession

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


@contextmanager
def _terminating_db() -> Iterator[MagicMock]:
    """Patch the DB layer ``terminate_session`` uses (the one in ``states``)."""
    with (
        patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
        patch(f"{_PATCH}.session_repo") as mock_repo,
    ):
        session = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_repo.delete_by_user_and_session_id = AsyncMock()
        yield mock_repo


def _denied_state() -> _StubLoginState:
    """A signed-in stub on a protected page with a stale expiry cache."""
    state = _StubLoginState()
    state.auth_token = "token"
    state.session_cookie = "token"
    state.user_id = 1
    state.is_hydrated = True
    state.router.url.path = "/dashboard"
    state._session_expires_at = None
    _prime_is_authenticated(state, False)
    return state


class TestCheckAuth:
    @pytest.mark.asyncio
    async def test_valid_user_syncs_state(self) -> None:
        """check_auth syncs user state when a valid session is found."""
        state = _StubLoginState()
        state.auth_token = "token"
        state.user_id = 1

        with _validating_db() as (_, mock_repo):
            mock_repo.find_by_user_and_session_id = AsyncMock(
                return_value=_session_row(user_entity=_user_entity(42, "bob"))
            )

            result = await state.check_auth()

        assert result is None
        assert state.user is not None
        assert state.user.user_id == 42
        assert state.user_id == 42
        # The validated expiry is cached so the next event skips the DB.
        assert state._has_unexpired_cache() is True

    @pytest.mark.asyncio
    async def test_token_only_session_uses_unscoped_lookup(self) -> None:
        """A token with no known owner must still resolve.

        A fresh tab restores ``auth_token`` from local storage before it knows
        ``user_id``; scoping that lookup to user 0 would match nothing and log
        the user out on every reload.
        """
        state = _StubLoginState()
        state.auth_token = "token"
        state.user_id = 0

        with _validating_db() as (_, mock_repo):
            mock_repo.find_by_session_id = AsyncMock(
                return_value=_session_row(user_entity=_user_entity(42, "bob"))
            )
            mock_repo.find_by_user_and_session_id = AsyncMock(return_value=None)

            result = await state.check_auth()

        assert result is None
        assert state.user_id == 42
        mock_repo.find_by_session_id.assert_awaited_once()
        mock_repo.find_by_user_and_session_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpired_cache_skips_the_database(self) -> None:
        """An unexpired cached expiry is authoritative — and costs no query.

        ``preprocess`` holds the exclusive per-session state lock while this
        runs, so a DB round trip on every event would serialize the whole
        session's event stream behind the database.
        """
        state = _StubLoginState()
        state.auth_token = "token"
        state.user_id = 1
        state._session_expires_at = datetime.now(UTC) + timedelta(minutes=5)

        with (
            _validating_db() as (validating_ctx, validating_repo),
            patch(f"{_PATCH}.get_asyncdb_session") as states_ctx,
        ):
            result = await state.check_auth()

        assert result is None
        validating_ctx.assert_not_called()
        validating_repo.find_by_user_and_session_id.assert_not_called()
        validating_repo.find_by_session_id.assert_not_called()
        states_ctx.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_session_terminates_and_redirects(self) -> None:
        state = _denied_state()

        with _validating_db() as (_, validating_repo), _terminating_db() as states_repo:
            validating_repo.find_by_user_and_session_id = AsyncMock(
                return_value=_session_row(expired=True)
            )

            result = await state.check_auth()

        assert any("redirect" in name for name in _handler_names(result))
        assert state.auth_token == ""
        assert state.session_cookie == ""
        assert state._session_expires_at is None
        # The row is really deleted, not just forgotten client-side.
        states_repo.delete_by_user_and_session_id.assert_awaited_once()
        # The attempted page is remembered so login can land back on it.
        assert state.redirect_to == "/dashboard"

    @pytest.mark.asyncio
    async def test_absent_session_terminates_and_redirects(self) -> None:
        state = _denied_state()

        with _validating_db() as (_, validating_repo), _terminating_db():
            validating_repo.find_by_user_and_session_id = AsyncMock(return_value=None)

            result = await state.check_auth()

        assert any("redirect" in name for name in _handler_names(result))
        assert state.auth_token == ""
        assert state.session_cookie == ""
        assert state._session_expires_at is None

    @pytest.mark.asyncio
    async def test_session_without_user_terminates(self) -> None:
        """A session row whose user row vanished must not authenticate."""
        state = _denied_state()

        with _validating_db() as (_, validating_repo), _terminating_db():
            validating_repo.find_by_user_and_session_id = AsyncMock(
                return_value=_session_row(user_entity=None)
            )

            result = await state.check_auth()

        assert any("redirect" in name for name in _handler_names(result))
        assert state.auth_token == ""

    @pytest.mark.asyncio
    async def test_deactivated_user_terminates(self) -> None:
        """Deactivating a user must take effect on their live session."""
        state = _denied_state()
        inactive = _user_entity(1, "alice")
        inactive.is_active = False

        with _validating_db() as (_, validating_repo), _terminating_db():
            validating_repo.find_by_user_and_session_id = AsyncMock(
                return_value=_session_row(user_entity=inactive)
            )

            result = await state.check_auth()

        assert any("redirect" in name for name in _handler_names(result))
        assert state.auth_token == ""

    @pytest.mark.asyncio
    async def test_validation_error_fails_closed(self) -> None:
        """check_auth redirects to login when the session cannot be validated.

        Regression guard: returning None here rendered the page anyway, so a
        database outage turned into an authorization bypass. Do not let this
        regress to a silent pass-through.
        """
        state = _StubLoginState()
        state.auth_token = "token"
        state.session_cookie = "token"
        state.user_id = 1
        state._session_expires_at = None

        with _validating_db() as (_, mock_repo):
            mock_repo.find_by_user_and_session_id = AsyncMock(
                side_effect=RuntimeError("db crash")
            )

            result = await state.check_auth()

        assert result is not None
        assert _handler_names(result) == {"_redirect"}
        # The session is preserved so the next monitor tick can still succeed.
        assert state.auth_token == "token"
        assert state.session_cookie == "token"

    @pytest.mark.asyncio
    async def test_stale_cache_does_not_rescue_an_error(self) -> None:
        """An expired cache must not be re-used when validation then fails."""
        state = _StubLoginState()
        state.auth_token = "token"
        state.user_id = 1
        state._session_expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with _validating_db() as (_, mock_repo):
            mock_repo.find_by_user_and_session_id = AsyncMock(
                side_effect=RuntimeError("db crash")
            )

            result = await state.check_auth()

        assert result is not None
        assert _handler_names(result) == {"_redirect"}


# ============================================================================
# Session invalidation on logout (real Reflex state tree)
# ============================================================================


async def _real_states() -> tuple[UserSession, LoginState]:
    """Build a real Reflex state tree and return (UserSession, LoginState).

    The stubs above hand-roll ``reset()`` so that it clears the session vars.
    Reflex does not behave that way for a substate: ``user``/``user_id``/
    ``auth_token`` are *inherited* vars owned by ``UserSession``, and
    ``State.reset()`` only walks ``base_vars``, which excludes them. These
    tests therefore drive the genuine state tree.
    """
    root = rx.State(_reflex_internal_init=True)
    session = await root.get_state(UserSession)
    login = await root.get_state(LoginState)
    return session, login


@contextmanager
def _live_session_repo() -> Iterator[MagicMock]:
    """Patch the DB so any lookup would return a valid, unexpired session.

    A gate that still holds the old token would authenticate against this,
    so the assertions below cannot pass vacuously.
    """
    user_session = _session_row(user_entity=_user_entity(1, "alice"))

    # One repo object shared by both modules: ``states`` owns the session
    # lifecycle, ``session_validation`` owns the lookups ``check_auth`` makes.
    # Sharing it lets a test re-point a finder and have both paths follow.
    mock_repo = MagicMock()
    mock_repo.save = AsyncMock()
    mock_repo.delete_by_user_and_session_id = AsyncMock()
    mock_repo.find_by_user_and_session_id = AsyncMock(return_value=user_session)
    mock_repo.find_by_session_id = AsyncMock(return_value=user_session)

    with (
        patch(f"{_PATCH}.get_asyncdb_session") as mock_ctx,
        patch(f"{_PATCH}.session_repo", mock_repo),
        patch(f"{_VPATCH}.get_asyncdb_session") as mock_v_ctx,
        patch(f"{_VPATCH}.session_repo", mock_repo),
    ):
        db = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_v_ctx.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_v_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_repo


class TestLogoutInvalidatesInheritedSession:
    """Logout must invalidate the session vars owned by ``UserSession``.

    These run against the real state tree rather than the stubs above, which
    hand-roll a ``reset()`` that clears everything and so cannot detect a
    regression here. The invariant relies on Reflex resolving an inherited
    event handler against the state that *defines* it (``BaseState`` delegates
    to ``parent_state``), so ``self`` inside ``terminate_session`` is the
    ``UserSession`` instance and ``reset()`` does cover these vars. If that
    dispatch ever changes, or ``terminate_session`` is redefined on a substate,
    these tests fail instead of the app silently keeping the old user.
    """

    @pytest.mark.asyncio
    async def test_logout_clears_session_vars_on_parent_state(self) -> None:
        session, login = await _real_states()

        with _live_session_repo():
            await login._create_session(AsyncMock(), _user_entity(1, "alice"))
            assert session.user is not None  # signed in

            await login.logout()

        assert session.user is None
        assert session.user_id == 0
        assert session.auth_token == ""
        assert session.session_cookie == ""
        assert session._session_expires_at is None

    @pytest.mark.asyncio
    async def test_gate_refuses_after_logout(self) -> None:
        """The authorization gate must answer False once logged out."""
        _, login = await _real_states()

        with _live_session_repo():
            await login._create_session(AsyncMock(), _user_entity(1, "alice"))
            assert await login.authenticated_user is not None

            await login.logout()

            assert await login.authenticated_user is None
            assert await login.is_authenticated is False

    @pytest.mark.asyncio
    async def test_logout_clears_session_storage_and_redirects(self) -> None:
        _, login = await _real_states()

        with _live_session_repo():
            await login._create_session(AsyncMock(), _user_entity(1, "alice"))
            result = await login.logout()

        events = result if isinstance(result, list) else [result]
        handlers = {event.handler.fn.__qualname__ for event in events}
        assert any("clear_session_storage" in name for name in handlers)
        assert any("redirect" in name for name in handlers)

    @pytest.mark.asyncio
    async def test_expired_session_clears_parent_state(self) -> None:
        """The check_auth expiry branch must invalidate the session too."""
        session, login = await _real_states()

        expired = _session_row(expired=True)

        with _live_session_repo() as mock_repo:
            await login._create_session(AsyncMock(), _user_entity(1, "alice"))
            # _create_session primes the expiry cache, which is authoritative
            # until the expiry instant. Drop it so check_auth really revalidates.
            session._session_expires_at = None
            login._session_expires_at = None
            mock_repo.find_by_user_and_session_id = AsyncMock(return_value=expired)
            mock_repo.find_by_session_id = AsyncMock(return_value=expired)

            await login.check_auth()

        assert session.user is None
        assert session.user_id == 0
        assert session.auth_token == ""
        assert session.session_cookie == ""
        assert session._session_expires_at is None


class _PrefsState(UserSession):
    """A consumer page state keeping a UI preference in the browser."""

    view: str = rx.LocalStorage("table", name="test_prefs_view")
    selected_id: int = 0


class TestTerminateKeepsConsumerBrowserStorage:
    """Ending a session must not overwrite the substates' browser storage.

    Consumer pages hang their ``rx.LocalStorage`` UI preferences below
    ``UserSession``. A plain ``reset()`` writes their defaults into the browser
    with the next delta, so every login, logout and session-filter denial wiped
    them. The login flow's own browser values in ``LoginState`` are cleared.
    """

    @pytest.mark.asyncio
    async def test_logout_keeps_consumer_local_storage(self) -> None:
        session, login = await _real_states()
        prefs = await session.get_state(_PrefsState)

        with _live_session_repo():
            await login._create_session(AsyncMock(), _user_entity(1, "alice"))
            prefs.view = "cards"
            prefs.selected_id = 5
            login.redirect_to = "/projects"
            login.oauth_state = "stale"

            await login.logout()

        assert prefs.view == "cards"
        assert prefs.selected_id == 0
        assert login.redirect_to == ""
        assert login.oauth_state == ""
        assert session.auth_token == ""
        assert session.session_cookie == ""

    @pytest.mark.asyncio
    async def test_prepare_login_keeps_consumer_local_storage(self) -> None:
        session, login = await _real_states()
        prefs = await session.get_state(_PrefsState)
        prefs.view = "cards"

        with _live_session_repo():
            await login._prepare_login()

        assert prefs.view == "cards"

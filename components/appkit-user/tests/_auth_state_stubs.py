# ruff: noqa: ARG002, SLF001, S105, S106
"""Shared stubs and helpers for the UserSession / LoginState test modules.

Split out of ``test_auth_states.py`` to keep each test module under the
1000-line limit. Holds the ``_unwrap`` binding helper, the model factories,
the DB-patching context managers and the ``_StubUserSession`` /
``_StubLoginState`` plain stubs.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, Final
from unittest.mock import AsyncMock, MagicMock, patch

from appkit_user.authentication.backend.models import User
from appkit_user.authentication.states import LoginState, UserSession

_PATCH = "appkit_user.authentication.states"
# check_auth no longer queries through ``states``: it delegates to the shared
# SessionValidator, which opens its own DB session in ``session_validation``.
# Patching only ``_PATCH`` would leave the validator talking to a real database.
_VPATCH = "appkit_user.authentication.session_validation"

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
    entity.name = name
    entity.email = email
    entity.avatar_url = ""
    entity.is_active = True
    entity.is_admin = False
    entity.is_verified = True
    entity.needs_password_reset = False
    entity.roles = []
    return entity


_UNSET: Final = object()


def _session_row(
    expired: bool = False,
    user_entity: Any = _UNSET,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Build a stand-in for a ``UserSessionEntity`` row.

    ``user_entity=None`` deliberately models a row whose user row is gone; the
    sentinel default is what yields the ordinary healthy user.
    """
    row = MagicMock()
    row.id = 7
    row.user_id = 1
    row.is_expired.return_value = expired
    row.user = _user_entity() if user_entity is _UNSET else user_entity
    row.expires_at = (
        datetime.now(UTC) + timedelta(minutes=25) if expires_at is None else expires_at
    )
    return row


@contextmanager
def _validating_db() -> Iterator[tuple[MagicMock, MagicMock]]:
    """Patch the DB layer the shared ``SessionValidator`` uses.

    Yields the patched ``get_asyncdb_session`` (so a test can prove no query
    was issued) and the patched ``session_repo``.
    """
    with (
        patch(f"{_VPATCH}.get_asyncdb_session") as mock_ctx,
        patch(f"{_VPATCH}.session_repo") as mock_repo,
    ):
        db = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_ctx, mock_repo


def _handler_names(result: object) -> set[str]:
    """Qualified handler names of the events an event handler returned."""
    events = result if isinstance(result, list) else [result]
    return {event.handler.fn.__qualname__ for event in events if event is not None}


def _prime_is_authenticated(state: _StubLoginState, value: bool) -> None:
    """Prime the awaitable ``is_authenticated`` var that ``redir()`` reads."""

    async def _result() -> bool:
        return value

    state.is_authenticated = _result()


# ============================================================================
# UserSession stub
# ============================================================================


class _StubUserSession:
    """Plain stub for UserSession."""

    def __init__(self) -> None:
        self.auth_token: str = ""
        self.session_cookie: str = ""
        self.user_id: int = 0
        self.user: User | None = None
        self._session_expires_at: datetime | None = None
        # No loaded substates, so terminate_session keeps no browser storage.
        self.substates: dict[str, object] = {}

    _execute_db_operation = _unwrap(UserSession, "_execute_db_operation")
    _find_valid_session = _unwrap(UserSession, "_find_valid_session")
    _create_session = _unwrap(UserSession, "_create_session")
    _has_unexpired_cache = _unwrap(UserSession, "_has_unexpired_cache")
    _cache_session = _unwrap(UserSession, "_cache_session")
    _trust_session_until = _unwrap(UserSession, "_trust_session_until")
    terminate_session = _unwrap(UserSession, "terminate_session")
    _reset_keeping_browser_prefs = _unwrap(UserSession, "_reset_keeping_browser_prefs")
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
        self.session_cookie: str = ""
        self.user_id: int = 0
        self.user: User | None = None
        self._session_expires_at: datetime | None = None
        # No loaded substates, so terminate_session keeps no browser storage.
        self.substates: dict[str, object] = {}
        self.redirect_to: str = ""
        self.homepage: str = "/"
        self.login_route: str = "/login"
        self.logout_route: str = "/login"
        self.is_loading: bool = False
        self.error_message: str = ""
        self.is_hydrated: bool = True
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
    _has_unexpired_cache = _unwrap(UserSession, "_has_unexpired_cache")
    _cache_session = _unwrap(UserSession, "_cache_session")
    _trust_session_until = _unwrap(UserSession, "_trust_session_until")
    terminate_session = _unwrap(UserSession, "terminate_session")
    _reset_keeping_browser_prefs = _unwrap(UserSession, "_reset_keeping_browser_prefs")
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
    _is_oauth_callback_path = _unwrap(LoginState, "_is_oauth_callback_path")

    async def get_state(self, cls: type) -> MagicMock:
        return MagicMock(user_id=0, user=None)

    def reset(self) -> None:
        """Model ``State.reset()`` as seen from a *substate*.

        Reflex's ``reset()`` walks ``base_vars``/``backend_vars``, both of which
        exclude vars inherited from a parent state. ``session_cookie`` and
        ``_session_expires_at`` are therefore deliberately left alone here, so a
        test asserting they are empty afterwards is asserting that
        ``terminate_session`` clears them *explicitly*.
        """
        self.auth_token = ""
        self.user_id = 0
        self.user = None

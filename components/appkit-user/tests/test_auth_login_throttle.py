# ruff: noqa: SLF001, S105, S106
"""Password login: throttle and forced password change."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _auth_state_stubs import _PATCH, _StubLoginState, _unwrap, _user_entity

from appkit_user.authentication.login_throttle import LoginThrottle
from appkit_user.authentication.states import (
    FORCED_RESET_MESSAGE,
    PASSWORD_RESET_CONFIRM_ROUTE,
    LoginState,
)
from appkit_user.configuration import LoginRateLimitConfig

_login = _unwrap(LoginState, "login_with_password")
_FORM = {"username": "Alice@Example.com", "password": "pw"}


@contextmanager
def _db(status: str, entity: MagicMock | None = None) -> Iterator[MagicMock]:
    with (
        patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
        patch(f"{_PATCH}.session_repo") as mock_s_repo,
        patch(f"{_PATCH}.user_repo") as mock_u_repo,
        patch(f"{_PATCH}.password_reset_token_repo") as mock_t_repo,
        patch(f"{_PATCH}._auth_config") as mock_config,
    ):
        db = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_u_repo.get_login_status_by_credentials = AsyncMock(
            return_value=(entity, status)
        )
        mock_s_repo.save = AsyncMock()
        mock_s_repo.delete_by_user_and_session_id = AsyncMock()
        mock_t_repo.create_token = AsyncMock(return_value=(MagicMock(), "raw-token"))
        mock_config.return_value.password_reset.token_expiry_minutes = 30
        mock_u_repo.token_repo = mock_t_repo
        mock_u_repo.db = db
        yield mock_u_repo


async def _run(state: _StubLoginState, form: dict | None = None) -> list:
    return [c async for c in _login(state, form or _FORM)]


class TestLoginThrottle:
    @pytest.mark.asyncio
    async def test_locked_login_skips_the_password_check(
        self, login_throttle: LoginThrottle
    ) -> None:
        state = _StubLoginState()
        for _ in range(5):
            login_throttle.record_failure(_FORM["username"])

        with _db("success", _user_entity()) as users:
            await _run(state)

        users.get_login_status_by_credentials.assert_not_called()
        assert "Zu viele" in state.error_message
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_wrong_password_counts_as_failure(
        self, login_throttle: LoginThrottle
    ) -> None:
        state = _StubLoginState()

        with _db("invalid_credentials"):
            for _ in range(5):
                await _run(state)

        assert login_throttle.retry_after(_FORM["username"]) > 0

    @pytest.mark.asyncio
    async def test_inactive_account_is_not_counted(
        self, login_throttle: LoginThrottle
    ) -> None:
        state = _StubLoginState()

        with _db("inactive"):
            for _ in range(6):
                await _run(state)

        assert login_throttle.retry_after(_FORM["username"]) == 0

    @pytest.mark.asyncio
    async def test_success_clears_the_failures(
        self, login_throttle: LoginThrottle
    ) -> None:
        state = _StubLoginState()
        for _ in range(4):
            login_throttle.record_failure(_FORM["username"])

        with _db("success", _user_entity()):
            await _run(state)
        login_throttle.record_failure(_FORM["username"])

        assert login_throttle.retry_after(_FORM["username"]) == 0

    @pytest.mark.asyncio
    async def test_client_address_is_counted(self) -> None:
        state = _StubLoginState()
        state.router.session.client_ip = "9.9.9.9"
        throttle = LoginThrottle(LoginRateLimitConfig(max_attempts_per_client=2))

        with (
            _db("invalid_credentials"),
            patch(f"{_PATCH}.get_login_throttle", return_value=throttle),
        ):
            await _run(state, {"username": "a@x.de", "password": "p"})
            await _run(state, {"username": "b@x.de", "password": "p"})

        assert throttle.retry_after("c@x.de", "9.9.9.9") > 0


class TestForcedPasswordChange:
    @pytest.mark.asyncio
    async def test_flagged_account_gets_a_reset_token_and_no_session(self) -> None:
        state = _StubLoginState()
        entity = _user_entity()
        entity.needs_password_reset = True
        state._create_session = AsyncMock()  # type: ignore[method-assign]

        with _db("success", entity) as users:
            events = await _run(state)

        state._create_session.assert_not_called()
        users.token_repo.create_token.assert_awaited_once()
        assert f"{PASSWORD_RESET_CONFIRM_ROUTE}?token=raw-token" in str(events[-1])
        assert FORCED_RESET_MESSAGE in str(events[0])

    @pytest.mark.asyncio
    async def test_unflagged_account_gets_a_session(self) -> None:
        state = _StubLoginState()
        state._create_session = AsyncMock()  # type: ignore[method-assign]

        with _db("success", _user_entity()) as users:
            await _run(state)

        state._create_session.assert_awaited_once()
        users.token_repo.create_token.assert_not_called()

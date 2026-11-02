# ruff: noqa: SLF001
"""Tests for the database-backed login throttle and its configuration."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from _throttle_store import SessionThrottleStore
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication import login_throttle
from appkit_user.authentication.backend.database import LoginThrottleEntity
from appkit_user.authentication.login_throttle import LoginThrottle
from appkit_user.configuration import (
    AuthenticationConfiguration,
    LoginRateLimitConfig,
)


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def make_throttle(
    async_session: AsyncSession, clock: _Clock
) -> Callable[..., LoginThrottle]:
    def _make(**overrides: int | bool) -> LoginThrottle:
        return LoginThrottle(
            LoginRateLimitConfig(**overrides),
            store=SessionThrottleStore(async_session),
            clock=clock,
        )

    return _make


class TestLoginThrottle:
    @pytest.mark.asyncio
    async def test_allows_until_the_limit_is_reached(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=3)

        for _ in range(2):
            await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("a@b.de") == 0

    @pytest.mark.asyncio
    async def test_locks_after_max_attempts(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=3, lockout_minutes=10)

        for _ in range(3):
            await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("a@b.de") == 600

    @pytest.mark.asyncio
    async def test_email_is_normalized(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=2)

        await throttle.record_failure("A@B.de")
        await throttle.record_failure(" a@b.DE ")

        assert await throttle.retry_after("a@b.de") > 0

    @pytest.mark.asyncio
    async def test_lock_expires(self, make_throttle, clock) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=1, lockout_minutes=1)
        await throttle.record_failure("a@b.de")

        clock.advance(61)

        assert await throttle.retry_after("a@b.de") == 0

    @pytest.mark.asyncio
    async def test_failures_outside_the_window_do_not_count(
        self,
        make_throttle,  # noqa: ANN001
        clock,  # noqa: ANN001
    ) -> None:
        throttle = make_throttle(max_attempts=2, window_minutes=1)
        await throttle.record_failure("a@b.de")

        clock.advance(61)
        await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("a@b.de") == 0

    @pytest.mark.asyncio
    async def test_success_clears_the_email(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=3)
        await throttle.record_failure("a@b.de")
        await throttle.record_failure("a@b.de")

        await throttle.record_success("a@b.de")
        await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("a@b.de") == 0

    @pytest.mark.asyncio
    async def test_other_emails_are_not_affected(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=1)

        await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("c@d.de") == 0

    @pytest.mark.asyncio
    async def test_client_has_its_own_higher_limit(self, make_throttle) -> None:  # noqa: ANN001
        throttle = make_throttle(max_attempts=2, max_attempts_per_client=3)

        await throttle.record_failure("a@b.de", "1.2.3.4")
        await throttle.record_failure("c@d.de", "1.2.3.4")
        assert await throttle.retry_after("e@f.de", "1.2.3.4") == 0

        await throttle.record_failure("g@h.de", "1.2.3.4")

        assert await throttle.retry_after("e@f.de", "1.2.3.4") > 0
        assert await throttle.retry_after("e@f.de", "5.6.7.8") == 0

    @pytest.mark.asyncio
    async def test_disabled_never_locks_or_stores(
        self,
        make_throttle,  # noqa: ANN001
        async_session: AsyncSession,
    ) -> None:
        throttle = make_throttle(enabled=False, max_attempts=1)

        await throttle.record_failure("a@b.de")

        assert await throttle.retry_after("a@b.de") == 0
        rows = (await async_session.execute(select(LoginThrottleEntity))).all()
        assert rows == []

    @pytest.mark.asyncio
    async def test_keys_are_stored_hashed(
        self,
        make_throttle,  # noqa: ANN001
        async_session: AsyncSession,
    ) -> None:
        throttle = make_throttle()

        await throttle.record_failure("Alice@Example.com", "9.9.9.9")

        keys = set(
            (await async_session.execute(select(LoginThrottleEntity.key))).scalars()
        )
        assert keys == {
            hashlib.sha256(b"email:alice@example.com").hexdigest(),
            hashlib.sha256(b"client:9.9.9.9").hexdigest(),
        }


class TestLoginRateLimitConfig:
    def test_defaults(self) -> None:
        config = LoginRateLimitConfig()

        assert config.enabled is True
        assert config.max_attempts == 5
        assert config.max_attempts_per_client == 20
        assert config.window_minutes == 15
        assert config.lockout_minutes == 15

    def test_limits_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            LoginRateLimitConfig(max_attempts=0)

    def test_part_of_the_authentication_configuration(self) -> None:
        config = AuthenticationConfiguration(
            server_url="http://x",
            server_port=0,
            login_rate_limit={"max_attempts": 9},
        )

        assert config.login_rate_limit.max_attempts == 9


class TestGetLoginThrottle:
    def _registry(self, config: LoginRateLimitConfig) -> MagicMock:
        registry = MagicMock()
        registry.get.return_value.login_rate_limit = config
        return registry

    def test_reuses_the_instance_for_the_same_config(self) -> None:
        registry = self._registry(LoginRateLimitConfig())
        with (
            patch.object(login_throttle, "_throttle", None),
            patch.object(login_throttle, "service_registry", return_value=registry),
        ):
            first = login_throttle.get_login_throttle()
            second = login_throttle.get_login_throttle()

        assert first is second

    def test_rebuilds_when_the_config_changes(self) -> None:
        with (
            patch.object(login_throttle, "_throttle", None),
            patch.object(
                login_throttle,
                "service_registry",
                return_value=self._registry(LoginRateLimitConfig()),
            ),
        ):
            first = login_throttle.get_login_throttle()
        with (
            patch.object(login_throttle, "_throttle", first),
            patch.object(
                login_throttle,
                "service_registry",
                return_value=self._registry(LoginRateLimitConfig(max_attempts=9)),
            ),
        ):
            second = login_throttle.get_login_throttle()

        assert second is not first
        assert second.config.max_attempts == 9

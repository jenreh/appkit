# ruff: noqa: SLF001
"""Tests for the in-memory login throttle and its configuration."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from appkit_user.authentication import login_throttle
from appkit_user.authentication.login_throttle import LoginThrottle
from appkit_user.configuration import (
    AuthenticationConfiguration,
    LoginRateLimitConfig,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _throttle(**overrides: int | bool) -> tuple[LoginThrottle, _Clock]:
    clock = _Clock()
    config = LoginRateLimitConfig(**overrides)
    return LoginThrottle(config, clock), clock


class TestLoginThrottle:
    def test_allows_until_the_limit_is_reached(self) -> None:
        throttle, _ = _throttle(max_attempts=3)

        for _ in range(2):
            throttle.record_failure("a@b.de")

        assert throttle.retry_after("a@b.de") == 0

    def test_locks_after_max_attempts(self) -> None:
        throttle, _ = _throttle(max_attempts=3, lockout_minutes=10)

        for _ in range(3):
            throttle.record_failure("a@b.de")

        assert throttle.retry_after("a@b.de") == 600

    def test_email_is_normalized(self) -> None:
        throttle, _ = _throttle(max_attempts=2)

        throttle.record_failure("A@B.de")
        throttle.record_failure(" a@b.DE ")

        assert throttle.retry_after("a@b.de") > 0

    def test_lock_expires(self) -> None:
        throttle, clock = _throttle(max_attempts=1, lockout_minutes=1)
        throttle.record_failure("a@b.de")

        clock.now += 61

        assert throttle.retry_after("a@b.de") == 0

    def test_failures_outside_the_window_do_not_count(self) -> None:
        throttle, clock = _throttle(max_attempts=2, window_minutes=1)
        throttle.record_failure("a@b.de")

        clock.now += 61
        throttle.record_failure("a@b.de")

        assert throttle.retry_after("a@b.de") == 0

    def test_success_clears_the_email(self) -> None:
        throttle, _ = _throttle(max_attempts=3)
        throttle.record_failure("a@b.de")
        throttle.record_failure("a@b.de")

        throttle.record_success("a@b.de")
        throttle.record_failure("a@b.de")

        assert throttle.retry_after("a@b.de") == 0

    def test_other_emails_are_not_affected(self) -> None:
        throttle, _ = _throttle(max_attempts=1)

        throttle.record_failure("a@b.de")

        assert throttle.retry_after("c@d.de") == 0

    def test_client_has_its_own_higher_limit(self) -> None:
        throttle, _ = _throttle(max_attempts=2, max_attempts_per_client=3)

        throttle.record_failure("a@b.de", "1.2.3.4")
        throttle.record_failure("c@d.de", "1.2.3.4")
        assert throttle.retry_after("e@f.de", "1.2.3.4") == 0

        throttle.record_failure("g@h.de", "1.2.3.4")

        assert throttle.retry_after("e@f.de", "1.2.3.4") > 0
        assert throttle.retry_after("e@f.de", "5.6.7.8") == 0

    def test_disabled_never_locks(self) -> None:
        throttle, _ = _throttle(enabled=False, max_attempts=1)

        throttle.record_failure("a@b.de")

        assert throttle.retry_after("a@b.de") == 0
        assert throttle._buckets == {}

    def test_tracked_keys_are_bounded(self) -> None:
        throttle, _ = _throttle()
        with patch.object(login_throttle, "_MAX_TRACKED_KEYS", 2):
            for name in ("a", "b", "c"):
                throttle.record_failure(f"{name}@x.de")

        assert len(throttle._buckets) == 2
        assert "email:a@x.de" not in throttle._buckets


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

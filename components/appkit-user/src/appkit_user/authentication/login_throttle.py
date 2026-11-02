"""Database-backed throttle for password logins.

Failed password attempts are counted per normalized email and, with a higher
limit, per client address (many users can share one office address). A key that
reaches its limit within ``window_minutes`` is locked for ``lockout_minutes``; a
locked login is refused before the password is checked, so it also costs no
scrypt run. A successful login clears the email's counter.

The counters live in ``auth_login_throttle``, so every worker and every restart
sees the same state. Keys are stored as SHA-256 hashes, never as the email or
address. The window is fixed (it starts at the first failure of a series), not
sliding. Behind a proxy set ``trusted_proxy_hops``, or all users share the
proxy's client address.
"""

import hashlib
import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.database.login_throttle_repository import (
    login_throttle_repo,
)
from appkit_user.configuration import (
    AuthenticationConfiguration,
    LoginRateLimitConfig,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ThrottleStore(Protocol):
    """Persistence behind the throttle."""

    async def locked_until(self, keys: list[str], now: datetime) -> datetime | None: ...

    async def register_failure(
        self,
        key: str,
        *,
        limit: int,
        window: timedelta,
        lockout: timedelta,
        now: datetime,
    ) -> bool: ...

    async def clear(self, key: str) -> None: ...


class DatabaseThrottleStore:
    """Stores the counters in the application database, one transaction per call."""

    async def locked_until(self, keys: list[str], now: datetime) -> datetime | None:
        async with get_asyncdb_session() as session:
            return await login_throttle_repo.locked_until(session, keys, now)

    async def register_failure(
        self,
        key: str,
        *,
        limit: int,
        window: timedelta,
        lockout: timedelta,
        now: datetime,
    ) -> bool:
        async with get_asyncdb_session() as session:
            return await login_throttle_repo.register_failure(
                session, key, limit=limit, window=window, lockout=lockout, now=now
            )

    async def clear(self, key: str) -> None:
        async with get_asyncdb_session() as session:
            await login_throttle_repo.clear(session, key)


class LoginThrottle:
    """Counts failed logins and reports how long a key stays locked."""

    def __init__(
        self,
        config: LoginRateLimitConfig,
        store: ThrottleStore | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._config = config
        self._store = store or DatabaseThrottleStore()
        self._clock = clock

    @property
    def config(self) -> LoginRateLimitConfig:
        return self._config

    @staticmethod
    def _digest(kind: str, value: str) -> str:
        return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()

    def _keys(self, email: str, client: str) -> list[tuple[str, int]]:
        """Throttle keys of a login with the failure limit of each."""
        keys = [
            (self._digest("email", email.strip().lower()), self._config.max_attempts)
        ]
        if client:
            keys.append(
                (
                    self._digest("client", client),
                    self._config.max_attempts_per_client,
                )
            )
        return keys

    async def retry_after(self, email: str, client: str = "") -> int:
        """Seconds until a login may be tried again; 0 when it may be tried now."""
        if not self._config.enabled:
            return 0
        now = self._clock()
        until = await self._store.locked_until(
            [key for key, _ in self._keys(email, client)], now
        )
        if until is None:
            return 0
        return max(0, math.ceil((until - now).total_seconds()))

    async def record_failure(self, email: str, client: str = "") -> None:
        """Count one failed password attempt; lock a key that reached its limit."""
        if not self._config.enabled:
            return
        now = self._clock()
        window = timedelta(minutes=self._config.window_minutes)
        lockout = timedelta(minutes=self._config.lockout_minutes)
        for key, limit in self._keys(email, client):
            if await self._store.register_failure(
                key, limit=limit, window=window, lockout=lockout, now=now
            ):
                logger.warning(
                    "Login locked for key %.12s after repeated failures", key
                )

    async def record_success(self, email: str) -> None:
        """Forget the failed attempts of ``email``."""
        if not self._config.enabled:
            return
        await self._store.clear(self._keys(email, "")[0][0])


_throttle: LoginThrottle | None = None


def get_login_throttle() -> LoginThrottle:
    """The shared throttle; rebuilt when the configured limits change."""
    global _throttle  # noqa: PLW0603
    config = service_registry().get(AuthenticationConfiguration).login_rate_limit
    if _throttle is None or _throttle.config != config:
        _throttle = LoginThrottle(config)
    return _throttle

"""In-memory throttle for password logins.

Failed password attempts are counted per normalized email and, with a higher
limit, per client address (many users can share one office address). Reaching
a limit locks that key for ``lockout_minutes``; a locked login is refused
before the password is checked, so it also costs no scrypt run. A successful
login clears the email's counter.

The state lives in the process: with several workers each one counts on its
own, so the effective limit is up to ``max_attempts`` per worker. A restart
clears it.
"""

import logging
import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from appkit_commons.registry import service_registry
from appkit_user.configuration import (
    AuthenticationConfiguration,
    LoginRateLimitConfig,
)

logger = logging.getLogger(__name__)

# Upper bound of tracked keys; the oldest are dropped first.
_MAX_TRACKED_KEYS = 10_000


@dataclass
class _Bucket:
    failures: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


class LoginThrottle:
    """Counts failed logins and reports how long a key stays locked."""

    def __init__(
        self,
        config: LoginRateLimitConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    @property
    def config(self) -> LoginRateLimitConfig:
        return self._config

    @staticmethod
    def _keys(email: str, client: str) -> list[str]:
        keys = [f"email:{email.strip().lower()}"]
        if client:
            keys.append(f"client:{client}")
        return keys

    def _limit(self, key: str) -> int:
        if key.startswith("client:"):
            return self._config.max_attempts_per_client
        return self._config.max_attempts

    def retry_after(self, email: str, client: str = "") -> int:
        """Seconds until a login may be tried again; 0 when it may be tried now."""
        if not self._config.enabled:
            return 0
        now = self._clock()
        remaining = 0.0
        for key in self._keys(email, client):
            bucket = self._buckets.get(key)
            if bucket is not None:
                remaining = max(remaining, bucket.locked_until - now)
        return math.ceil(remaining) if remaining > 0 else 0

    def record_failure(self, email: str, client: str = "") -> None:
        """Count one failed password attempt; lock a key that reached its limit."""
        if not self._config.enabled:
            return
        now = self._clock()
        window = self._config.window_minutes * 60
        for key in self._keys(email, client):
            bucket = self._bucket(key)
            while bucket.failures and now - bucket.failures[0] > window:
                bucket.failures.popleft()
            bucket.failures.append(now)
            if len(bucket.failures) >= self._limit(key):
                bucket.failures.clear()
                bucket.locked_until = now + self._config.lockout_minutes * 60
                logger.warning("Login locked for %s after repeated failures", key)

    def record_success(self, email: str) -> None:
        """Forget the failed attempts of ``email``."""
        self._buckets.pop(self._keys(email, "")[0], None)

    def _bucket(self, key: str) -> _Bucket:
        bucket = self._buckets.get(key)
        if bucket is None:
            if len(self._buckets) >= _MAX_TRACKED_KEYS:
                self._buckets.pop(next(iter(self._buckets)))
            bucket = self._buckets[key] = _Bucket()
        return bucket


_throttle: LoginThrottle | None = None


def get_login_throttle() -> LoginThrottle:
    """The shared throttle; rebuilt when the configured limits change."""
    global _throttle  # noqa: PLW0603
    config = service_registry().get(AuthenticationConfiguration).login_rate_limit
    if _throttle is None or _throttle.config != config:
        _throttle = LoginThrottle(config)
    return _throttle

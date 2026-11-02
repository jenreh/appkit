"""Throttle store for tests: the real repository on the test session."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database import login_throttle_repo


class SessionThrottleStore:
    """Throttle store that runs the real repository on the test session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def locked_until(self, keys: list[str], now: datetime) -> datetime | None:
        return await login_throttle_repo.locked_until(self._session, keys, now)

    async def register_failure(
        self,
        key: str,
        *,
        limit: int,
        window: timedelta,
        lockout: timedelta,
        now: datetime,
    ) -> bool:
        return await login_throttle_repo.register_failure(
            self._session, key, limit=limit, window=window, lockout=lockout, now=now
        )

    async def clear(self, key: str) -> None:
        await login_throttle_repo.clear(self._session, key)

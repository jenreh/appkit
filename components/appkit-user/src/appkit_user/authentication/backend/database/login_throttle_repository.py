"""Repository for the failed-login counters behind the login throttle."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database.entities import LoginThrottleEntity

logger = logging.getLogger(__name__)


def as_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime (SQLite returns naive values)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class LoginThrottleRepository:
    """Counts failures per key in a fixed window and locks keys at their limit.

    Does not commit: the caller owns the transaction. Rows are locked with
    ``SELECT ... FOR UPDATE`` so concurrent workers count every failure.
    """

    async def locked_until(
        self, session: AsyncSession, keys: list[str], now: datetime
    ) -> datetime | None:
        """Latest lock expiry among ``keys`` that is still in the future."""
        result = await session.execute(
            select(func.max(LoginThrottleEntity.locked_until)).where(
                LoginThrottleEntity.key.in_(keys),
                LoginThrottleEntity.locked_until > now,
            )
        )
        value = result.scalar()
        return as_utc(value) if value is not None else None

    async def register_failure(
        self,
        session: AsyncSession,
        key: str,
        *,
        limit: int,
        window: timedelta,
        lockout: timedelta,
        now: datetime,
    ) -> bool:
        """Count one failure for ``key``; return True when it became locked."""
        row = await self._lock_row(session, key)
        if row is None:
            try:
                async with session.begin_nested():
                    session.add(
                        LoginThrottleEntity(key=key, failures=0, window_started_at=now)
                    )
            except IntegrityError:
                logger.debug("Throttle row created concurrently")
            row = await self._lock_row(session, key)
            if row is None:  # pragma: no cover - the insert above just succeeded
                raise RuntimeError("Throttle row vanished")

        if now - as_utc(row.window_started_at) > window:
            row.failures = 0
            row.window_started_at = now
        row.failures += 1

        locked = row.failures >= limit
        if locked:
            row.failures = 0
            row.locked_until = now + lockout
        await session.flush()
        return locked

    async def clear(self, session: AsyncSession, key: str) -> None:
        """Forget the failures of ``key`` (successful login)."""
        await session.execute(
            delete(LoginThrottleEntity).where(LoginThrottleEntity.key == key)
        )

    async def delete_stale(
        self, session: AsyncSession, window: timedelta, now: datetime
    ) -> int:
        """Delete rows whose window is over and whose lock (if any) has expired."""
        result = await session.execute(
            delete(LoginThrottleEntity).where(
                LoginThrottleEntity.window_started_at < now - window,
                or_(
                    LoginThrottleEntity.locked_until.is_(None),
                    LoginThrottleEntity.locked_until < now,
                ),
            )
        )
        return cast("CursorResult[Any]", result).rowcount or 0

    @staticmethod
    async def _lock_row(session: AsyncSession, key: str) -> LoginThrottleEntity | None:
        result = await session.execute(
            select(LoginThrottleEntity)
            .where(LoginThrottleEntity.key == key)
            .with_for_update()
        )
        return result.scalar_one_or_none()


login_throttle_repo = LoginThrottleRepository()

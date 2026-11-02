"""Tests for LoginThrottleRepository."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database import (
    LoginThrottleEntity,
    LoginThrottleRepository,
)

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=10)


@pytest.fixture
def repo() -> LoginThrottleRepository:
    return LoginThrottleRepository()


async def _fail(
    repo: LoginThrottleRepository,
    session: AsyncSession,
    key: str = "k",
    *,
    limit: int = 3,
    now: datetime = NOW,
) -> bool:
    return await repo.register_failure(
        session, key, limit=limit, window=WINDOW, lockout=LOCKOUT, now=now
    )


class TestRegisterFailure:
    @pytest.mark.asyncio
    async def test_counts_below_limit_without_locking(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        assert not await _fail(repo, async_session)
        assert not await _fail(repo, async_session)

        assert await repo.locked_until(async_session, ["k"], NOW) is None

    @pytest.mark.asyncio
    async def test_locks_at_the_limit(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        results = [await _fail(repo, async_session) for _ in range(3)]

        assert results == [False, False, True]
        assert await repo.locked_until(async_session, ["k"], NOW) == NOW + LOCKOUT

    @pytest.mark.asyncio
    async def test_window_expiry_restarts_the_count(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        await _fail(repo, async_session)
        await _fail(repo, async_session)

        later = NOW + WINDOW + timedelta(seconds=1)
        assert not await _fail(repo, async_session, now=later)
        assert not await _fail(repo, async_session, now=later)

    @pytest.mark.asyncio
    async def test_keys_are_independent(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        for _ in range(3):
            await _fail(repo, async_session, "a")

        assert await repo.locked_until(async_session, ["b"], NOW) is None
        assert await repo.locked_until(async_session, ["a", "b"], NOW) is not None


class TestLockedUntil:
    @pytest.mark.asyncio
    async def test_expired_lock_is_ignored(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        for _ in range(3):
            await _fail(repo, async_session)

        after = NOW + LOCKOUT + timedelta(seconds=1)
        assert await repo.locked_until(async_session, ["k"], after) is None

    @pytest.mark.asyncio
    async def test_returns_the_latest_expiry(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        for _ in range(3):
            await _fail(repo, async_session, "a")
        for _ in range(3):
            await _fail(repo, async_session, "b", now=NOW + timedelta(minutes=1))

        assert (
            await repo.locked_until(async_session, ["a", "b"], NOW)
            == NOW + timedelta(minutes=1) + LOCKOUT
        )


class TestClearAndCleanup:
    @pytest.mark.asyncio
    async def test_clear_forgets_failures(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        for _ in range(3):
            await _fail(repo, async_session)

        await repo.clear(async_session, "k")

        assert await repo.locked_until(async_session, ["k"], NOW) is None
        assert not await _fail(repo, async_session)

    @pytest.mark.asyncio
    async def test_delete_stale_keeps_active_rows(
        self, repo: LoginThrottleRepository, async_session: AsyncSession
    ) -> None:
        await _fail(repo, async_session, "old")  # window long over
        for _ in range(3):  # lock outlasts the window
            await repo.register_failure(
                async_session,
                "locked",
                limit=3,
                window=WINDOW,
                lockout=timedelta(hours=1),
                now=NOW,
            )
        later = NOW + WINDOW + timedelta(minutes=1)
        await _fail(repo, async_session, "fresh", now=later)

        deleted = await repo.delete_stale(async_session, WINDOW, later)

        assert deleted == 1
        remaining = {
            row.key
            for row in (
                await async_session.execute(LoginThrottleEntity.__table__.select())
            ).all()
        }
        assert remaining == {"locked", "fresh"}

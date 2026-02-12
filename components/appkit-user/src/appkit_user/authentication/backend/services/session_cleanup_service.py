"""Session cleanup scheduler."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.user_session_repository import session_repo

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
CLEANUP_INTERVAL_MINUTES = 30  # Run every 30 minutes


async def _run_cleanup_job() -> None:
    """Run the session cleanup job."""
    try:
        logger.info("Running session cleanup job")
        async with get_asyncdb_session() as session:
            count = await session_repo.delete_expired(session)
            if count > 0:
                logger.info("Cleaned up %d expired user sessions", count)
    except Exception as e:
        logger.error("Session cleanup failed: %s", e)


def start_session_scheduler() -> None:
    """Start the session cleanup scheduler."""
    global _scheduler  # noqa: PLW0603

    if _scheduler:
        logger.warning("Session scheduler already running")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_cleanup_job,
        # Trigger cleanup every 30 minutes
        trigger=IntervalTrigger(minutes=CLEANUP_INTERVAL_MINUTES),
        id="session_cleanup",
        name="Clean up expired user sessions",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Session cleanup scheduler started (interval: %d min)", CLEANUP_INTERVAL_MINUTES
    )


def stop_session_scheduler() -> None:
    """Stop the session cleanup scheduler."""
    global _scheduler  # noqa: PLW0603
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Session scheduler stopped")

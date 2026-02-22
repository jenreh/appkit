"""Session cleanup scheduler."""

import logging

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.scheduler import (
    IntervalTrigger,
    ScheduledService,
    Trigger,
)
from appkit_user.authentication.backend.database.user_session_repository import (
    session_repo,
)

logger = logging.getLogger(__name__)


class SessionCleanupService(ScheduledService):
    """Service to clean up expired user sessions."""

    job_id = "session_cleanup"
    name = "Clean up expired user sessions"

    def __init__(self, interval_minutes: int = 30) -> None:
        """Initialize the service.

        Args:
            interval_minutes: How often to run the cleanup job (default: 30 min).
        """
        self.interval_minutes = interval_minutes

    @property
    def trigger(self) -> Trigger:
        """Run periodically based on configured interval."""
        return IntervalTrigger(minutes=self.interval_minutes)

    async def execute(self) -> None:
        """Execute the cleanup logic."""
        try:
            logger.info("Running session cleanup job")
            async with get_asyncdb_session() as session:
                count = await session_repo.delete_expired(session)
                if count > 0:
                    logger.info("Cleaned up %d expired user sessions", count)
        except Exception as e:
            logger.error("Session cleanup failed: %s", e)

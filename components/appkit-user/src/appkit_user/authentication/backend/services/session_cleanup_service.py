"""Session cleanup scheduler."""

import logging
from datetime import UTC, datetime, timedelta

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_commons.scheduler import (
    IntervalTrigger,
    ScheduledService,
    Trigger,
)
from appkit_user.authentication.backend.database import (
    login_throttle_repo,
    session_repo,
)
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)


class SessionCleanupService(ScheduledService):
    """Service to clean up expired user sessions and stale login-throttle rows."""

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

                window = timedelta(
                    minutes=service_registry()
                    .get(AuthenticationConfiguration)
                    .login_rate_limit.window_minutes
                )
                stale = await login_throttle_repo.delete_stale(
                    session, window, datetime.now(UTC)
                )
                if stale > 0:
                    logger.info("Cleaned up %d stale login throttle rows", stale)
        except Exception as e:
            logger.error("Session cleanup failed: %s", e)

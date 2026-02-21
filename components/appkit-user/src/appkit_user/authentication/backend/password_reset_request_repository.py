"""Repository for password reset request rate limiting."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.entities import PasswordResetRequestEntity

logger = logging.getLogger(__name__)


class PasswordResetRequestRepository(
    BaseRepository[PasswordResetRequestEntity, AsyncSession]
):
    """Repository for managing password reset request rate limiting."""

    @property
    def model_class(self) -> type[PasswordResetRequestEntity]:
        return PasswordResetRequestEntity

    async def count_recent_requests(
        self, session: AsyncSession, email: str, hours: int = 1
    ) -> int:
        """Count recent password reset requests for an email.

        Args:
            session: Database session
            email: Email address
            hours: Time window in hours (default 1)

        Returns:
            Number of requests in the time window
        """
        since = datetime.now(UTC) - timedelta(hours=hours)
        since_naive = since.replace(tzinfo=None)

        stmt = (
            select(func.count())
            .select_from(PasswordResetRequestEntity)
            .where(
                PasswordResetRequestEntity.email == email,
                PasswordResetRequestEntity.created_at >= since_naive,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0

        return count

    async def log_request(
        self, session: AsyncSession, email: str, ip_address: str | None = None
    ) -> PasswordResetRequestEntity:
        """Log a password reset request.

        Args:
            session: Database session
            email: Email address
            ip_address: IP address of requester (optional)

        Returns:
            Created PasswordResetRequestEntity
        """
        entity = PasswordResetRequestEntity(
            email=email,
            ip_address=ip_address,
        )

        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        logger.debug("Logged password reset request for email=%s, ip=%s", email, ip_address)
        return entity

    async def cleanup_old_requests(
        self, session: AsyncSession, days: int = 7
    ) -> int:
        """Clean up old password reset requests.

        Args:
            session: Database session
            days: Age threshold in days (default 7)

        Returns:
            Number of requests deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        cutoff_naive = cutoff.replace(tzinfo=None)

        stmt = delete(PasswordResetRequestEntity).where(
            PasswordResetRequestEntity.created_at < cutoff_naive
        )
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount or 0
        if deleted_count > 0:
            logger.info("Cleaned up %d old password reset requests", deleted_count)

        return deleted_count


# Singleton instance
password_reset_request_repo = PasswordResetRequestRepository()

"""Repository for password history management."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_commons.security import check_password_hash
from appkit_user.authentication.backend.entities import PasswordHistoryEntity

logger = logging.getLogger(__name__)


class PasswordHistoryRepository(BaseRepository[PasswordHistoryEntity, AsyncSession]):
    """Repository for managing password history."""

    @property
    def model_class(self) -> type[PasswordHistoryEntity]:
        return PasswordHistoryEntity

    async def get_last_n_password_hashes(
        self, session: AsyncSession, user_id: int, n: int = 6
    ) -> list[str]:
        """Get last N password hashes for a user.

        Args:
            session: Database session
            user_id: User ID
            n: Number of recent passwords to retrieve (default 6)

        Returns:
            List of password hashes, ordered by most recent first
        """
        stmt = (
            select(PasswordHistoryEntity.password_hash)
            .where(PasswordHistoryEntity.user_id == user_id)
            .order_by(PasswordHistoryEntity.changed_at.desc())
            .limit(n)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def check_password_reuse(
        self, session: AsyncSession, user_id: int, new_password: str, n: int = 6
    ) -> bool:
        """Check if a new password matches any of the last N passwords.

        Args:
            session: Database session
            user_id: User ID
            new_password: Plaintext password to check
            n: Number of recent passwords to check (default 6)

        Returns:
            True if password was previously used, False otherwise
        """
        recent_hashes = await self.get_last_n_password_hashes(session, user_id, n)

        for password_hash in recent_hashes:
            if check_password_hash(password_hash, new_password):
                logger.warning("Password reuse detected for user_id=%d", user_id)
                return True

        return False

    async def save_password_to_history(
        self,
        session: AsyncSession,
        user_id: int,
        password_hash: str,
        change_reason: str,
    ) -> PasswordHistoryEntity:
        """Save a password hash to history.

        Args:
            session: Database session
            user_id: User ID
            password_hash: Hashed password
            change_reason: Reason for password change

        Returns:
            Created PasswordHistoryEntity
        """
        entity = PasswordHistoryEntity(
            user_id=user_id,
            password_hash=password_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
            change_reason=change_reason,
        )

        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        logger.info(
            "Saved password to history for user_id=%d, reason=%s",
            user_id,
            change_reason,
        )
        return entity


# Singleton instance
password_history_repo = PasswordHistoryRepository()

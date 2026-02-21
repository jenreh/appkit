"""Repository for password reset token management."""

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.entities import PasswordResetTokenEntity

logger = logging.getLogger(__name__)

TOKEN_CHARS = string.ascii_letters + string.digits + "-_"


def _generate_reset_token() -> str:
    """Generate a URL-safe password reset token (64 characters)."""
    return "".join(secrets.choice(TOKEN_CHARS) for _ in range(64))


class PasswordResetTokenRepository(BaseRepository[PasswordResetTokenEntity, AsyncSession]):
    """Repository for managing password reset tokens."""

    @property
    def model_class(self) -> type[PasswordResetTokenEntity]:
        return PasswordResetTokenEntity

    async def find_by_token(
        self, session: AsyncSession, token: str
    ) -> PasswordResetTokenEntity | None:
        """Find a password reset token by its token value.

        Args:
            session: Database session
            token: The reset token string

        Returns:
            PasswordResetTokenEntity if found, None otherwise
        """
        stmt = select(PasswordResetTokenEntity).where(
            PasswordResetTokenEntity.token == token
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def create_token(
        self,
        session: AsyncSession,
        user_id: int,
        email: str,
        reset_type: str,
        expiry_minutes: int = 60,
    ) -> PasswordResetTokenEntity:
        """Create a new password reset token.

        Args:
            session: Database session
            user_id: User ID for whom to create the token
            email: Email address associated with the reset
            reset_type: Type of reset ("user_initiated" or "admin_forced")
            expiry_minutes: Token expiration time in minutes (default 60)

        Returns:
            Created PasswordResetTokenEntity
        """
        token = _generate_reset_token()
        expires_at = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

        entity = PasswordResetTokenEntity(
            user_id=user_id,
            token=token,
            email=email,
            reset_type=reset_type,
            is_used=False,
            expires_at=expires_at.replace(tzinfo=None),
        )

        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        logger.info("Created password reset token for user_id=%d, type=%s", user_id, reset_type)
        return entity

    async def mark_as_used(
        self, session: AsyncSession, token_id: int
    ) -> None:
        """Mark a token as used.

        Args:
            session: Database session
            token_id: ID of the token to mark as used
        """
        stmt = select(PasswordResetTokenEntity).where(
            PasswordResetTokenEntity.id == token_id
        )
        result = await session.execute(stmt)
        token_entity = result.scalars().first()

        if token_entity:
            token_entity.is_used = True
            await session.commit()
            logger.info("Marked password reset token id=%d as used", token_id)

    async def delete_expired(self, session: AsyncSession) -> int:
        """Delete expired tokens.

        Args:
            session: Database session

        Returns:
            Number of tokens deleted
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = delete(PasswordResetTokenEntity).where(
            PasswordResetTokenEntity.expires_at < now
        )
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount or 0
        if deleted_count > 0:
            logger.info("Deleted %d expired password reset tokens", deleted_count)

        return deleted_count

    async def delete_by_user_id(self, session: AsyncSession, user_id: int) -> int:
        """Delete all tokens for a specific user.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            Number of tokens deleted
        """
        stmt = delete(PasswordResetTokenEntity).where(
            PasswordResetTokenEntity.user_id == user_id
        )
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount or 0
        if deleted_count > 0:
            logger.info("Deleted %d password reset tokens for user_id=%d", deleted_count, user_id)

        return deleted_count


# Singleton instance
password_reset_token_repo = PasswordResetTokenRepository()

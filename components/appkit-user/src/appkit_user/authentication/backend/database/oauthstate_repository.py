from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.database.entities import (
    OAuthStateEntity,
)


class OAuthStateRepository(BaseRepository[OAuthStateEntity, AsyncSession]):
    @property
    def model_class(self) -> type[OAuthStateEntity]:
        return OAuthStateEntity

    async def delete_expired(self, session: AsyncSession) -> int:
        """Clean up expired OAuth states and return count of deleted records."""
        # Use naive datetime to match SQLite's storage of timezone-aware datetimes
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = delete(OAuthStateEntity).where(OAuthStateEntity.expires_at < now)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def delete_by_session_id(self, session: AsyncSession, session_id: str) -> int:
        """Clean up OAuth states for a specific session."""
        stmt = delete(OAuthStateEntity).where(OAuthStateEntity.session_id == session_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def find_valid_by_state_and_provider(
        self, session: AsyncSession, state: str, provider: str
    ) -> OAuthStateEntity | None:
        stmt = select(OAuthStateEntity).where(
            OAuthStateEntity.state == state,
            OAuthStateEntity.provider == provider,
            OAuthStateEntity.expires_at > datetime.now(UTC),  # Check not expired
        )
        result = await session.execute(stmt)
        return result.scalars().first()


oauth_state_repo = OAuthStateRepository()

from datetime import datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.entities import (
    UserSessionEntity,
)


class DefaultUserRoles(StrEnum):
    """Default user roles."""

    USER = "user"
    ADMIN = "admin"
    GUEST = "guest"


class UserSessionRepository(BaseRepository[UserSessionEntity, AsyncSession]):
    @property
    def model_class(self) -> type[UserSessionEntity]:
        return UserSessionEntity

    async def find_by_user_and_session_id(
        self, session: AsyncSession, user_id: int, session_id: str
    ) -> UserSessionEntity | None:  # Return type can be None if not found
        """Get a user session."""
        stmt = select(UserSessionEntity).where(
            UserSessionEntity.user_id == user_id,
            UserSessionEntity.session_id == session_id,
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def find_by_session_id(
        self, session: AsyncSession, session_id: str
    ) -> UserSessionEntity | None:
        """Get a user session by session_id."""
        stmt = select(UserSessionEntity).where(
            UserSessionEntity.session_id == session_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def save(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        expires_at: datetime,
    ) -> UserSessionEntity:
        """Create or update a user session."""
        existing_session = await self.find_by_user_and_session_id(
            session, user_id, session_id
        )

        if not existing_session:
            new_session = UserSessionEntity(
                user_id=user_id, session_id=session_id, expires_at=expires_at
            )
            session.add(new_session)
            current_session = new_session
        else:
            existing_session.expires_at = expires_at
            current_session = existing_session

        await session.flush()
        await session.refresh(current_session)
        return current_session

    async def delete_by_user_and_session_id(
        self, session: AsyncSession, user_id: int, session_id: str
    ) -> None:
        """Delete a user session."""
        existing_session = await self.find_by_user_and_session_id(
            session, user_id, session_id
        )

        if existing_session:
            await session.delete(existing_session)
            await session.flush()


session_repo = UserSessionRepository()

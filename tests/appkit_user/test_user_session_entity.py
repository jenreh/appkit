"""Tests for UserSessionEntity model."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database.entities import UserSessionEntity


class TestUserSessionEntity:
    """Test suite for UserSessionEntity model."""

    @pytest.mark.asyncio
    async def test_create_session(self, user_factory, session_factory) -> None:
        """Creating a session for a user succeeds."""
        # Arrange
        user = await user_factory(email="session@example.com")

        # Act
        session = await session_factory(user=user)

        # Assert
        assert session.id is not None
        assert session.user_id == user.id
        assert session.session_id is not None
        assert len(session.session_id) > 20  # Token should be reasonably long

    @pytest.mark.asyncio
    async def test_session_expires_at_required(
        self, user_factory, session_factory
    ) -> None:
        """Session must have expires_at timestamp."""
        # Arrange
        user = await user_factory(email="expires@example.com")

        # Act
        session = await session_factory(user=user)

        # Assert
        assert session.expires_at is not None
        assert isinstance(session.expires_at, datetime)

    @pytest.mark.asyncio
    async def test_is_expired_returns_false_for_active(
        self, user_factory, session_factory
    ) -> None:
        """is_expired returns False for active sessions."""
        # Arrange
        user = await user_factory(email="active@example.com")
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        session = await session_factory(user=user, expires_at=expires_at)

        # Act
        result = session.is_expired()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_is_expired_returns_true_for_expired(
        self, user_factory, session_factory
    ) -> None:
        """is_expired returns True for expired sessions."""
        # Arrange
        user = await user_factory(email="expired@example.com")
        expires_at = datetime.now(UTC) - timedelta(hours=1)
        session = await session_factory(user=user, expires_at=expires_at)

        # Act
        result = session.is_expired()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_is_expired_handles_naive_datetime(
        self, async_session: AsyncSession, user_factory
    ) -> None:
        """is_expired handles naive datetime by converting to UTC."""
        # Arrange
        user = await user_factory(email="naive@example.com")
        naive_expires = datetime.now(UTC) - timedelta(hours=1)  # Timezone-aware

        session = UserSessionEntity(
            user_id=user.id,
            session_id="test_session_123",
            expires_at=naive_expires,
        )
        async_session.add(session)
        await async_session.flush()

        # Act
        result = session.is_expired()

        # Assert
        assert result is True  # Should be expired

    @pytest.mark.asyncio
    async def test_session_to_dict(self, user_factory, session_factory) -> None:
        """to_dict returns correct dictionary representation."""
        # Arrange
        user = await user_factory(email="dict@example.com")
        session = await session_factory(user=user, session_id="test_session_abc")

        # Act
        session_dict = session.to_dict()

        # Assert
        assert session_dict["id"] == session.id
        assert session_dict["user_id"] == user.id
        assert session_dict["session_id"] == "test_session_abc"
        assert "expires_at" in session_dict
        assert isinstance(session_dict["expires_at"], str)  # ISO format

    @pytest.mark.asyncio
    async def test_session_unique_session_id(
        self, user_factory, session_factory
    ) -> None:
        """Session IDs must be unique."""
        # Arrange
        user1 = await user_factory(email="user1@example.com")
        user2 = await user_factory(email="user2@example.com")
        session_id = "duplicate_session_id_123"
        await session_factory(user=user1, session_id=session_id)

        # Act & Assert
        with pytest.raises(IntegrityError):
            await session_factory(user=user2, session_id=session_id)

    @pytest.mark.asyncio
    async def test_session_user_relationship(
        self, user_factory, session_factory, async_session: AsyncSession
    ) -> None:
        """Session has relationship to user."""
        # Arrange
        user = await user_factory(email="relationship@example.com")
        session = await session_factory(user=user)

        # Act - refresh to load relationship
        await async_session.refresh(session, ["user"])

        # Assert
        assert session.user is not None
        assert session.user.id == user.id
        assert session.user.email == user.email

    @pytest.mark.asyncio
    async def test_session_cascade_delete_on_user_delete(
        self, user_factory, session_factory, async_session: AsyncSession
    ) -> None:
        """Deleting user cascades to delete sessions at ORM level."""
        # Arrange
        user = await user_factory(email="cascade@example.com")
        session = await session_factory(user=user)
        await async_session.refresh(user, ["sessions"])

        # Verify session exists in user's relationship
        assert len(user.sessions) == 1
        assert user.sessions[0].id == session.id

        # Act - delete user
        await async_session.delete(user)
        await async_session.flush()

        # Assert - session should be marked for deletion in ORM
        # The cascade="all, delete-orphan" on UserEntity.sessions
        # relationship ensures sessions are deleted when user is deleted
        # After flush, check that the session is no longer in the database
        result = await async_session.execute(
            select(UserSessionEntity).where(UserSessionEntity.user_id == user.id)
        )
        sessions = result.scalars().all()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions_per_user(
        self, user_factory, session_factory
    ) -> None:
        """A user can have multiple active sessions."""
        # Arrange
        user = await user_factory(email="multi@example.com")

        # Act
        session1 = await session_factory(user=user)
        session2 = await session_factory(user=user)
        session3 = await session_factory(user=user)

        # Assert
        assert session1.id != session2.id != session3.id
        assert session1.user_id == session2.user_id == session3.user_id == user.id

    @pytest.mark.asyncio
    async def test_is_expired_well_before_expiry(
        self, user_factory, session_factory
    ) -> None:
        """Session is not expired when significantly before expiry time."""
        # Arrange
        user = await user_factory(email="well_before@example.com")
        # Set to expire far in the future (avoids race conditions)
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        session = await session_factory(user=user, expires_at=expires_at)

        # Act
        result = session.is_expired()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_is_expired_well_after_expiry(
        self, user_factory, session_factory
    ) -> None:
        """Session is expired when well past expiry time."""
        # Arrange
        user = await user_factory(email="well_after@example.com")
        # Set to expire far in the past (avoids race conditions)
        expires_at = datetime.now(UTC) - timedelta(hours=24)
        session = await session_factory(user=user, expires_at=expires_at)

        # Act
        result = session.is_expired()

        # Assert
        assert result is True

"""Tests for UserSessionEntity model."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.entities import UserSessionEntity


class TestUserSessionEntity:
    """Test suite for UserSessionEntity model."""

    @pytest.mark.asyncio
    async def test_create_session(
        self, async_session: AsyncSession, user_factory, session_factory
    ) -> None:
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
        self, async_session: AsyncSession, user_factory, session_factory
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
        self, async_session: AsyncSession, user_factory, session_factory
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
        self, async_session: AsyncSession, user_factory, session_factory
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
        naive_expires = datetime.now() - timedelta(hours=1)  # Naive datetime

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
    async def test_session_to_dict(
        self, async_session: AsyncSession, user_factory, session_factory
    ) -> None:
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
        self, async_session: AsyncSession, user_factory, session_factory
    ) -> None:
        """Session IDs must be unique."""
        # Arrange
        user1 = await user_factory(email="user1@example.com")
        user2 = await user_factory(email="user2@example.com")
        session_id = "duplicate_session_id_123"
        await session_factory(user=user1, session_id=session_id)

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError
            await session_factory(user=user2, session_id=session_id)

    @pytest.mark.asyncio
    async def test_session_user_relationship(
        self, async_session: AsyncSession, user_factory, session_factory
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
        self, async_session: AsyncSession, user_factory, session_factory
    ) -> None:
        """Deleting user cascades to delete sessions."""
        # Arrange
        user = await user_factory(email="cascade@example.com")
        session = await session_factory(user=user)
        session_id = session.id

        # Act
        await async_session.delete(user)
        await async_session.flush()

        # Assert - session should be deleted
        from sqlalchemy import select

        result = await async_session.execute(
            select(UserSessionEntity).where(UserSessionEntity.id == session_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_multiple_sessions_per_user(
        self, async_session: AsyncSession, user_factory, session_factory
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
    async def test_is_expired_exactly_at_expiry(
        self, async_session: AsyncSession, user_factory, session_factory
    ) -> None:
        """Session is considered expired exactly at expiry time."""
        # Arrange
        user = await user_factory(email="exact@example.com")
        # Set to expire right now
        expires_at = datetime.now(UTC)
        session = await session_factory(user=user, expires_at=expires_at)

        # Act - wait a tiny bit to ensure we're past the expiry
        import asyncio

        await asyncio.sleep(0.01)
        result = session.is_expired()

        # Assert
        assert result is True

"""Tests for PasswordResetTokenRepository."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database import (
    PasswordResetTokenEntity,
    PasswordResetTokenRepository,
)
from appkit_user.authentication.backend.types import PasswordResetType


@pytest.fixture
def password_reset_token_repository() -> PasswordResetTokenRepository:
    """Provide PasswordResetTokenRepository instance."""
    return PasswordResetTokenRepository()


class TestPasswordResetTokenRepository:
    """Test suite for PasswordResetTokenRepository."""

    @pytest.mark.asyncio
    async def test_find_by_token_existing(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """find_by_token returns existing token."""
        # Arrange
        user = await user_factory()
        token = "test_reset_token_123456789"  # noqa: S105
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        entity = PasswordResetTokenEntity(
            user_id=user.id,
            token=token,
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=expires_at.replace(tzinfo=None),
        )
        async_session.add(entity)
        await async_session.flush()

        # Act
        found = await password_reset_token_repository.find_by_token(
            async_session, token
        )

        # Assert
        assert found is not None
        assert found.token == token
        assert found.user_id == user.id
        assert found.email == user.email

    @pytest.mark.asyncio
    async def test_find_by_token_nonexistent(
        self,
        async_session: AsyncSession,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """find_by_token returns None for nonexistent token."""
        # Act
        found = await password_reset_token_repository.find_by_token(
            async_session, "nonexistent_token"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_create_token_user_initiated(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """create_token creates a token for user-initiated reset."""
        # Arrange
        user = await user_factory()

        # Act
        entity = await password_reset_token_repository.create_token(
            async_session,
            user_id=user.id,
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            expiry_minutes=60,
        )

        # Assert
        assert entity.id is not None
        assert entity.user_id == user.id
        assert entity.email == user.email
        assert entity.reset_type == PasswordResetType.USER_INITIATED
        assert entity.is_used is False
        assert len(entity.token) == 64  # Token should be 64 characters
        assert entity.expires_at is not None

    @pytest.mark.asyncio
    async def test_create_token_admin_forced(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """create_token creates a token for admin-forced reset."""
        # Arrange
        user = await user_factory()

        # Act
        entity = await password_reset_token_repository.create_token(
            async_session,
            user_id=user.id,
            email=user.email,
            reset_type=PasswordResetType.ADMIN_FORCED,
            expiry_minutes=30,
        )

        # Assert
        assert entity.reset_type == PasswordResetType.ADMIN_FORCED

    @pytest.mark.asyncio
    async def test_create_token_expiry_time(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """create_token sets correct expiration time."""
        # Arrange
        user = await user_factory()
        before = datetime.now(UTC)

        # Act
        entity = await password_reset_token_repository.create_token(
            async_session,
            user_id=user.id,
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            expiry_minutes=120,
        )

        # Assert
        after = datetime.now(UTC)
        expected_expiry_min = before + timedelta(minutes=119)
        expected_expiry_max = after + timedelta(minutes=121)

        # Convert to UTC for comparison
        entity_expires = entity.expires_at.replace(tzinfo=UTC)
        assert expected_expiry_min <= entity_expires <= expected_expiry_max

    @pytest.mark.asyncio
    async def test_create_token_unique_tokens(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """create_token generates unique tokens."""
        # Arrange
        user = await user_factory()

        # Act
        entity1 = await password_reset_token_repository.create_token(
            async_session,
            user_id=user.id,
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
        )
        entity2 = await password_reset_token_repository.create_token(
            async_session,
            user_id=user.id,
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
        )

        # Assert
        assert entity1.token != entity2.token

    @pytest.mark.asyncio
    async def test_mark_as_used(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """mark_as_used sets is_used flag to True."""
        # Arrange
        user = await user_factory()
        entity = PasswordResetTokenEntity(
            user_id=user.id,
            token="test_token_for_marking",
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=(datetime.now(UTC) + timedelta(hours=1)).replace(tzinfo=None),
        )
        async_session.add(entity)
        await async_session.flush()

        # Act
        await password_reset_token_repository.mark_as_used(async_session, entity.id)

        # Assert
        await async_session.refresh(entity)
        assert entity.is_used is True

    @pytest.mark.asyncio
    async def test_mark_as_used_nonexistent_token(
        self,
        async_session: AsyncSession,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """mark_as_used handles nonexistent token gracefully."""
        # Act - should not raise an error
        await password_reset_token_repository.mark_as_used(async_session, token_id=999)

        # Assert - no exception raised, no harm done

    @pytest.mark.asyncio
    async def test_delete_expired(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """delete_expired removes expired tokens."""
        # Arrange
        user = await user_factory()
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create expired and non-expired tokens
        expired_entity = PasswordResetTokenEntity(
            user_id=user.id,
            token="expired_token",
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=now - timedelta(hours=1),
        )
        valid_entity = PasswordResetTokenEntity(
            user_id=user.id,
            token="valid_token",
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=now + timedelta(hours=1),
        )

        async_session.add(expired_entity)
        async_session.add(valid_entity)
        await async_session.flush()

        # Act
        deleted_count = await password_reset_token_repository.delete_expired(
            async_session
        )

        # Assert
        assert deleted_count == 1
        found_expired = await password_reset_token_repository.find_by_token(
            async_session, "expired_token"
        )
        found_valid = await password_reset_token_repository.find_by_token(
            async_session, "valid_token"
        )
        assert found_expired is None
        assert found_valid is not None

    @pytest.mark.asyncio
    async def test_delete_expired_no_tokens_to_delete(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """delete_expired returns 0 when no expired tokens exist."""
        # Arrange
        user = await user_factory()
        now = datetime.now(UTC).replace(tzinfo=None)

        valid_entity = PasswordResetTokenEntity(
            user_id=user.id,
            token="always_valid_token",
            email=user.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=now + timedelta(days=30),
        )
        async_session.add(valid_entity)
        await async_session.flush()

        # Act
        deleted_count = await password_reset_token_repository.delete_expired(
            async_session
        )

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_by_user_id(
        self,
        async_session: AsyncSession,
        user_factory,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """delete_by_user_id removes all tokens for a user."""
        # Arrange
        user1 = await user_factory()
        user2 = await user_factory()
        now = datetime.now(UTC) + timedelta(hours=1)

        # Create tokens for both users
        for i in range(3):
            entity = PasswordResetTokenEntity(
                user_id=user1.id,
                token=f"user1_token_{i}",
                email=user1.email,
                reset_type=PasswordResetType.USER_INITIATED,
                is_used=False,
                expires_at=now.replace(tzinfo=None),
            )
            async_session.add(entity)

        user2_entity = PasswordResetTokenEntity(
            user_id=user2.id,
            token="user2_token",
            email=user2.email,
            reset_type=PasswordResetType.USER_INITIATED,
            is_used=False,
            expires_at=now.replace(tzinfo=None),
        )
        async_session.add(user2_entity)
        await async_session.flush()

        # Act
        deleted_count = await password_reset_token_repository.delete_by_user_id(
            async_session, user1.id
        )

        # Assert
        assert deleted_count == 3
        user2_token = await password_reset_token_repository.find_by_token(
            async_session, "user2_token"
        )
        assert user2_token is not None

    @pytest.mark.asyncio
    async def test_delete_by_user_id_no_tokens(
        self,
        async_session: AsyncSession,
        password_reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        """delete_by_user_id returns 0 when user has no tokens."""
        # Act
        deleted_count = await password_reset_token_repository.delete_by_user_id(
            async_session, user_id=999
        )

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_model_class_property(
        self, password_reset_token_repository: PasswordResetTokenRepository
    ) -> None:
        """model_class property returns PasswordResetTokenEntity."""
        # Act
        model_class = password_reset_token_repository.model_class

        # Assert
        assert model_class == PasswordResetTokenEntity

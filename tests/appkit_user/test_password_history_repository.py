"""Tests for PasswordHistoryRepository."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.security import generate_password_hash
from appkit_user.authentication.backend.database import (
    PasswordHistoryEntity,
    PasswordHistoryRepository,
)


@pytest.fixture
def password_history_repository() -> PasswordHistoryRepository:
    """Provide PasswordHistoryRepository instance."""
    return PasswordHistoryRepository()


@pytest.fixture
def password_hash_factory() -> Callable[[str], str]:
    """Factory for creating password hashes."""

    def _create_hash(password: str) -> str:  # noqa: S107
        return generate_password_hash(password)

    return _create_hash


class TestPasswordHistoryRepository:
    """Test suite for PasswordHistoryRepository."""

    @pytest.mark.asyncio
    async def test_get_last_n_password_hashes_empty(
        self,
        async_session: AsyncSession,
        password_history_repository: PasswordHistoryRepository,
    ) -> None:
        """get_last_n_password_hashes returns empty list for user with no history."""
        # Act
        result = await password_history_repository.get_last_n_password_hashes(
            async_session, user_id=999, n=6
        )

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_last_n_password_hashes_returns_ordered_by_recent(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """get_last_n_password_hashes returns hashes ordered by most recent."""
        # Arrange
        user = await user_factory()
        old_hash = password_hash_factory("OldPassword123!")
        middle_hash = password_hash_factory("MiddlePassword123!")
        new_hash = password_hash_factory("NewPassword123!")

        # Create entities with different timestamps
        old_entity = PasswordHistoryEntity(
            user_id=user.id,
            password_hash=old_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2),
            change_reason="password_change",
        )
        middle_entity = PasswordHistoryEntity(
            user_id=user.id,
            password_hash=middle_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
            change_reason="password_change",
        )
        new_entity = PasswordHistoryEntity(
            user_id=user.id,
            password_hash=new_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
            change_reason="password_change",
        )

        async_session.add(old_entity)
        async_session.add(middle_entity)
        async_session.add(new_entity)
        await async_session.flush()

        # Act
        result = await password_history_repository.get_last_n_password_hashes(
            async_session, user_id=user.id, n=10
        )

        # Assert
        assert len(result) == 3
        assert result[0] == new_hash  # Most recent first
        assert result[1] == middle_hash
        assert result[2] == old_hash  # Oldest last

    @pytest.mark.asyncio
    async def test_get_last_n_password_hashes_respects_limit(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """get_last_n_password_hashes respects the n parameter."""
        # Arrange
        user = await user_factory()
        hashes = [password_hash_factory(f"Password{i}123!") for i in range(10)]

        for i, hash_val in enumerate(hashes):
            entity = PasswordHistoryEntity(
                user_id=user.id,
                password_hash=hash_val,
                changed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=i),
                change_reason="password_change",
            )
            async_session.add(entity)
        await async_session.flush()

        # Act
        result = await password_history_repository.get_last_n_password_hashes(
            async_session, user_id=user.id, n=3
        )

        # Assert
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_check_password_reuse_detects_reuse(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """check_password_reuse returns True when password was previously used."""
        # Arrange
        user = await user_factory()
        old_password = "OldPassword123!"  # noqa: S105
        old_hash = password_hash_factory(old_password)

        entity = PasswordHistoryEntity(
            user_id=user.id,
            password_hash=old_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
            change_reason="password_change",
        )
        async_session.add(entity)
        await async_session.flush()

        # Act
        result = await password_history_repository.check_password_reuse(
            async_session, user_id=user.id, new_password=old_password, n=6
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_password_reuse_no_reuse(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """check_password_reuse returns False when password is new."""
        # Arrange
        user = await user_factory()
        old_hash = password_hash_factory("OldPassword123!")

        entity = PasswordHistoryEntity(
            user_id=user.id,
            password_hash=old_hash,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
            change_reason="password_change",
        )
        async_session.add(entity)
        await async_session.flush()

        # Act
        result = await password_history_repository.check_password_reuse(
            async_session, user_id=user.id, new_password="BrandNewPassword456!", n=6
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_password_reuse_respects_limit(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """check_password_reuse only checks N most recent passwords."""
        # Arrange
        user = await user_factory()
        # Create 10 passwords in history
        passwords = [f"Password{i}123!" for i in range(10)]
        hashes = [password_hash_factory(pwd) for pwd in passwords]

        for i, hash_val in enumerate(hashes):
            entity = PasswordHistoryEntity(
                user_id=user.id,
                password_hash=hash_val,
                changed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=i),
                change_reason="password_change",
            )
            async_session.add(entity)
        await async_session.flush()

        # Act - Check only last 3 passwords
        # Most recent 3 are: Password0 (0 days), Password1 (1 day), Password2 (2 days)
        result = await password_history_repository.check_password_reuse(
            async_session, user_id=user.id, new_password="Password1123!", n=3
        )

        # Assert - Password1 is the second most recent (within last 3)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_password_reuse_beyond_limit_not_checked(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """check_password_reuse doesn't check passwords beyond N limit."""
        # Arrange
        user = await user_factory()
        # Create 10 passwords
        passwords = [f"Password{i}123!" for i in range(10)]
        hashes = [password_hash_factory(pwd) for pwd in passwords]

        for i, hash_val in enumerate(hashes):
            entity = PasswordHistoryEntity(
                user_id=user.id,
                password_hash=hash_val,
                changed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=i),
                change_reason="password_change",
            )
            async_session.add(entity)
        await async_session.flush()

        # Act - Check only last 3 passwords, but try oldest password
        # Most recent 3 are: Password0 (0 days), Password1 (1 day), Password2 (2 days)
        # Password9 is oldest (9 days), so should NOT be found
        result = await password_history_repository.check_password_reuse(
            async_session, user_id=user.id, new_password="Password9123!", n=3
        )

        # Assert - Should not detect reuse since it's beyond our limit
        assert result is False

    @pytest.mark.asyncio
    async def test_check_password_reuse_empty_history(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
    ) -> None:
        """check_password_reuse returns False for user with no history."""
        # Arrange
        user = await user_factory()

        # Act
        result = await password_history_repository.check_password_reuse(
            async_session, user_id=user.id, new_password="AnyPassword123!", n=6
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_save_password_to_history_creates_entity(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """save_password_to_history creates a new password history entity."""
        # Arrange
        user = await user_factory()
        password_hash = password_hash_factory("NewPassword123!")

        # Act
        entity = await password_history_repository.save_password_to_history(
            async_session,
            user_id=user.id,
            password_hash=password_hash,
            change_reason="password_change",
        )

        # Assert
        assert entity.id is not None
        assert entity.user_id == user.id
        assert entity.password_hash == password_hash
        assert entity.change_reason == "password_change"
        assert entity.changed_at is not None

    @pytest.mark.asyncio
    async def test_save_password_to_history_sets_timestamp(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """save_password_to_history sets changed_at timestamp."""
        # Arrange
        user = await user_factory()
        password_hash = password_hash_factory("AnotherPassword123!")
        before = datetime.now(UTC)

        # Act
        entity = await password_history_repository.save_password_to_history(
            async_session,
            user_id=user.id,
            password_hash=password_hash,
            change_reason="admin_reset",
        )

        # Assert
        after = datetime.now(UTC)
        # Naive comparison since changed_at is stored as naive
        entity_time = entity.changed_at.replace(tzinfo=UTC)
        assert before <= entity_time <= after

    @pytest.mark.asyncio
    async def test_save_password_to_history_multiple_reasons(
        self,
        async_session: AsyncSession,
        user_factory,
        password_history_repository: PasswordHistoryRepository,
        password_hash_factory,
    ) -> None:
        """save_password_to_history stores different change reasons."""
        # Arrange
        user = await user_factory()

        # Act
        entity1 = await password_history_repository.save_password_to_history(
            async_session,
            user_id=user.id,
            password_hash=password_hash_factory("Pass1123!"),
            change_reason="password_change",
        )
        entity2 = await password_history_repository.save_password_to_history(
            async_session,
            user_id=user.id,
            password_hash=password_hash_factory("Pass2123!"),
            change_reason="admin_reset",
        )

        # Assert
        assert entity1.change_reason == "password_change"
        assert entity2.change_reason == "admin_reset"

    @pytest.mark.asyncio
    async def test_model_class_property(
        self, password_history_repository: PasswordHistoryRepository
    ) -> None:
        """model_class property returns PasswordHistoryEntity."""
        # Act
        model_class = password_history_repository.model_class

        # Assert
        assert model_class == PasswordHistoryEntity

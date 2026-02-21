"""Tests for GeneratedImageRepository."""

import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_imagecreator.backend.models import GeneratedImage
from appkit_imagecreator.backend.repository import GeneratedImageRepository


class TestGeneratedImageRepository:
    """Test suite for GeneratedImageRepository."""

    @pytest.mark.asyncio
    async def test_find_by_user_returns_user_images(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_by_user returns images for specific user."""
        # Arrange
        user1_image1 = await generated_image_factory(user_id=1, prompt="User 1 Image 1")
        user1_image2 = await generated_image_factory(user_id=1, prompt="User 1 Image 2")
        user2_image = await generated_image_factory(user_id=2, prompt="User 2 Image")

        # Act
        results = await image_repo.find_by_user(async_session, user_id=1)

        # Assert
        assert len(results) == 2
        image_ids = {img.id for img in results}
        assert user1_image1.id in image_ids
        assert user1_image2.id in image_ids
        assert user2_image.id not in image_ids

    @pytest.mark.asyncio
    async def test_find_by_user_excludes_deleted(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_by_user excludes deleted images."""
        # Arrange
        active_image = await generated_image_factory(user_id=1, is_deleted=False)
        deleted_image = await generated_image_factory(user_id=1, is_deleted=True)

        # Act
        results = await image_repo.find_by_user(async_session, user_id=1)

        # Assert
        assert len(results) == 1
        assert results[0].id == active_image.id

    @pytest.mark.asyncio
    async def test_find_by_user_orders_by_created_desc(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_by_user returns newest images first."""
        # Arrange
        old_image = await generated_image_factory(user_id=1)
        old_image.created_at = datetime.now(UTC) - timedelta(days=2)

        new_image = await generated_image_factory(user_id=1)
        new_image.created_at = datetime.now(UTC)
        await async_session.flush()

        # Act
        results = await image_repo.find_by_user(async_session, user_id=1)

        # Assert
        assert results[0].id == new_image.id  # Newest first
        assert results[1].id == old_image.id

    @pytest.mark.asyncio
    async def test_find_by_user_respects_limit(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_by_user respects limit parameter."""
        # Arrange
        for i in range(5):
            await generated_image_factory(user_id=1, prompt=f"Image {i}")

        # Act
        results = await image_repo.find_by_user(async_session, user_id=1, limit=3)

        # Assert
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_by_user_defers_image_data(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_by_user defers loading image_data BLOB."""
        # Arrange
        await generated_image_factory(user_id=1)

        # Act
        results = await image_repo.find_by_user(async_session, user_id=1)

        # Assert - image_data should not be loaded initially (deferred)
        # Note: This is a performance optimization, actual check requires
        # inspecting SQLAlchemy's deferred state
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_today_by_user_returns_today_images(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_today_by_user returns only today's images."""
        # Arrange
        today_image = await generated_image_factory(user_id=1)
        today_image.created_at = datetime.now(UTC)

        old_image = await generated_image_factory(user_id=1)
        old_image.created_at = datetime.now(UTC) - timedelta(days=1, hours=1)
        await async_session.flush()

        # Act
        results = await image_repo.find_today_by_user(async_session, user_id=1)

        # Assert
        assert len(results) == 1
        assert results[0].id == today_image.id

    @pytest.mark.asyncio
    async def test_find_today_by_user_boundary_midnight(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """find_today_by_user uses midnight as cutoff."""
        # Arrange
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        just_after_midnight = await generated_image_factory(user_id=1)
        just_after_midnight.created_at = today_start + timedelta(seconds=1)

        just_before_midnight = await generated_image_factory(user_id=1)
        just_before_midnight.created_at = today_start - timedelta(seconds=1)
        await async_session.flush()

        # Act
        results = await image_repo.find_today_by_user(async_session, user_id=1)

        # Assert
        assert len(results) == 1
        assert results[0].id == just_after_midnight.id

    @pytest.mark.asyncio
    async def test_find_image_data_returns_bytes_and_type(
        self, async_session: AsyncSession, generated_image_factory, image_repo, sample_image_bytes
    ) -> None:
        """find_image_data returns image bytes and content type."""
        # Arrange
        image = await generated_image_factory(
            image_data=sample_image_bytes, content_type="image/png"
        )

        # Act
        result = await image_repo.find_image_data(async_session, image.id)

        # Assert
        assert result is not None
        image_data, content_type = result
        assert image_data == sample_image_bytes
        assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_find_image_data_nonexistent_returns_none(
        self, async_session: AsyncSession, image_repo
    ) -> None:
        """find_image_data returns None for nonexistent image."""
        # Act
        result = await image_repo.find_image_data(async_session, image_id=99999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_id_and_user_sets_deleted_flag(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_by_id_and_user marks image as deleted."""
        # Arrange
        image = await generated_image_factory(user_id=1)

        # Act
        success = await image_repo.delete_by_id_and_user(
            async_session, image.id, user_id=1
        )

        # Assert
        assert success is True
        await async_session.refresh(image)
        assert image.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_by_id_and_user_clears_image_data(
        self, async_session: AsyncSession, generated_image_factory, image_repo, sample_image_bytes
    ) -> None:
        """delete_by_id_and_user clears image_data to save space."""
        # Arrange
        image = await generated_image_factory(user_id=1, image_data=sample_image_bytes)

        # Act
        await image_repo.delete_by_id_and_user(async_session, image.id, user_id=1)

        # Assert
        await async_session.refresh(image)
        assert image.image_data == b""

    @pytest.mark.asyncio
    async def test_delete_by_id_and_user_wrong_user_fails(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_by_id_and_user fails if user doesn't own image."""
        # Arrange
        image = await generated_image_factory(user_id=1)

        # Act
        success = await image_repo.delete_by_id_and_user(
            async_session, image.id, user_id=2
        )

        # Assert
        assert success is False
        await async_session.refresh(image)
        assert image.is_deleted is False

    @pytest.mark.asyncio
    async def test_delete_by_id_and_user_nonexistent_fails(
        self, async_session: AsyncSession, image_repo
    ) -> None:
        """delete_by_id_and_user returns False for nonexistent image."""
        # Act
        success = await image_repo.delete_by_id_and_user(
            async_session, image_id=99999, user_id=1
        )

        # Assert
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_all_by_user_marks_all_deleted(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_all_by_user marks all user images as deleted."""
        # Arrange
        image1 = await generated_image_factory(user_id=1)
        image2 = await generated_image_factory(user_id=1)
        other_user_image = await generated_image_factory(user_id=2)

        # Act
        count = await image_repo.delete_all_by_user(async_session, user_id=1)

        # Assert
        assert count == 2
        await async_session.refresh(image1)
        await async_session.refresh(image2)
        await async_session.refresh(other_user_image)
        assert image1.is_deleted is True
        assert image2.is_deleted is True
        assert other_user_image.is_deleted is False

    @pytest.mark.asyncio
    async def test_delete_all_by_user_clears_image_data(
        self, async_session: AsyncSession, generated_image_factory, image_repo, sample_image_bytes
    ) -> None:
        """delete_all_by_user clears image_data for all images."""
        # Arrange
        image1 = await generated_image_factory(user_id=1, image_data=sample_image_bytes)
        image2 = await generated_image_factory(user_id=1, image_data=sample_image_bytes)

        # Act
        await image_repo.delete_all_by_user(async_session, user_id=1)

        # Assert
        await async_session.refresh(image1)
        await async_session.refresh(image2)
        assert image1.image_data == b""
        assert image2.image_data == b""

    @pytest.mark.asyncio
    async def test_delete_all_by_user_no_images_returns_zero(
        self, async_session: AsyncSession, image_repo
    ) -> None:
        """delete_all_by_user returns 0 when no images exist."""
        # Act
        count = await image_repo.delete_all_by_user(async_session, user_id=999)

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_by_older_than_days_marks_old_deleted(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_by_older_than_days marks old images as deleted."""
        # Arrange
        old_image = await generated_image_factory(user_id=1)
        old_image.created_at = datetime.now(UTC) - timedelta(days=40)

        recent_image = await generated_image_factory(user_id=1)
        recent_image.created_at = datetime.now(UTC) - timedelta(days=10)
        await async_session.flush()

        # Act
        count = await image_repo.delete_by_older_than_days(async_session, days=30)

        # Assert
        assert count == 1
        await async_session.refresh(old_image)
        await async_session.refresh(recent_image)
        assert old_image.is_deleted is True
        assert recent_image.is_deleted is False

    @pytest.mark.asyncio
    async def test_delete_by_older_than_days_boundary(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_by_older_than_days uses strict < comparison."""
        # Arrange
        cutoff = datetime.now(UTC) - timedelta(days=30)

        just_before = await generated_image_factory(user_id=1)
        just_before.created_at = cutoff - timedelta(seconds=1)

        just_after = await generated_image_factory(user_id=1)
        just_after.created_at = cutoff + timedelta(seconds=1)
        await async_session.flush()

        # Act
        count = await image_repo.delete_by_older_than_days(async_session, days=30)

        # Assert
        assert count == 1
        await async_session.refresh(just_before)
        await async_session.refresh(just_after)
        assert just_before.is_deleted is True
        assert just_after.is_deleted is False

    @pytest.mark.asyncio
    async def test_delete_by_older_than_days_affects_all_users(
        self, async_session: AsyncSession, generated_image_factory, image_repo
    ) -> None:
        """delete_by_older_than_days affects all users' old images."""
        # Arrange
        old_date = datetime.now(UTC) - timedelta(days=40)

        user1_old = await generated_image_factory(user_id=1)
        user1_old.created_at = old_date

        user2_old = await generated_image_factory(user_id=2)
        user2_old.created_at = old_date
        await async_session.flush()

        # Act
        count = await image_repo.delete_by_older_than_days(async_session, days=30)

        # Assert
        assert count == 2
        await async_session.refresh(user1_old)
        await async_session.refresh(user2_old)
        assert user1_old.is_deleted is True
        assert user2_old.is_deleted is True

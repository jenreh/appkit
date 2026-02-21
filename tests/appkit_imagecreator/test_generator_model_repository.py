"""Tests for ImageGeneratorModelRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_imagecreator.backend.models import ImageGeneratorModel
from appkit_imagecreator.backend.generator_repository import (
    ImageGeneratorModelRepository,
)


class TestImageGeneratorModelRepository:
    """Test suite for ImageGeneratorModelRepository."""

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_name(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_all_ordered_by_name returns all models sorted by label."""
        # Arrange
        model_b = await image_generator_model_factory(label="B Model")
        model_a = await image_generator_model_factory(label="A Model")
        model_c = await image_generator_model_factory(label="C Model")

        # Act
        results = await generator_model_repo.find_all_ordered_by_name(async_session)

        # Assert
        assert len(results) == 3
        assert results[0].id == model_a.id  # A first
        assert results[1].id == model_b.id  # B second
        assert results[2].id == model_c.id  # C third

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_name_includes_inactive(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_all_ordered_by_name includes inactive models."""
        # Arrange
        active_model = await image_generator_model_factory(active=True)
        inactive_model = await image_generator_model_factory(active=False)

        # Act
        results = await generator_model_repo.find_all_ordered_by_name(async_session)

        # Assert
        assert len(results) == 2
        model_ids = {m.id for m in results}
        assert active_model.id in model_ids
        assert inactive_model.id in model_ids

    @pytest.mark.asyncio
    async def test_find_all_active(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_all_active returns only active models."""
        # Arrange
        active1 = await image_generator_model_factory(label="Active 1", active=True)
        active2 = await image_generator_model_factory(label="Active 2", active=True)
        inactive = await image_generator_model_factory(label="Inactive", active=False)

        # Act
        results = await generator_model_repo.find_all_active(async_session)

        # Assert
        assert len(results) == 2
        model_ids = {m.id for m in results}
        assert active1.id in model_ids
        assert active2.id in model_ids
        assert inactive.id not in model_ids

    @pytest.mark.asyncio
    async def test_find_all_active_ordered_by_label(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_all_active returns results sorted by label."""
        # Arrange
        model_z = await image_generator_model_factory(label="Z Model", active=True)
        model_a = await image_generator_model_factory(label="A Model", active=True)

        # Act
        results = await generator_model_repo.find_all_active(async_session)

        # Assert
        assert results[0].id == model_a.id  # A first
        assert results[1].id == model_z.id  # Z second

    @pytest.mark.asyncio
    async def test_find_by_model_id_existing(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_by_model_id returns model by model_id string."""
        # Arrange
        model = await image_generator_model_factory(model_id="unique-model-id")

        # Act
        result = await generator_model_repo.find_by_model_id(
            async_session, "unique-model-id"
        )

        # Assert
        assert result is not None
        assert result.id == model.id
        assert result.model_id == "unique-model-id"

    @pytest.mark.asyncio
    async def test_find_by_model_id_nonexistent(
        self, async_session: AsyncSession, generator_model_repo
    ) -> None:
        """find_by_model_id returns None for nonexistent model_id."""
        # Act
        result = await generator_model_repo.find_by_model_id(
            async_session, "nonexistent-id"
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_model_id_case_sensitive(
        self, async_session: AsyncSession, image_generator_model_factory, generator_model_repo
    ) -> None:
        """find_by_model_id is case-sensitive."""
        # Arrange
        await image_generator_model_factory(model_id="lowercase-id")

        # Act
        result = await generator_model_repo.find_by_model_id(
            async_session, "LOWERCASE-ID"
        )

        # Assert
        assert result is None  # Case mismatch

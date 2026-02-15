"""Repository for generated images database operations."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from appkit_commons.database.base_repository import BaseRepository
from appkit_imagecreator.backend.models import GeneratedImage

logger = logging.getLogger(__name__)


class GeneratedImageRepository(BaseRepository[GeneratedImage, AsyncSession]):
    """Repository class for generated image database operations."""

    @property
    def model_class(self) -> type[GeneratedImage]:
        return GeneratedImage

    async def find_by_user(
        self, session: AsyncSession, user_id: int, limit: int = 100
    ) -> list[GeneratedImage]:
        """Retrieve all generated images for a user (excluding deleted)."""
        # Defer loading of image_data to avoid fetching large blobs
        stmt = (
            select(GeneratedImage)
            .options(defer(GeneratedImage.image_data))
            .where(
                GeneratedImage.user_id == user_id,
                ~GeneratedImage.is_deleted,
            )
            .order_by(GeneratedImage.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_today_by_user(
        self, session: AsyncSession, user_id: int, limit: int = 100
    ) -> list[GeneratedImage]:
        """Retrieve today's generated images for a user (excluding deleted)."""
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(GeneratedImage)
            .options(defer(GeneratedImage.image_data))
            .where(
                GeneratedImage.user_id == user_id,
                GeneratedImage.created_at >= today_start,
                ~GeneratedImage.is_deleted,
            )
            .order_by(GeneratedImage.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_image_data(
        self, session: AsyncSession, image_id: int
    ) -> tuple[bytes, str] | None:
        """Retrieve only the image data and content type for an image."""
        stmt = select(GeneratedImage).where(GeneratedImage.id == image_id)
        result = await session.execute(stmt)
        image = result.scalars().first()
        if image:
            return image.image_data, image.content_type
        return None

    async def delete_by_id_and_user(
        self, session: AsyncSession, image_id: int, user_id: int
    ) -> bool:
        """Mark a generated image as deleted by ID (only if owned by user).

        Sets is_deleted flag while keeping the database record intact.
        """
        stmt = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == user_id,
        )
        result = await session.execute(stmt)
        image = result.scalars().first()
        if image:
            image.is_deleted = True
            image.image_data = b""  # Clear image data to save space
            await session.flush()
            logger.debug("Marked image as deleted: %s", image_id)
            return True
        logger.warning(
            "Generated image with ID %s not found for user %s",
            image_id,
            user_id,
        )
        return False

    async def delete_all_by_user(self, session: AsyncSession, user_id: int) -> int:
        """Mark all generated images for a user as deleted.

        Sets is_deleted flag while keeping database records intact.
        Returns count of images updated.
        """
        stmt = select(GeneratedImage).where(GeneratedImage.user_id == user_id)
        result = await session.execute(stmt)
        images = list(result.scalars().all())
        for image in images:
            image.is_deleted = True
            image.image_data = b""  # Clear image data to save space
        await session.flush()
        count = len(images)
        logger.debug(
            "Marked %d generated images as deleted for user %s", count, user_id
        )
        return count

    async def delete_by_older_than_days(self, session: AsyncSession, days: int) -> int:
        """Mark all generated images older than x days as deleted.

        Sets is_deleted flag for images created before the cutoff date.
        Returns count of images updated.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        stmt = select(GeneratedImage).where(
            GeneratedImage.created_at < cutoff_date,
        )
        result = await session.execute(stmt)
        images = list(result.scalars().all())
        for image in images:
            image.is_deleted = True
            image.image_data = b""  # Clear image data to save space
        await session.flush()
        count = len(images)
        logger.debug(
            "Marked %d generated images older than %d days as deleted",
            count,
            days,
        )
        return count


image_repo = GeneratedImageRepository()

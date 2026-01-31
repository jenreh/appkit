"""Repository for generated images database operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
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
        """Retrieve all generated images for a user (without blob data)."""
        # Defer loading of image_data to avoid fetching large blobs
        stmt = (
            select(GeneratedImage)
            .options(defer(GeneratedImage.image_data))
            .where(GeneratedImage.user_id == user_id)
            .order_by(GeneratedImage.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_today_by_user(
        self, session: AsyncSession, user_id: int, limit: int = 100
    ) -> list[GeneratedImage]:
        """Retrieve today's generated images for a user (without blob data)."""
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(GeneratedImage)
            .options(defer(GeneratedImage.image_data))
            .where(
                GeneratedImage.user_id == user_id,
                GeneratedImage.created_at >= today_start,
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
        """Delete a generated image by ID (only if owned by user)."""
        stmt = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == user_id,
        )
        result = await session.execute(stmt)
        image = result.scalars().first()
        if image:
            await session.delete(image)
            await session.flush()
            logger.debug("Deleted generated image: %s", image_id)
            return True
        logger.warning(
            "Generated image with ID %s not found for user %s",
            image_id,
            user_id,
        )
        return False

    async def delete_all_by_user(self, session: AsyncSession, user_id: int) -> int:
        """Delete all generated images for a user. Returns count of deleted images."""
        stmt = delete(GeneratedImage).where(GeneratedImage.user_id == user_id)
        result = await session.execute(stmt)
        await session.flush()
        count = result.rowcount
        logger.debug("Deleted %d generated images for user %s", count, user_id)
        return count


image_repo = GeneratedImageRepository()

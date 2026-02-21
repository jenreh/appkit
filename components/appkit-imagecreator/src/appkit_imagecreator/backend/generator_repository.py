"""Repository for image generator model database operations."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.base_repository import BaseRepository
from appkit_imagecreator.backend.models import ImageGeneratorModel

logger = logging.getLogger(__name__)


class ImageGeneratorModelRepository(BaseRepository[ImageGeneratorModel, AsyncSession]):
    """Repository for image generator model CRUD operations."""

    @property
    def model_class(self) -> type[ImageGeneratorModel]:
        return ImageGeneratorModel

    async def find_all_ordered_by_name(
        self, session: AsyncSession
    ) -> list[ImageGeneratorModel]:
        """Retrieve all generator models ordered by label."""
        stmt = select(ImageGeneratorModel).order_by(ImageGeneratorModel.label)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_all_active(self, session: AsyncSession) -> list[ImageGeneratorModel]:
        """Retrieve all active generator models ordered by label."""
        stmt = (
            select(ImageGeneratorModel)
            .where(ImageGeneratorModel.active == True)  # noqa: E712
            .order_by(ImageGeneratorModel.label)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_model_id(
        self, session: AsyncSession, model_id: str
    ) -> ImageGeneratorModel | None:
        """Find a generator model by its model_id string."""
        stmt = select(ImageGeneratorModel).where(
            ImageGeneratorModel.model_id == model_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()


generator_model_repo = ImageGeneratorModelRepository()

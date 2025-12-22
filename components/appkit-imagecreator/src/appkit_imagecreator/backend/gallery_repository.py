"""Repository for generated images database operations."""

import logging
from datetime import UTC, datetime
from typing import Any

import reflex as rx
from sqlalchemy.orm import defer

from appkit_imagecreator.backend.gallery_models import (
    GeneratedImage,
    GeneratedImageModel,
)

logger = logging.getLogger(__name__)


class GeneratedImageRepository:
    """Repository class for generated image database operations."""

    @staticmethod
    async def get_by_user(user_id: int, limit: int = 100) -> list[GeneratedImageModel]:
        """Retrieve all generated images for a user (without blob data)."""
        async with rx.asession() as session:
            # Defer loading of image_data to avoid fetching large blobs
            result = await session.exec(
                GeneratedImage.select()
                .options(defer(GeneratedImage.image_data))
                .where(GeneratedImage.user_id == user_id)
                .order_by(GeneratedImage.created_at.desc())
                .limit(limit)
            )
            images = result.all()
            return [
                GeneratedImageModel(
                    id=img.id,
                    user_id=img.user_id,
                    prompt=img.prompt,
                    enhanced_prompt=img.enhanced_prompt,
                    style=img.style,
                    model=img.model,
                    content_type=img.content_type,
                    width=img.width,
                    height=img.height,
                    quality=img.quality,
                    config=img.config,
                    created_at=img.created_at,
                )
                for img in images
            ]

    @staticmethod
    async def get_today_by_user(
        user_id: int, limit: int = 100
    ) -> list[GeneratedImageModel]:
        """Retrieve today's generated images for a user (without blob data)."""
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        async with rx.asession() as session:
            result = await session.exec(
                GeneratedImage.select()
                .options(defer(GeneratedImage.image_data))
                .where(
                    GeneratedImage.user_id == user_id,
                    GeneratedImage.created_at >= today_start,
                )
                .order_by(GeneratedImage.created_at.desc())
                .limit(limit)
            )
            images = result.all()
            return [
                GeneratedImageModel(
                    id=img.id,
                    user_id=img.user_id,
                    prompt=img.prompt,
                    enhanced_prompt=img.enhanced_prompt,
                    style=img.style,
                    model=img.model,
                    content_type=img.content_type,
                    width=img.width,
                    height=img.height,
                    quality=img.quality,
                    config=img.config,
                    created_at=img.created_at,
                )
                for img in images
            ]

    @staticmethod
    async def get_by_id(image_id: int) -> GeneratedImage | None:
        """Retrieve a generated image by ID (including blob data)."""
        async with rx.asession() as session:
            result = await session.exec(
                GeneratedImage.select().where(GeneratedImage.id == image_id)
            )
            return result.first()

    @staticmethod
    async def get_image_data(image_id: int) -> tuple[bytes, str] | None:
        """Retrieve only the image data and content type for an image."""
        async with rx.asession() as session:
            result = await session.exec(
                GeneratedImage.select().where(GeneratedImage.id == image_id)
            )
            image = result.first()
            if image:
                return image.image_data, image.content_type
            return None

    @staticmethod
    async def create(
        user_id: int,
        prompt: str,
        model: str,
        image_data: bytes,
        content_type: str,
        width: int,
        height: int,
        enhanced_prompt: str | None = None,
        style: str | None = None,
        quality: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> GeneratedImageModel:
        """Create a new generated image record with blob data."""
        async with rx.asession() as session:
            image = GeneratedImage(
                user_id=user_id,
                prompt=prompt,
                enhanced_prompt=enhanced_prompt,
                style=style,
                model=model,
                image_data=image_data,
                content_type=content_type,
                width=width,
                height=height,
                quality=quality,
                config=config,
            )
            session.add(image)
            await session.commit()
            await session.refresh(image)
            logger.debug("Created generated image for user %s: %s", user_id, image.id)
            return GeneratedImageModel(
                id=image.id,
                user_id=image.user_id,
                prompt=image.prompt,
                enhanced_prompt=image.enhanced_prompt,
                style=image.style,
                model=image.model,
                content_type=image.content_type,
                width=image.width,
                height=image.height,
                quality=image.quality,
                config=image.config,
                created_at=image.created_at,
            )

    @staticmethod
    async def delete(image_id: int, user_id: int) -> bool:
        """Delete a generated image by ID (only if owned by user)."""
        async with rx.asession() as session:
            result = await session.exec(
                GeneratedImage.select().where(
                    GeneratedImage.id == image_id,
                    GeneratedImage.user_id == user_id,
                )
            )
            image = result.first()
            if image:
                await session.delete(image)
                await session.commit()
                logger.debug("Deleted generated image: %s", image_id)
                return True
            logger.warning(
                "Generated image with ID %s not found for user %s",
                image_id,
                user_id,
            )
            return False

    @staticmethod
    async def delete_all_by_user(user_id: int) -> int:
        """Delete all generated images for a user. Returns count of deleted images."""
        async with rx.asession() as session:
            result = await session.exec(
                GeneratedImage.select().where(GeneratedImage.user_id == user_id)
            )
            images = result.all()
            count = len(images)
            for image in images:
                await session.delete(image)
            await session.commit()
            logger.debug("Deleted %d generated images for user %s", count, user_id)
            return count

"""Image cleanup scheduler for deleting old generated images.

Provides scheduled cleanup of generated images older than a configured threshold.
The scheduler runs once daily at 3:00 AM.
"""

import logging

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_commons.scheduler import CronTrigger, ScheduledService, Trigger
from appkit_imagecreator.backend.repository import image_repo
from appkit_imagecreator.configuration import ImageGeneratorConfig

logger = logging.getLogger(__name__)


class ImageCleanupService(ScheduledService):
    """Service to clean up old generated images."""

    job_id = "image_cleanup"
    name = "Clean up old generated images"

    def __init__(self, config: ImageGeneratorConfig = None) -> None:
        """Initialize the cleanup service."""
        self.config = config or service_registry().get(ImageGeneratorConfig)

    @property
    def trigger(self) -> Trigger:
        """Run daily at 3:07 AM UTC."""
        return CronTrigger(hour=3, minute=7)

    async def execute(self) -> None:
        """Run the image cleanup job."""
        try:
            config = self.config
            logger.info(
                "Running image cleanup job (threshold: %d days)",
                config.cleanup_days_threshold,
            )
            async with get_asyncdb_session() as session:
                count = await image_repo.delete_by_user_older_than_days(
                    session, config.cleanup_days_threshold
                )
                if count > 0:
                    logger.info(
                        "Marked %d generated images as deleted (older than %d days)",
                        count,
                        config.cleanup_days_threshold,
                    )
                else:
                    logger.debug(
                        "No images older than %d days found for cleanup",
                        config.cleanup_days_threshold,
                    )
        except Exception as e:
            logger.error("Image cleanup job failed: %s", e)

"""Tests for ImageCleanupService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_imagecreator.backend.services.image_cleanup_service import (
    ImageCleanupService,
)
from appkit_imagecreator.configuration import ImageGeneratorConfig
from appkit_commons.scheduler import CronTrigger


class TestImageCleanupService:
    """Test suite for ImageCleanupService."""

    def test_initialization_default_config(self) -> None:
        """ImageCleanupService initializes with default config."""
        # Arrange
        mock_config = ImageGeneratorConfig(cleanup_days_threshold=30)

        with patch("appkit_imagecreator.backend.services.image_cleanup_service.service_registry") as mock_registry:
            mock_registry.return_value.get.return_value = mock_config

            # Act
            service = ImageCleanupService()

            # Assert
            assert service.config == mock_config
            assert service.job_id == "image_cleanup"
            assert service.name == "Clean up old generated images"

    def test_initialization_custom_config(self) -> None:
        """ImageCleanupService accepts custom config."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=60)

        # Act
        service = ImageCleanupService(config=config)

        # Assert
        assert service.config == config
        assert service.config.cleanup_days_threshold == 60

    def test_trigger_returns_cron_trigger(self) -> None:
        """trigger property returns CronTrigger for 3:07 AM."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        # Act
        trigger = service.trigger

        # Assert
        assert isinstance(trigger, CronTrigger)
        assert trigger.hour == 3
        assert trigger.minute == 7

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    async def test_execute_calls_repository(
        self, mock_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute calls image_repo.delete_by_older_than_days."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Note: The service calls delete_by_user_older_than_days but
        # the repository method is delete_by_older_than_days
        mock_repo.delete_by_older_than_days = AsyncMock(return_value=5)

        # Act
        await service.execute()

        # Assert
        mock_repo.delete_by_older_than_days.assert_called_once_with(mock_session, 30)

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.logger")
    async def test_execute_logs_cleanup_count(
        self,
        mock_logger: MagicMock,
        mock_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute logs number of cleaned images."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_repo.delete_by_older_than_days = AsyncMock(return_value=10)

        # Act
        await service.execute()

        # Assert
        mock_logger.info.assert_any_call(
            "Running image cleanup job (threshold: %d days)", 30
        )
        mock_logger.info.assert_any_call(
            "Marked %d generated images as deleted (older than %d days)",
            10,
            30,
        )

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.logger")
    async def test_execute_logs_debug_when_no_images(
        self,
        mock_logger: MagicMock,
        mock_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute logs debug message when no images deleted."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_repo.delete_by_older_than_days = AsyncMock(return_value=0)

        # Act
        await service.execute()

        # Assert
        mock_logger.debug.assert_called_once_with(
            "No images older than %d days found for cleanup", 30
        )

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.logger")
    async def test_execute_handles_exceptions(
        self,
        mock_logger: MagicMock,
        mock_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute catches and logs exceptions."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        error = Exception("Database connection failed")
        mock_repo.delete_by_older_than_days = AsyncMock(side_effect=error)

        # Act - should not raise
        await service.execute()

        # Assert
        mock_logger.error.assert_called_once_with(
            "Image cleanup job failed: %s", error
        )

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    async def test_execute_uses_config_threshold(
        self, mock_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute uses cleanup_days_threshold from config."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=90)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_repo.delete_by_older_than_days = AsyncMock(return_value=0)

        # Act
        await service.execute()

        # Assert
        mock_repo.delete_by_older_than_days.assert_called_once_with(mock_session, 90)

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.get_asyncdb_session")
    @patch("appkit_imagecreator.backend.services.image_cleanup_service.image_repo")
    async def test_execute_session_context_manager(
        self, mock_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute properly uses session context manager."""
        # Arrange
        config = ImageGeneratorConfig(cleanup_days_threshold=30)
        service = ImageCleanupService(config=config)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_context
        mock_repo.delete_by_older_than_days = AsyncMock(return_value=3)

        # Act
        await service.execute()

        # Assert
        mock_context.__aenter__.assert_called_once()
        mock_context.__aexit__.assert_called_once()

    def test_job_id_is_constant(self) -> None:
        """job_id is a constant class attribute."""
        # Arrange
        config1 = ImageGeneratorConfig(cleanup_days_threshold=30)
        config2 = ImageGeneratorConfig(cleanup_days_threshold=60)

        # Act
        service1 = ImageCleanupService(config=config1)
        service2 = ImageCleanupService(config=config2)

        # Assert
        assert service1.job_id == service2.job_id == "image_cleanup"

    def test_name_is_constant(self) -> None:
        """name is a constant class attribute."""
        # Arrange
        config1 = ImageGeneratorConfig(cleanup_days_threshold=30)
        config2 = ImageGeneratorConfig(cleanup_days_threshold=60)

        # Act
        service1 = ImageCleanupService(config=config1)
        service2 = ImageCleanupService(config=config2)

        # Assert
        assert (
            service1.name
            == service2.name
            == "Clean up old generated images"
        )

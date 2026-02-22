"""Tests for SessionCleanupService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.scheduler import IntervalTrigger
from appkit_user.authentication.backend.services import (
    SessionCleanupService,
)


class TestSessionCleanupService:
    """Test suite for SessionCleanupService."""

    def test_initialization_default_interval(self) -> None:
        """SessionCleanupService initializes with default interval."""
        # Act
        service = SessionCleanupService()

        # Assert
        assert service.interval_minutes == 30
        assert service.job_id == "session_cleanup"
        assert service.name == "Clean up expired user sessions"

    def test_initialization_custom_interval(self) -> None:
        """SessionCleanupService initializes with custom interval."""
        # Act
        service = SessionCleanupService(interval_minutes=15)

        # Assert
        assert service.interval_minutes == 15

    def test_trigger_returns_interval_trigger(self) -> None:
        """trigger property returns IntervalTrigger with correct interval."""
        # Arrange
        service = SessionCleanupService(interval_minutes=45)

        # Act
        trigger = service.trigger

        # Assert
        assert isinstance(trigger, IntervalTrigger)
        # IntervalTrigger stores interval as a timedelta
        assert trigger.interval.total_seconds() == 45 * 60  # 45 minutes in seconds

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    async def test_execute_cleans_expired_sessions(
        self, mock_session_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute calls delete_expired on session repository."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session_repo.delete_expired = AsyncMock(return_value=5)

        service = SessionCleanupService()

        # Act
        await service.execute()

        # Assert
        mock_session_repo.delete_expired.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    @patch("appkit_user.authentication.backend.services.session_cleanup_service.logger")
    async def test_execute_logs_cleanup_count(
        self,
        mock_logger: MagicMock,
        mock_session_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute logs number of cleaned sessions."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session_repo.delete_expired = AsyncMock(return_value=10)

        service = SessionCleanupService()

        # Act
        await service.execute()

        # Assert
        mock_logger.info.assert_any_call("Running session cleanup job")
        mock_logger.info.assert_any_call("Cleaned up %d expired user sessions", 10)

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    @patch("appkit_user.authentication.backend.services.session_cleanup_service.logger")
    async def test_execute_does_not_log_when_no_sessions_cleaned(
        self,
        mock_logger: MagicMock,
        mock_session_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute does not log cleanup count when zero sessions deleted."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session_repo.delete_expired = AsyncMock(return_value=0)

        service = SessionCleanupService()

        # Act
        await service.execute()

        # Assert
        mock_logger.info.assert_called_once_with("Running session cleanup job")
        # Should not log "Cleaned up X sessions" when count is 0

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    @patch("appkit_user.authentication.backend.services.session_cleanup_service.logger")
    async def test_execute_handles_exceptions(
        self,
        mock_logger: MagicMock,
        mock_session_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute catches and logs exceptions."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        error = Exception("Database connection failed")
        mock_session_repo.delete_expired = AsyncMock(side_effect=error)

        service = SessionCleanupService()

        # Act - should not raise
        await service.execute()

        # Assert
        mock_logger.error.assert_called_once_with("Session cleanup failed: %s", error)

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    async def test_execute_session_context_manager(
        self, mock_session_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute properly uses session context manager."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_context
        mock_session_repo.delete_expired = AsyncMock(return_value=3)

        service = SessionCleanupService()

        # Act
        await service.execute()

        # Assert
        mock_context.__aenter__.assert_called_once()
        mock_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    async def test_execute_multiple_calls(
        self, mock_session_repo: MagicMock, mock_get_session: MagicMock
    ) -> None:
        """execute can be called multiple times."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session_repo.delete_expired = AsyncMock(side_effect=[5, 3, 0])

        service = SessionCleanupService()

        # Act
        await service.execute()
        await service.execute()
        await service.execute()

        # Assert
        assert mock_session_repo.delete_expired.call_count == 3

    def test_job_id_is_constant(self) -> None:
        """job_id is a constant class attribute."""
        # Act
        service1 = SessionCleanupService(interval_minutes=10)
        service2 = SessionCleanupService(interval_minutes=20)

        # Assert
        assert service1.job_id == service2.job_id == "session_cleanup"

    def test_name_is_constant(self) -> None:
        """name is a constant class attribute."""
        # Act
        service1 = SessionCleanupService(interval_minutes=10)
        service2 = SessionCleanupService(interval_minutes=20)

        # Assert
        assert service1.name == service2.name == "Clean up expired user sessions"

    def test_trigger_changes_with_interval(self) -> None:
        """trigger interval changes based on initialization parameter."""
        # Arrange
        service1 = SessionCleanupService(interval_minutes=10)
        service2 = SessionCleanupService(interval_minutes=60)

        # Act
        trigger1 = service1.trigger
        trigger2 = service2.trigger

        # Assert
        assert trigger1.interval.total_seconds() == 10 * 60  # 10 minutes in seconds
        assert trigger2.interval.total_seconds() == 60 * 60  # 60 minutes in seconds

    @pytest.mark.asyncio
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
    )
    @patch(
        "appkit_user.authentication.backend.services.session_cleanup_service.session_repo"
    )
    @patch("appkit_user.authentication.backend.services.session_cleanup_service.logger")
    async def test_execute_logs_with_proper_format(
        self,
        mock_logger: MagicMock,
        mock_session_repo: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """execute uses parameterized logging (not f-strings)."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session_repo.delete_expired = AsyncMock(return_value=7)

        service = SessionCleanupService()

        # Act
        await service.execute()

        # Assert - Verify logger.info was called with % formatting
        assert mock_logger.info.call_count == 2
        # Check second call (cleanup count log)
        call_args = mock_logger.info.call_args_list[1]
        assert call_args[0][0] == "Cleaned up %d expired user sessions"
        assert call_args[0][1] == 7

    @pytest.mark.asyncio
    async def test_execute_integration_with_real_session(
        self, async_session: AsyncSession, session_factory
    ) -> None:
        """execute performs actual cleanup with real session (integration test)."""
        # Arrange
        expired_time = datetime.now(UTC) - timedelta(hours=1)
        valid_time = datetime.now(UTC) + timedelta(hours=1)

        await session_factory(session_id="expired_1", expires_at=expired_time)
        await session_factory(session_id="expired_2", expires_at=expired_time)
        await session_factory(session_id="valid", expires_at=valid_time)

        # Mock get_asyncdb_session to return our test session
        with patch(
            "appkit_user.authentication.backend.services.session_cleanup_service.get_asyncdb_session"
        ) as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=async_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            service = SessionCleanupService()

            # Act
            await service.execute()

        # Assert - verify expired sessions were deleted
        from appkit_user.authentication.backend.user_session_repository import (
            session_repo,
        )

        found_expired1 = await session_repo.find_by_session_id(
            async_session, "expired_1"
        )
        found_expired2 = await session_repo.find_by_session_id(
            async_session, "expired_2"
        )
        found_valid = await session_repo.find_by_session_id(async_session, "valid")

        assert found_expired1 is None
        assert found_expired2 is None
        assert found_valid is not None

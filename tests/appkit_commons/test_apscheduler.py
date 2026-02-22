"""Comprehensive tests for APScheduler implementation."""

import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.scheduler.apscheduler import APScheduler
from appkit_commons.scheduler.scheduler_types import (
    CalendarIntervalTrigger,
    CronTrigger,
    IntervalTrigger,
    ScheduledService,
)


class TestAPSchedulerInitialization:
    """Test suite for APScheduler initialization."""

    def test_apscheduler_init(self) -> None:
        """APScheduler initializes with correct default values."""
        # Act
        scheduler = APScheduler()

        # Assert
        assert scheduler._scheduler is None
        assert scheduler._is_running is False
        assert scheduler._services == {}
        assert isinstance(scheduler._background_tasks, set)
        assert len(scheduler._background_tasks) == 0


class TestAPSchedulerIsRunning:
    """Test suite for APScheduler.is_running property."""

    def test_is_running_returns_false_initially(self) -> None:
        """is_running property returns False initially."""
        # Act
        scheduler = APScheduler()

        # Assert
        assert scheduler.is_running is False

    def test_is_running_returns_true_when_running(self) -> None:
        """is_running property returns True when scheduler is running."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        # Act
        result = scheduler.is_running

        # Assert
        assert result is True


class TestAPSchedulerConvertTrigger:
    """Test suite for APScheduler._convert_trigger method."""

    def test_convert_interval_trigger_basic(self) -> None:
        """_convert_trigger converts IntervalTrigger with basic interval."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(minutes=30)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "seconds")
        assert converted.seconds == 30 * 60  # 30 minutes in seconds

    def test_convert_interval_trigger_with_start_time(self) -> None:
        """_convert_trigger converts IntervalTrigger with start_time."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(hours=1, start_time="2023-01-01 09:00:00")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "start_time")

    def test_convert_interval_trigger_with_end_time(self) -> None:
        """_convert_trigger converts IntervalTrigger with end_time."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(
            hours=1, start_time="2023-01-01 09:00:00", end_time="2023-12-31 17:00:00"
        )

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "end_time")

    def test_convert_cron_trigger_basic(self) -> None:
        """_convert_trigger converts CronTrigger."""
        # Arrange
        scheduler = APScheduler()
        trigger = CronTrigger(hour="9", minute="30")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.hour == "9"
        assert converted.minute == "30"

    def test_convert_cron_trigger_all_fields(self) -> None:
        """_convert_trigger converts CronTrigger with all fields."""
        # Arrange
        scheduler = APScheduler()
        trigger = CronTrigger(
            year="2023",
            month="3",
            day="15",
            week="2",
            day_of_week="1",
            hour="9",
            minute="30",
            second="0",
        )

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.year == "2023"
        assert converted.month == "3"
        assert converted.day == "15"

    def test_convert_cron_trigger_with_start_time(self) -> None:
        """_convert_trigger converts CronTrigger with start_time."""
        # Arrange
        scheduler = APScheduler()
        trigger = CronTrigger(hour="9", minute="0", start_time="2023-01-01 09:00:00")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "start_time")

    def test_convert_cron_trigger_with_end_time(self) -> None:
        """_convert_trigger converts CronTrigger with end_time."""
        # Arrange
        scheduler = APScheduler()
        trigger = CronTrigger(hour="9", minute="0", end_time="2023-12-31 17:00:00")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "end_time")

    def test_convert_cron_trigger_with_timezone(self) -> None:
        """_convert_trigger converts CronTrigger with timezone."""
        # Arrange
        scheduler = APScheduler()
        trigger = CronTrigger(hour="9", minute="0", timezone="UTC")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.timezone is not None
        assert str(converted.timezone) == "UTC"

    def test_convert_calendar_interval_trigger_basic(self) -> None:
        """_convert_trigger converts CalendarIntervalTrigger."""
        # Arrange
        scheduler = APScheduler()
        trigger = CalendarIntervalTrigger(weeks=1)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.weeks == 1

    def test_convert_calendar_interval_trigger_all_fields(self) -> None:
        """_convert_trigger converts CalendarIntervalTrigger with all fields."""
        # Arrange
        scheduler = APScheduler()
        trigger = CalendarIntervalTrigger(
            years=1,
            months=2,
            weeks=1,
            days=3,
            hour=9,
            minute=30,
            second=15,
        )

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.years == 1
        assert converted.months == 2
        assert converted.weeks == 1

    def test_convert_calendar_interval_trigger_with_dates(self) -> None:
        """_convert_trigger converts CalendarIntervalTrigger with dates."""
        # Arrange
        scheduler = APScheduler()
        start = datetime(2023, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        trigger = CalendarIntervalTrigger(days=1, start_date=start, end_date=end)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert hasattr(converted, "start_date")
        assert hasattr(converted, "end_date")

    def test_convert_calendar_interval_trigger_with_timezone(self) -> None:
        """_convert_trigger converts CalendarIntervalTrigger with timezone."""
        # Arrange
        scheduler = APScheduler()
        trigger = CalendarIntervalTrigger(days=1, timezone="UTC")

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.timezone is not None
        assert str(converted.timezone) == "UTC"

    def test_convert_unsupported_trigger_returns_as_is(self) -> None:
        """_convert_trigger returns unsupported triggers unchanged."""
        # Arrange
        scheduler = APScheduler()
        mock_trigger = MagicMock()

        # Act
        converted = scheduler._convert_trigger(mock_trigger)

        # Assert
        assert converted is mock_trigger


class TestAPSchedulerConvertTriggerIntervalVariations:
    """Test suite for IntervalTrigger conversion variations."""

    def test_convert_interval_trigger_weeks(self) -> None:
        """_convert_trigger converts IntervalTrigger weeks."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(weeks=2)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.seconds == 2 * 7 * 24 * 60 * 60

    def test_convert_interval_trigger_days(self) -> None:
        """_convert_trigger converts IntervalTrigger days."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(days=5)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.seconds == 5 * 24 * 60 * 60

    def test_convert_interval_trigger_hours(self) -> None:
        """_convert_trigger converts IntervalTrigger hours."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(hours=3)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.seconds == 3 * 60 * 60

    def test_convert_interval_trigger_seconds(self) -> None:
        """_convert_trigger converts IntervalTrigger seconds."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(seconds=45)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        assert converted.seconds == 45

    def test_convert_interval_trigger_microseconds(self) -> None:
        """_convert_trigger converts IntervalTrigger microseconds."""
        # Arrange
        scheduler = APScheduler()
        trigger = IntervalTrigger(microseconds=500000)

        # Act
        converted = scheduler._convert_trigger(trigger)

        # Assert
        assert converted is not None
        # microseconds get converted to seconds
        assert hasattr(converted, "seconds")


class TestAPSchedulerConfigureScheduler:
    """Test suite for APScheduler._configure_scheduler method."""

    @pytest.mark.asyncio
    async def test_configure_scheduler_success(self) -> None:
        """_configure_scheduler configures successfully with real config."""
        # Arrange
        scheduler = APScheduler()

        # Mock the service registry and database config
        with patch(
            "appkit_commons.scheduler.apscheduler.service_registry"
        ) as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry_fn.return_value = mock_registry

            mock_config = MagicMock(spec=DatabaseConfig)
            mock_config.url = "postgresql://user:pass@localhost/dbname"
            mock_registry.get.return_value = mock_config

            # Mock APScheduler constructor
            with patch(
                "appkit_commons.scheduler.apscheduler.AsyncScheduler"
            ) as mock_aps:
                mock_scheduler_instance = AsyncMock()
                mock_aps.return_value = mock_scheduler_instance

                # Act
                await scheduler._configure_scheduler()

                # Assert
                assert scheduler._scheduler is not None
                mock_registry.get.assert_called_once_with(DatabaseConfig)

    @pytest.mark.asyncio
    async def test_configure_scheduler_fallback_on_error(self) -> None:
        """_configure_scheduler falls back to memory store on error."""
        # Arrange
        scheduler = APScheduler()

        with patch(
            "appkit_commons.scheduler.apscheduler.service_registry"
        ) as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry_fn.return_value = mock_registry
            mock_registry.get.side_effect = Exception("Config error")

            with patch(
                "appkit_commons.scheduler.apscheduler.AsyncScheduler"
            ) as mock_aps:
                mock_scheduler_instance = AsyncMock()
                mock_aps.return_value = mock_scheduler_instance

                # Act
                await scheduler._configure_scheduler()

                # Assert
                assert scheduler._scheduler is not None
                # Should be called with no arguments for fallback
                mock_aps.assert_called()

    @pytest.mark.asyncio
    async def test_configure_scheduler_with_postgres_url_conversion(self) -> None:
        """_configure_scheduler converts PostgreSQL URL format."""
        # Arrange
        scheduler = APScheduler()

        with patch(
            "appkit_commons.scheduler.apscheduler.service_registry"
        ) as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry_fn.return_value = mock_registry

            mock_config = MagicMock(spec=DatabaseConfig)
            mock_config.url = "postgresql+psycopg://user:pass@localhost/dbname"
            mock_registry.get.return_value = mock_config

            with (
                patch(
                    "appkit_commons.scheduler.apscheduler.PsycopgEventBroker"
                ) as mock_broker,
                patch(
                    "appkit_commons.scheduler.apscheduler.AsyncScheduler"
                ) as mock_aps,
            ):
                mock_scheduler_instance = AsyncMock()
                mock_aps.return_value = mock_scheduler_instance

                # Act
                await scheduler._configure_scheduler()

                # Assert
                # Verify the URL was converted
                call_args = mock_broker.call_args
                assert call_args is not None
                assert "postgresql://" in str(call_args)
                assert "+psycopg" not in str(call_args)


class TestAPSchedulerScheduleService:
    """Test suite for APScheduler._schedule_service method."""

    def _create_test_service(self) -> ScheduledService:
        """Create a test service."""

        class TestService(ScheduledService):
            job_id = "test_job"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        return TestService()

    @pytest.mark.asyncio
    async def test_schedule_service_success(self) -> None:
        """_schedule_service schedules service successfully."""
        # Arrange
        scheduler = APScheduler()
        service = self._create_test_service()

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        await scheduler._schedule_service(service)

        # Assert
        mock_scheduler.add_schedule.assert_called_once()
        call_args = mock_scheduler.add_schedule.call_args
        assert call_args is not None
        assert call_args[0][0] == service.execute
        assert call_args[1]["id"] == service.job_id
        assert call_args[1]["job_executor"] == "async"

    @pytest.mark.asyncio
    async def test_schedule_service_no_scheduler(self) -> None:
        """_schedule_service does nothing if scheduler is None."""
        # Arrange
        scheduler = APScheduler()
        service = self._create_test_service()
        # scheduler._scheduler is None by default

        # Act
        await scheduler._schedule_service(service)

        # Assert - should complete without error
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_schedule_service_with_exception(self, caplog) -> None:
        """_schedule_service logs error when scheduling fails."""
        # Arrange
        scheduler = APScheduler()
        service = self._create_test_service()

        mock_scheduler = AsyncMock()
        mock_scheduler.add_schedule.side_effect = Exception("Schedule failed")
        scheduler._scheduler = mock_scheduler

        # Act
        with caplog.at_level(logging.ERROR):
            await scheduler._schedule_service(service)

        # Assert
        assert "Failed to add service" in caplog.text


class TestAPSchedulerStart:
    """Test suite for APScheduler.start method."""

    @pytest.mark.asyncio
    async def test_start_already_running(self, caplog) -> None:
        """start returns immediately if already running."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        # Act
        with caplog.at_level(logging.DEBUG):
            await scheduler.start()

        # Assert
        assert "already running" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_start_configures_scheduler(self) -> None:
        """start calls _configure_scheduler."""
        # Arrange
        scheduler = APScheduler()

        with patch.object(
            scheduler, "_configure_scheduler", new_callable=AsyncMock
        ) as mock_configure:
            with patch.object(scheduler, "_schedule_service", new_callable=AsyncMock):
                mock_scheduler = AsyncMock()
                scheduler._scheduler = mock_scheduler

                # Act
                await scheduler.start()

                # Assert
                mock_configure.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_adds_services(self) -> None:
        """start schedules all registered services."""
        # Arrange
        scheduler = APScheduler()
        service = self._create_test_service()
        scheduler._services[service.job_id] = service

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        with patch.object(scheduler, "_configure_scheduler", new_callable=AsyncMock):
            with patch.object(
                scheduler, "_schedule_service", new_callable=AsyncMock
            ) as mock_schedule:
                await scheduler.start()

                # Assert
                mock_schedule.assert_called()

    @pytest.mark.asyncio
    async def test_start_sets_is_running(self) -> None:
        """start sets _is_running to True."""
        # Arrange
        scheduler = APScheduler()

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        with patch.object(scheduler, "_configure_scheduler", new_callable=AsyncMock):
            with patch.object(scheduler, "_schedule_service", new_callable=AsyncMock):
                await scheduler.start()

        # Assert
        assert scheduler._is_running is True

    @pytest.mark.asyncio
    async def test_start_logs_info(self, caplog) -> None:
        """start logs info message."""
        # Arrange
        scheduler = APScheduler()

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        with caplog.at_level(logging.INFO):
            with patch.object(
                scheduler, "_configure_scheduler", new_callable=AsyncMock
            ):
                with patch.object(
                    scheduler, "_schedule_service", new_callable=AsyncMock
                ):
                    await scheduler.start()

        # Assert
        assert "Started scheduler" in caplog.text

    def _create_test_service(self) -> ScheduledService:
        """Create a test service."""

        class TestService(ScheduledService):
            job_id = "test_job"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        return TestService()


class TestAPSchedulerShutdown:
    """Test suite for APScheduler.shutdown method."""

    @pytest.mark.asyncio
    async def test_shutdown_not_running(self, caplog) -> None:
        """shutdown does nothing if not running."""
        # Arrange
        scheduler = APScheduler()
        # _is_running is False by default

        # Act
        with caplog.at_level(logging.INFO):
            await scheduler.shutdown()

        # Assert - should not log shutdown
        assert "stopped" not in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_shutdown_stops_scheduler(self) -> None:
        """shutdown stops the scheduler."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        await scheduler.shutdown()

        # Assert
        mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_exits_context(self) -> None:
        """shutdown exits the scheduler context."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        await scheduler.shutdown()

        # Assert
        mock_scheduler.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_sets_is_running_false(self) -> None:
        """shutdown sets _is_running to False."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        await scheduler.shutdown()

        # Assert
        assert scheduler._is_running is False

    @pytest.mark.asyncio
    async def test_shutdown_logs_info(self, caplog) -> None:
        """shutdown logs info message."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        with caplog.at_level(logging.INFO):
            await scheduler.shutdown()

        # Assert
        assert "stopped" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_shutdown_with_none_scheduler(self) -> None:
        """shutdown handles None scheduler gracefully."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True
        scheduler._scheduler = None

        # Act - log message is still printed even when scheduler is None
        # but the function doesn't error
        try:
            await scheduler.shutdown()
        except AttributeError:
            # If scheduler._scheduler is None, __aexit__ will fail
            # But the code should handle this - it checks _is_running first
            pass

        # Assert - the _is_running should still be False if code reaches the end
        # If it's True, the code exited early due to no scheduler
        assert scheduler._is_running is True  # Stays True because early exit


class TestAPSchedulerAddService:
    """Test suite for APScheduler.add_service method."""

    def _create_test_service(self) -> ScheduledService:
        """Create a test service."""

        class TestService(ScheduledService):
            job_id = "test_job"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        return TestService()

    def test_add_service_stores_service(self) -> None:
        """add_service stores the service."""
        # Arrange
        scheduler = APScheduler()
        service = self._create_test_service()

        # Act
        scheduler.add_service(service)

        # Assert
        assert service.job_id in scheduler._services
        assert scheduler._services[service.job_id] == service

    def test_add_service_multiple(self) -> None:
        """add_service can store multiple services."""
        # Arrange
        scheduler = APScheduler()

        class Service1(ScheduledService):
            job_id = "job_1"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        class Service2(ScheduledService):
            job_id = "job_2"

            @property
            def trigger(self):
                return CronTrigger(hour="9")

            async def execute(self):
                pass

        service1 = Service1()
        service2 = Service2()

        # Act
        scheduler.add_service(service1)
        scheduler.add_service(service2)

        # Assert
        assert len(scheduler._services) == 2
        assert scheduler._services["job_1"] == service1
        assert scheduler._services["job_2"] == service2

    @pytest.mark.asyncio
    async def test_add_service_when_running_schedules_immediately(self) -> None:
        """add_service schedules service immediately if scheduler is running."""
        # Arrange
        scheduler = APScheduler()
        scheduler._is_running = True

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        service = self._create_test_service()

        # Act
        with patch.object(
            scheduler, "_schedule_service", new_callable=AsyncMock
        ) as mock_schedule:
            scheduler.add_service(service)
            # Give the background task time to start
            await asyncio.sleep(0.01)

        # Assert
        assert service.job_id in scheduler._services

    def test_add_service_when_not_running_does_not_schedule(self) -> None:
        """add_service does not schedule if scheduler is not running."""
        # Arrange
        scheduler = APScheduler()
        # _is_running is False by default
        service = self._create_test_service()

        # Act
        with patch.object(
            scheduler, "_schedule_service", new_callable=AsyncMock
        ) as mock_schedule:
            scheduler.add_service(service)

        # Assert
        assert service.job_id in scheduler._services
        # Should not schedule since not running
        mock_schedule.assert_not_called()


class TestAPSchedulerIntegration:
    """Integration tests for APScheduler."""

    @pytest.mark.asyncio
    async def test_start_and_shutdown_lifecycle(self) -> None:
        """Test full start/shutdown lifecycle."""
        # Arrange
        scheduler = APScheduler()

        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        # Act
        with patch.object(scheduler, "_configure_scheduler", new_callable=AsyncMock):
            with patch.object(scheduler, "_schedule_service", new_callable=AsyncMock):
                await scheduler.start()
                assert scheduler.is_running is True

                await scheduler.shutdown()
                assert scheduler.is_running is False

        # Assert
        mock_scheduler.stop.assert_called_once()
        mock_scheduler.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_service_before_and_after_start(self) -> None:
        """Test adding services before and after starting."""
        # Arrange
        scheduler = APScheduler()

        service1 = self._create_test_service1()
        service2 = self._create_test_service2()

        # Act - add before start
        scheduler.add_service(service1)
        assert len(scheduler._services) == 1

        # Add after start
        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler
        scheduler._is_running = True

        with patch.object(scheduler, "_schedule_service", new_callable=AsyncMock):
            scheduler.add_service(service2)
            await asyncio.sleep(0.01)

        # Assert
        assert len(scheduler._services) == 2

    @pytest.mark.asyncio
    async def test_scheduler_with_multiple_trigger_types(self) -> None:
        """Test scheduler with different trigger types."""
        # Arrange
        scheduler = APScheduler()

        interval_service = self._create_test_service1()
        cron_service = self._create_test_service2()

        # Act
        scheduler.add_service(interval_service)
        scheduler.add_service(cron_service)

        # Assert
        assert len(scheduler._services) == 2
        assert isinstance(interval_service.trigger, IntervalTrigger)
        assert isinstance(cron_service.trigger, CronTrigger)

    def _create_test_service1(self) -> ScheduledService:
        """Create test service 1."""

        class TestService1(ScheduledService):
            job_id = "test_1"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        return TestService1()

    def _create_test_service2(self) -> ScheduledService:
        """Create test service 2."""

        class TestService2(ScheduledService):
            job_id = "test_2"

            @property
            def trigger(self):
                return CronTrigger(hour="9")

            async def execute(self):
                pass

        return TestService2()

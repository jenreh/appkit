"""Comprehensive tests for scheduler_types module."""

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from appkit_commons.scheduler.scheduler_types import (
    HOURS_PER_DAY,
    MINUTES_PER_HOUR,
    CalendarIntervalTrigger,
    CronTrigger,
    IntervalTrigger,
    ScheduledService,
    Scheduler,
)


class TestIntervalTriggerComprehensive:
    """Comprehensive test suite for IntervalTrigger."""

    def test_interval_trigger_weeks(self) -> None:
        """IntervalTrigger with weeks parameter."""
        # Act
        trigger = IntervalTrigger(weeks=2)

        # Assert
        assert trigger.interval.days == 14

    def test_interval_trigger_all_parameters(self) -> None:
        """IntervalTrigger with all time parameters."""
        # Act
        trigger = IntervalTrigger(
            weeks=1, days=2, hours=3, minutes=4, seconds=5, microseconds=6
        )

        # Assert
        expected = timedelta(
            weeks=1, days=2, hours=3, minutes=4, seconds=5, microseconds=6
        )  # noqa: E501
        assert trigger.interval == expected

    def test_interval_trigger_to_cron_minutes(self) -> None:
        """IntervalTrigger converts minutes to cron."""
        # Act
        trigger = IntervalTrigger(minutes=15)

        # Assert
        cron = trigger.to_cron()
        assert "*/15" in cron

    def test_interval_trigger_to_cron_hours_less_than_day(self) -> None:
        """IntervalTrigger converts hours < 24 to cron."""
        # Act
        trigger = IntervalTrigger(hours=6)

        # Assert
        cron = trigger.to_cron()
        assert "0 */6" in cron

    def test_interval_trigger_to_cron_days(self) -> None:
        """IntervalTrigger converts days to cron."""
        # Act
        trigger = IntervalTrigger(days=3)

        # Assert
        cron = trigger.to_cron()
        assert "*/3" in cron

    def test_interval_trigger_with_seconds_logs_warning(self, caplog) -> None:
        """IntervalTrigger logs warning for seconds > 0."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = IntervalTrigger(minutes=1, seconds=30)
            trigger.to_cron()

        # Assert
        assert "Seconds granularity" in caplog.text

    def test_interval_trigger_with_start_time_logs_warning(self, caplog) -> None:
        """IntervalTrigger logs warning for ignored start_time."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = IntervalTrigger(hours=1, start_time="2023-01-01")
            trigger.to_cron()

        # Assert
        assert "ignored" in caplog.text.lower()

    def test_interval_trigger_with_end_time_logs_warning(self, caplog) -> None:
        """IntervalTrigger logs warning for ignored end_time."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = IntervalTrigger(hours=1, end_time="2023-12-31")
            trigger.to_cron()

        # Assert
        assert "ignored" in caplog.text.lower()

    def test_interval_trigger_with_timezone_logs_warning(self, caplog) -> None:
        """IntervalTrigger logs warning for ignored timezone."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = IntervalTrigger(hours=1, timezone="UTC")
            trigger.to_cron()

        # Assert
        assert "ignored" in caplog.text.lower()

    def test_interval_trigger_with_jitter_logs_warning(self, caplog) -> None:
        """IntervalTrigger logs warning for ignored jitter."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = IntervalTrigger(hours=1, jitter=30)
            trigger.to_cron()

        # Assert
        assert "ignored" in caplog.text.lower()

    def test_interval_trigger_minutes_per_hour_constant(self) -> None:
        """MINUTES_PER_HOUR constant is correct."""
        # Assert
        assert MINUTES_PER_HOUR == 60

    def test_interval_trigger_hours_per_day_constant(self) -> None:
        """HOURS_PER_DAY constant is correct."""
        # Assert
        assert HOURS_PER_DAY == 24


class TestCalendarIntervalTriggerComprehensive:
    """Comprehensive test suite for CalendarIntervalTrigger."""

    def test_calendar_interval_trigger_all_parameters(self) -> None:
        """CalendarIntervalTrigger with all parameters."""
        # Act
        trigger = CalendarIntervalTrigger(
            years=1,
            months=2,
            weeks=1,
            days=3,
            hour=9,
            minute=30,
            second=15,
            start_date=datetime(2023, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 12, 31, tzinfo=UTC),
            timezone="UTC",
        )

        # Assert
        assert trigger.years == 1
        assert trigger.months == 2
        assert trigger.weeks == 1
        assert trigger.days == 3
        assert trigger.hour == 9
        assert trigger.minute == 30
        assert trigger.second == 15

    def test_calendar_interval_weekly_to_cron(self) -> None:
        """CalendarIntervalTrigger weekly to cron."""
        # Act
        trigger = CalendarIntervalTrigger(weeks=1, hour=9, minute=0)

        # Assert
        cron = trigger.to_cron()
        assert "0" in cron  # minute
        assert "9" in cron  # hour

    def test_calendar_interval_daily_to_cron(self) -> None:
        """CalendarIntervalTrigger daily to cron."""
        # Act
        trigger = CalendarIntervalTrigger(days=1, hour=12)

        # Assert
        cron = trigger.to_cron()
        assert "*" in cron

    def test_calendar_interval_multi_day_to_cron(self) -> None:
        """CalendarIntervalTrigger multi-day to cron."""
        # Act
        with patch("appkit_commons.scheduler.scheduler_types.logger") as mock_logger:
            trigger = CalendarIntervalTrigger(days=3, hour=12)
            cron = trigger.to_cron()

            # Assert
            assert "*/3" in cron
            assert mock_logger.warning.called

    def test_calendar_interval_monthly_to_cron(self) -> None:
        """CalendarIntervalTrigger monthly to cron."""
        # Arrange
        anchor_date = datetime(2023, 3, 15, tzinfo=UTC)

        # Act
        trigger = CalendarIntervalTrigger(months=1, start_date=anchor_date)

        # Assert
        cron = trigger.to_cron()
        assert "15" in cron  # day from anchor
        # months=1 means every month, so month should be "*" (wildcard)

    def test_calendar_interval_multi_month_to_cron(self) -> None:
        """CalendarIntervalTrigger multi-month to cron."""
        # Arrange
        anchor_date = datetime(2023, 6, 15, tzinfo=UTC)

        # Act
        trigger = CalendarIntervalTrigger(months=3, start_date=anchor_date)

        # Assert
        cron = trigger.to_cron()
        assert "*/3" in cron

    def test_calendar_interval_yearly_to_cron(self) -> None:
        """CalendarIntervalTrigger yearly to cron."""
        # Arrange
        anchor_date = datetime(2023, 3, 15, tzinfo=UTC)

        # Act
        trigger = CalendarIntervalTrigger(years=1, start_date=anchor_date)

        # Assert
        cron = trigger.to_cron()
        assert "15" in cron  # day
        assert "3" in cron  # month

    def test_calendar_interval_multi_year_logs_warning(self, caplog) -> None:
        """CalendarIntervalTrigger logs warning for years > 1."""
        # Arrange
        anchor_date = datetime(2023, 1, 1, tzinfo=UTC)

        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CalendarIntervalTrigger(years=2, start_date=anchor_date)
            trigger.to_cron()

        # Assert
        assert "not supported" in caplog.text.lower()

    def test_calendar_interval_seconds_logs_warning(self, caplog) -> None:
        """CalendarIntervalTrigger logs warning for seconds > 0."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CalendarIntervalTrigger(days=1, second=30)
            trigger.to_cron()

        # Assert
        assert "granularity" in caplog.text.lower()

    def test_calendar_interval_multi_week_logs_warning(self, caplog) -> None:
        """CalendarIntervalTrigger logs warning for weeks > 1."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CalendarIntervalTrigger(weeks=2)
            trigger.to_cron()

        # Assert
        assert "weekly" in caplog.text.lower()


class TestCronTriggerComprehensive:
    """Comprehensive test suite for CronTrigger."""

    def test_cron_trigger_all_parameters(self) -> None:
        """CronTrigger with all parameters."""
        # Act
        trigger = CronTrigger(
            year="2023",
            month="3",
            day="15",
            week="2",
            day_of_week="1",
            hour="9",
            minute="30",
            second="0",
            start_time="09:00:00",
            end_time="17:00:00",
            timezone="UTC",
            custom_param="value",
        )

        # Assert
        assert trigger.year == "2023"
        assert trigger.month == "3"
        assert trigger.day == "15"
        assert trigger.week == "2"
        assert trigger.day_of_week == "1"
        assert trigger.hour == "9"
        assert trigger.minute == "30"
        assert trigger.second == "0"
        assert trigger.kwargs["custom_param"] == "value"

    def test_cron_trigger_integer_parameters(self) -> None:
        """CronTrigger accepts integer parameters."""
        # Act
        trigger = CronTrigger(hour=9, minute=30, day=15)

        # Assert
        assert trigger.hour == 9
        assert trigger.minute == 30
        assert trigger.day == 15

    def test_cron_trigger_to_cron_basic(self) -> None:
        """CronTrigger.to_cron generates basic cron expression."""
        # Act
        trigger = CronTrigger(hour="9", minute="30", day="15")

        # Assert
        cron = trigger.to_cron()
        assert cron == "30 9 15 * *"

    def test_cron_trigger_with_year_logs_warning(self, caplog) -> None:
        """CronTrigger logs warning for unsupported year."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CronTrigger(year="2023")
            trigger.to_cron()

        # Assert
        assert "year" in caplog.text.lower()

    def test_cron_trigger_with_week_logs_warning(self, caplog) -> None:
        """CronTrigger logs warning for unsupported ISO week."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CronTrigger(week="15")
            trigger.to_cron()

        # Assert
        assert "week" in caplog.text.lower()

    def test_cron_trigger_with_second_logs_warning(self, caplog) -> None:
        """CronTrigger logs warning for unsupported second."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CronTrigger(second="30")
            trigger.to_cron()

        # Assert
        assert "second" in caplog.text.lower()

    def test_cron_trigger_with_ignored_time_params_logs_warning(self, caplog) -> None:
        """CronTrigger logs warning for ignored time parameters."""
        # Act
        with caplog.at_level(logging.WARNING):
            trigger = CronTrigger(start_time="09:00", end_time="17:00")
            trigger.to_cron()

        # Assert
        assert "ignored" in caplog.text.lower()


class TestScheduledServiceComprehensive:
    """Comprehensive test suite for ScheduledService."""

    def test_scheduled_service_job_id_required(self) -> None:
        """ScheduledService requires job_id class variable."""

        # Arrange
        class TestService(ScheduledService):
            job_id = "test_job"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=1)

            async def execute(self):
                pass

        # Act
        service = TestService()

        # Assert
        assert service.job_id == "test_job"

    def test_scheduled_service_name_has_default(self) -> None:
        """ScheduledService has default name."""

        # Arrange
        class TestService(ScheduledService):
            job_id = "test"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=1)

            async def execute(self):
                pass

        # Act
        service = TestService()

        # Assert
        assert service.name == "Scheduled Service"

    def test_scheduled_service_name_customizable(self) -> None:
        """ScheduledService name can be customized."""

        # Arrange
        class CustomService(ScheduledService):
            job_id = "custom"
            name = "My Custom Service"

            @property
            def trigger(self):
                return CronTrigger(hour="9")

            async def execute(self):
                pass

        # Act
        service = CustomService()

        # Assert
        assert service.name == "My Custom Service"

    @pytest.mark.asyncio
    async def test_scheduled_service_execute_is_async(self) -> None:
        """ScheduledService.execute is async."""
        # Arrange
        call_count = 0

        class CounterService(ScheduledService):
            job_id = "counter"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=1)

            async def execute(self):
                nonlocal call_count
                call_count += 1

        # Act
        service = CounterService()
        await service.execute()

        # Assert
        assert call_count == 1


class TestSchedulerComprehensive:
    """Comprehensive test suite for Scheduler."""

    def test_scheduler_requires_is_running_property(self) -> None:
        """Scheduler requires is_running property."""

        # Arrange
        class TestScheduler(Scheduler):
            @property
            def is_running(self):
                return False

            def add_service(self, service):
                pass

            async def start(self):
                pass

            async def shutdown(self):
                pass

        # Act
        scheduler = TestScheduler()

        # Assert
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_scheduler_start_method(self) -> None:
        """Scheduler.start is async."""

        # Arrange
        class TestScheduler(Scheduler):
            started = False

            @property
            def is_running(self):
                return self.started

            def add_service(self, service):
                pass

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

        # Act
        scheduler = TestScheduler()
        await scheduler.start()

        # Assert
        assert scheduler.started is True

    @pytest.mark.asyncio
    async def test_scheduler_shutdown_method(self) -> None:
        """Scheduler.shutdown is async."""

        # Arrange
        class TestScheduler(Scheduler):
            started = True

            @property
            def is_running(self):
                return self.started

            def add_service(self, service):
                pass

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

        # Act
        scheduler = TestScheduler()
        await scheduler.shutdown()

        # Assert
        assert scheduler.started is False

    def test_scheduler_add_service_stores_service(self) -> None:
        """Scheduler.add_service stores the service."""

        # Arrange
        class TestScheduler(Scheduler):
            def __init__(self):
                self.services = []

            @property
            def is_running(self):
                return False

            def add_service(self, service):
                self.services.append(service)

            async def start(self):
                pass

            async def shutdown(self):
                pass

        class TestService(ScheduledService):
            job_id = "test"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=1)

            async def execute(self):
                pass

        # Act
        scheduler = TestScheduler()
        service = TestService()
        scheduler.add_service(service)

        # Assert
        assert len(scheduler.services) == 1
        assert scheduler.services[0] == service

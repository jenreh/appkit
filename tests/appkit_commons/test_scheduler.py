"""Tests for scheduler modules."""

from datetime import timedelta

from appkit_commons.scheduler import (
    CalendarIntervalTrigger,
    CronTrigger,
    IntervalTrigger,
    ScheduledService,
    Scheduler,
    Trigger,
)


class TestTrigger:
    """Test suite for Trigger base class."""

    def test_trigger_is_abstract(self) -> None:
        """Trigger is an abstract base class."""
        # Assert
        assert hasattr(Trigger, "__abstractmethods__")

    def test_trigger_to_cron_required(self) -> None:
        """Trigger requires to_cron method."""
        # Assert
        assert "to_cron" in Trigger.__abstractmethods__


class TestIntervalTrigger:
    """Test suite for IntervalTrigger."""

    def test_interval_trigger_creation(self) -> None:
        """IntervalTrigger can be created with interval parameters."""
        # Act
        trigger = IntervalTrigger(hours=1, minutes=30)

        # Assert
        assert trigger.interval == timedelta(hours=1, minutes=30)

    def test_interval_trigger_default_values(self) -> None:
        """IntervalTrigger has default values."""
        # Act
        trigger = IntervalTrigger()

        # Assert
        assert trigger.start_time is None
        assert trigger.end_time is None
        assert trigger.timezone is None
        assert trigger.jitter is None

    def test_interval_trigger_to_cron_hourly(self) -> None:
        """IntervalTrigger.to_cron converts hourly interval correctly."""
        # Act
        trigger = IntervalTrigger(hours=2)

        # Assert
        cron = trigger.to_cron()
        assert "*/2" in cron  # 2 hours

    def test_interval_trigger_to_cron_daily(self) -> None:
        """IntervalTrigger.to_cron converts daily interval correctly."""
        # Act
        trigger = IntervalTrigger(days=1)

        # Assert
        cron = trigger.to_cron()
        assert "*/1" in cron  # 1 day

    def test_interval_trigger_zero_interval(self) -> None:
        """IntervalTrigger with zero interval generates cron for every minute."""
        # Act
        trigger = IntervalTrigger()

        # Assert
        cron = trigger.to_cron()
        assert cron == "* * * * *"


class TestCronTrigger:
    """Test suite for CronTrigger."""

    def test_cron_trigger_creation(self) -> None:
        """CronTrigger can be created with cron parameters."""
        # Act
        trigger = CronTrigger(hour="9", minute="0")

        # Assert
        assert trigger.hour == "9"
        assert trigger.minute == "0"

    def test_cron_trigger_default_values(self) -> None:
        """CronTrigger has default wildcard values."""
        # Act
        trigger = CronTrigger()

        # Assert
        assert trigger.year == "*"
        assert trigger.month == "*"
        assert trigger.day == "*"
        assert trigger.hour == "*"
        assert trigger.minute == "*"

    def test_cron_trigger_to_cron(self) -> None:
        """CronTrigger.to_cron generates cron expression."""
        # Act
        trigger = CronTrigger(hour="9", minute="30", day="1")

        # Assert
        cron = trigger.to_cron()
        assert "30" in cron  # minute
        assert "9" in cron  # hour
        assert "1" in cron  # day


class TestCalendarIntervalTrigger:
    """Test suite for CalendarIntervalTrigger."""

    def test_calendar_interval_trigger_creation(self) -> None:
        """CalendarIntervalTrigger can be created."""
        # Act
        trigger = CalendarIntervalTrigger(weeks=1)

        # Assert
        assert trigger is not None
        assert trigger.to_cron() is not None

    def test_calendar_interval_trigger_to_cron(self) -> None:
        """CalendarIntervalTrigger.to_cron generates cron expression."""
        # Act
        trigger = CalendarIntervalTrigger(days=3)

        # Assert
        cron = trigger.to_cron()
        assert cron is not None


class TestScheduledService:
    """Test suite for ScheduledService base class."""

    def test_scheduled_service_is_abstract(self) -> None:
        """ScheduledService is an abstract base class."""
        # Assert
        assert hasattr(ScheduledService, "__abstractmethods__")

    def test_scheduled_service_requires_execute(self) -> None:
        """ScheduledService requires execute method."""
        # Assert
        assert "execute" in ScheduledService.__abstractmethods__

    def test_scheduled_service_requires_trigger(self) -> None:
        """ScheduledService requires trigger property."""
        # Assert
        assert "trigger" in ScheduledService.__abstractmethods__

    def test_scheduled_service_subclass_can_be_created(self) -> None:
        """ScheduledService subclass can be created."""

        # Arrange
        class TestService(ScheduledService):
            job_id = "test_job"
            name = "Test Service"

            @property
            def trigger(self) -> Trigger:
                return IntervalTrigger(minutes=5)

            async def execute(self, *args, **kwargs) -> None:  # noqa: ARG002
                pass

        # Act & Assert
        service = TestService()
        assert service.job_id == "test_job"
        assert service.name == "Test Service"

    def test_scheduled_service_has_trigger(self) -> None:
        """ScheduledService subclass provides trigger."""

        # Arrange
        class TestService(ScheduledService):
            job_id = "test_job"

            @property
            def trigger(self) -> Trigger:
                return CronTrigger(hour="12", minute="0")

            async def execute(self, *args, **kwargs) -> None:  # noqa: ARG002
                pass

        # Act
        service = TestService()

        # Assert
        assert isinstance(service.trigger, CronTrigger)


class TestScheduler:
    """Test suite for Scheduler base class."""

    def test_scheduler_is_abstract(self) -> None:
        """Scheduler is an abstract base class."""
        # Assert
        assert hasattr(Scheduler, "__abstractmethods__")

    def test_scheduler_methods_required(self) -> None:
        """Scheduler requires required abstract methods."""
        # Assert
        required = {"is_running", "add_service", "start", "shutdown"}
        assert required.issubset(Scheduler.__abstractmethods__)

    def test_scheduler_subclass_can_be_created(self) -> None:
        """Scheduler subclass can be created."""

        # Arrange
        class TestScheduler(Scheduler):
            @property
            def is_running(self) -> bool:
                return False

            def add_service(self, service: ScheduledService) -> None:  # noqa: ARG002
                pass

            async def start(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        # Act & Assert
        scheduler = TestScheduler()
        assert scheduler is not None

    def test_scheduler_can_add_service(self) -> None:
        """Scheduler subclass can add services."""

        # Arrange
        class TestScheduler(Scheduler):
            def __init__(self):
                self.services = []

            @property
            def is_running(self) -> bool:
                return False

            def add_service(self, service: ScheduledService) -> None:
                self.services.append(service)

            async def start(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        class TestService(ScheduledService):
            job_id = "test"

            @property
            def trigger(self) -> Trigger:
                return IntervalTrigger(minutes=1)

            async def execute(self, *args, **kwargs) -> None:  # noqa: ARG002
                pass

        # Act
        scheduler = TestScheduler()
        service = TestService()
        scheduler.add_service(service)

        # Assert
        assert len(scheduler.services) == 1
        assert scheduler.services[0] == service

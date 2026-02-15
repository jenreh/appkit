"""Scheduler types and abstract base classes."""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


class Trigger(ABC):
    """Abstract base class for triggers."""

    @abstractmethod
    def to_cron(self) -> str:
        """Convert trigger to cron expression."""
        ...

    def _warn_ignoring_args(self, **kwargs: Any) -> None:
        """Log warning for ignored arguments."""
        ignored = [k for k, v in kwargs.items() if v]
        if ignored:
            logger.warning(
                "The following arguments are ignored by this backend: %s",
                ", ".join(ignored),
            )


class IntervalTrigger(Trigger):
    """Trigger that runs at a fixed interval."""

    def __init__(
        self,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        microseconds: int = 0,
        start_time: Any | None = None,
        end_time: Any | None = None,
        timezone: Any | None = None,
        jitter: int | None = None,
    ):
        self._interval = timedelta(
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            microseconds=microseconds,
        )
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.jitter = jitter

    def to_cron(self) -> str:
        """Convert interval to cron expression."""
        total_seconds = int(self._interval.total_seconds())
        total_minutes = total_seconds // 60
        remainder_seconds = total_seconds % 60

        if remainder_seconds > 0:
            logger.warning(
                "Seconds granularity (%d seconds) not supported. Ignoring.",
                remainder_seconds,
            )

        self._warn_ignoring_args(
            start_time=self.start_time,
            end_time=self.end_time,
            timezone=self.timezone,
            jitter=self.jitter,
        )

        if total_minutes == 0:
            return "* * * * *"

        if total_minutes < MINUTES_PER_HOUR:
            return f"*/{total_minutes} * * * *"

        if total_minutes % MINUTES_PER_HOUR == 0:
            hours = total_minutes // MINUTES_PER_HOUR
            if hours < HOURS_PER_DAY:
                return f"0 */{hours} * * * *"
            if hours % HOURS_PER_DAY == 0:
                days = hours // HOURS_PER_DAY
                return f"0 0 */{days} * *"

        logger.warning(
            "Interval %d minutes cannot be perfectly represented as simple Cron. "
            "Defaulting to */%d * * * * which might be inexact.",
            total_minutes,
            total_minutes,
        )
        return f"*/{total_minutes} * * * *"


class CalendarIntervalTrigger(Trigger):
    """Runs the task on specified calendar-based intervals."""

    def __init__(
        self,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        start_date: Any | None = None,
        end_date: Any | None = None,
        timezone: Any | None = None,
    ):
        self.years = years
        self.months = months
        self.weeks = weeks
        self.days = days
        self.hour = hour
        self.minute = minute
        self.second = second
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone

    def to_cron(self) -> str:
        """Convert calendar interval to cron expression."""
        if self.second > 0:
            logger.warning(
                "Seconds granularity (%d) not supported. Ignoring.", self.second
            )

        anchor = self.start_date or datetime.now(tz=UTC)
        parts = {
            "minute": str(self.minute),
            "hour": str(self.hour),
            "day": "*",
            "month": "*",
            "week": "*",
        }

        if self.weeks > 0:
            self._handle_weekly(parts, anchor)
        elif self.days > 0:
            self._handle_daily(parts)
        elif self.months > 0:
            self._handle_monthly(parts, anchor)
        elif self.years > 0:
            self._handle_yearly(parts, anchor)

        return (
            f"{parts['minute']} {parts['hour']} {parts['day']} "
            f"{parts['month']} {parts['week']}"
        )

    def _handle_weekly(self, parts: dict[str, str], anchor: datetime) -> None:
        if self.weeks > 1:
            logger.warning(
                "Weekly interval > 1 week (%d) resets weekly in Cron.", self.weeks
            )
        # Python: Mon=0 -> Sun=6. Cron: Sun=0 or 7.
        dow = (anchor.weekday() + 1) % 7
        parts["week"] = str(dow)

    def _handle_daily(self, parts: dict[str, str]) -> None:
        if self.days > 1:
            parts["day"] = f"*/{self.days}"
            logger.warning(
                "Daily interval > 1 day (%d) resets monthly in Cron.", self.days
            )
        # If days=1, default is "*" which is already set

    def _handle_monthly(self, parts: dict[str, str], anchor: datetime) -> None:
        parts["day"] = str(anchor.day)
        if self.months > 1:
            parts["month"] = f"*/{self.months}"

    def _handle_yearly(self, parts: dict[str, str], anchor: datetime) -> None:
        parts["day"] = str(anchor.day)
        parts["month"] = str(anchor.month)
        if self.years > 1:
            logger.warning(
                "Yearly interval > 1 year (%d) not supported in Cron.", self.years
            )


class CronTrigger(Trigger):
    """Triggers when current time matches all specified time constraints."""

    def __init__(
        self,
        year: int | str = "*",
        month: int | str = "*",
        day: int | str = "*",
        week: int | str = "*",
        day_of_week: int | str = "*",
        hour: int | str = "*",
        minute: int | str = "*",
        second: int | str = "0",
        start_time: Any | None = None,
        end_time: Any | None = None,
        timezone: Any | None = None,
        **kwargs: Any,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.week = week
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.kwargs = kwargs

    def to_cron(self) -> str:
        """Convert to cron expression."""
        self._check_unsupported_fields()
        self._warn_ignoring_args(
            start_time=self.start_time,
            end_time=self.end_time,
            timezone=self.timezone,
        )
        return f"{self.minute} {self.hour} {self.day} {self.month} {self.day_of_week}"

    def _check_unsupported_fields(self) -> None:
        unsupported = {
            "Year": (self.year, "*"),
            "ISO Week": (self.week, "*"),
            "Second": (str(self.second), "0"),
        }
        for name, (value, default) in unsupported.items():
            if value != default:
                logger.warning(
                    "%s constraint (%s) not supported by standard Cron. Ignoring.",
                    name,
                    value,
                )


class ScheduledService(ABC):
    """Base class for scheduled services."""

    job_id: ClassVar[str]
    name: ClassVar[str] = "Scheduled Service"

    @property
    @abstractmethod
    def trigger(self) -> Trigger:
        """The trigger configuration for the job."""
        ...

    @abstractmethod
    async def execute(self, *args, **kwargs) -> None:
        """The actual job logic to execute."""
        ...


class Scheduler(ABC):
    """Abstract base class for the application scheduler."""

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        ...

    @abstractmethod
    def add_service(self, service: ScheduledService) -> None:
        """Add a service to the scheduler."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the scheduler background task."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        ...

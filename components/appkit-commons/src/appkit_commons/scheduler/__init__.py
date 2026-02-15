"""Central scheduler service interface and exports.

Provides a unified scheduling interface for the application, with types
and the default implementation.
"""

# Try to import PGQueuerScheduler, but don't fail at module level
try:
    from appkit_commons.scheduler.pgqueuer import PGQueuerScheduler
except ImportError:
    PGQueuerScheduler = None  # type: ignore
try:
    from appkit_commons.scheduler.apscheduler import APScheduler
except ImportError:
    APScheduler = None  # type: ignore

from appkit_commons.scheduler.scheduler_types import (
    CalendarIntervalTrigger,
    CronTrigger,
    IntervalTrigger,
    ScheduledService,
    Scheduler,
    Trigger,
)

__all__ = [
    "APScheduler",
    "CalendarIntervalTrigger",
    "CronTrigger",
    "IntervalTrigger",
    "PGQueuerScheduler",
    "ScheduledService",
    "Scheduler",
    "Trigger",
]

"""Central scheduler service for managing background jobs.

Distributed-safe using APScheduler 4.x + PostgresEventBroker.
"""

import asyncio
import logging
from typing import Any

from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.eventbrokers.psycopg import PsycopgEventBroker
from apscheduler.triggers.calendarinterval import (
    CalendarIntervalTrigger as APSCalendarIntervalTrigger,
)
from apscheduler.triggers.cron import CronTrigger as APSCronTrigger
from apscheduler.triggers.interval import IntervalTrigger as APSIntervalTrigger

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.registry import service_registry
from appkit_commons.scheduler.scheduler_types import (
    CalendarIntervalTrigger,
    CronTrigger,
    IntervalTrigger,
    ScheduledService,
    Scheduler,
    Trigger,
)

logger = logging.getLogger(__name__)


class APScheduler(Scheduler):
    """Central application scheduler service with distributed coordination."""

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._scheduler: AsyncScheduler | None = None
        self._is_running = False
        self._services: dict[str, ScheduledService] = {}
        self._background_tasks: set[asyncio.Task] = set()

    def _convert_trigger(self, trigger: Trigger) -> Any:
        """Convert internal trigger type to APScheduler trigger."""
        if isinstance(trigger, IntervalTrigger):
            kwargs = {
                "seconds": trigger._interval.total_seconds(),  # noqa: SLF001
            }
            if trigger.start_time:
                kwargs["start_time"] = trigger.start_time
            if trigger.end_time:
                kwargs["end_time"] = trigger.end_time
            # IntervalTrigger does not support timezone directly in v4

            return APSIntervalTrigger(**kwargs)

        if isinstance(trigger, CronTrigger):
            kwargs = {
                "year": trigger.year,
                "month": trigger.month,
                "day": trigger.day,
                "week": trigger.week,
                "day_of_week": trigger.day_of_week,
                "hour": trigger.hour,
                "minute": trigger.minute,
                "second": trigger.second,
            }
            if trigger.start_time:
                kwargs["start_time"] = trigger.start_time
            if trigger.end_time:
                kwargs["end_time"] = trigger.end_time
            if trigger.timezone:
                kwargs["timezone"] = trigger.timezone

            return APSCronTrigger(**kwargs)

        if isinstance(trigger, CalendarIntervalTrigger):
            kwargs = {
                "years": trigger.years,
                "months": trigger.months,
                "weeks": trigger.weeks,
                "days": trigger.days,
                "hour": trigger.hour,
                "minute": trigger.minute,
                "second": trigger.second,
            }
            if trigger.start_date:
                kwargs["start_date"] = trigger.start_date
            if trigger.end_date:
                kwargs["end_date"] = trigger.end_date
            if trigger.timezone:
                kwargs["timezone"] = trigger.timezone

            return APSCalendarIntervalTrigger(**kwargs)

        return trigger

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._is_running

    async def _configure_scheduler(self) -> None:
        """Configure the scheduler with PostgresEventBroker + SQLAlchemy datastore."""
        try:
            registry = service_registry()
            config = registry.get(DatabaseConfig)

            # Create event broker for distributed coordination
            # Uses PsycopgEventBroker (PostgresEventBroker) as requested
            # PsycopgEventBroker requires a standard postgres URI, not SQLAlchemy's
            # +psycopg format
            conn_url = config.url.replace("postgresql+psycopg://", "postgresql://")
            event_broker = PsycopgEventBroker(conninfo=conn_url)

            data_store = SQLAlchemyDataStore(config.url)
            self._scheduler = AsyncScheduler(
                data_store=data_store,
                event_broker=event_broker,
            )
        except Exception as e:
            logger.exception(
                "Failed to configure distributed scheduler: %s. "
                "Falling back to memory store.",
                e,
            )
            # Fallback to memory (single-instance only)
            self._scheduler = AsyncScheduler()

    async def _schedule_service(self, service: ScheduledService) -> None:
        """Schedule a service instance."""
        if not self._scheduler:
            return

        try:
            await self._scheduler.add_schedule(
                service.execute,
                trigger=self._convert_trigger(service.trigger),
                id=service.job_id,
                job_executor="async",  # For async execute() methods
                conflict_policy="replace",  # Safe for multi-instance
            )
        except Exception as e:
            logger.exception(
                "Failed to add service '%s': %s",
                service.name,
                e,
            )

    async def start(self) -> None:
        """Start the scheduler if not already running."""
        if self._is_running:
            logger.debug("Application scheduler is already running")
            return

        await self._configure_scheduler()

        # Start scheduler using async context manager pattern manually
        if self._scheduler:
            # Enter the context manager to initialize the scheduler
            await self._scheduler.__aenter__()

            # Add all registered services
            for service in self._services.values():
                await self._schedule_service(service)

            # Start processing in background
            await self._scheduler.start_in_background()
            self._is_running = True
            logger.info("Started scheduler (services=%d)", len(self._services))

    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self._is_running and self._scheduler:
            # Stop the scheduler
            await self._scheduler.stop()
            # Exit the context manager to cleanup resources
            await self._scheduler.__aexit__(None, None, None)

            self._is_running = False
            logger.info("Application scheduler stopped")

    def add_service(self, service: ScheduledService) -> None:
        """Add a service to the scheduler.

        Schedules the job defined by the service instance.

        Args:
            service: The initialized service instance to schedule.
        """
        self._services[service.job_id] = service
        if self._is_running:
            # Schedule immediately if already running
            task = asyncio.create_task(self._schedule_service(service))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

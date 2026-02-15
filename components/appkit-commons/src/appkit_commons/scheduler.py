"""Central scheduler service for managing background jobs.

Wraps APScheduler to provide a unified scheduling interface for the application.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class ScheduledService(ABC):
    """Base class for scheduled services."""

    job_id: ClassVar[str]
    name: ClassVar[str]

    @property
    @abstractmethod
    def trigger(self) -> BaseTrigger:
        """The trigger configuration for the job."""
        ...

    @abstractmethod
    async def execute(self) -> None:
        """The actual job logic to execute."""
        ...


class Scheduler:
    """Central application scheduler service."""

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._scheduler = AsyncIOScheduler()
        self._is_running = False
        self._services: dict[str, ScheduledService] = {}

    def start(self) -> None:
        """Start the scheduler if not already running."""
        if not self._is_running:
            self._scheduler.start()
            self._is_running = True
            logger.info("Application scheduler started")
        else:
            logger.debug("Application scheduler is already running")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Application scheduler stopped")

    def add_service(self, service: ScheduledService) -> None:
        """Add a service to the scheduler.

        Schedules the job defined by the service instance.

        Args:
            service: The initialized service instance to schedule.
        """
        try:
            self._services[service.job_id] = service

            self._scheduler.add_job(
                service.execute,
                trigger=service.trigger,
                id=service.job_id,
                name=service.name,
                replace_existing=True,
            )
            logger.info("Added service '%s' (id=%s)", service.name, service.job_id)
        except Exception as e:
            logger.error("Failed to add service '%s': %s", service.name, e)

    def add_job(
        self,
        func: Any,
        trigger: BaseTrigger,
        id: str | None = None,  # noqa: A002
        name: str | None = None,
        replace_existing: bool = True,
        **kwargs: Any,
    ) -> None:
        """Add a job to the scheduler.

        Args:
            func: Function to schedule
            trigger: Trigger instance (IntervalTrigger, CronTrigger, etc.)
            id: Unique identifier for the job
            name: Human-readable name
            replace_existing: Whether to replace existing job with same ID
            **kwargs: Additional arguments for add_job
        """
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=id,
            name=name,
            replace_existing=replace_existing,
            **kwargs,
        )
        logger.info("Added job '%s' (id=%s)", name or func.__name__, id)


# Global instance
scheduler = Scheduler()

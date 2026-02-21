"""PGQueuer implementation of the scheduler."""

import asyncio
import contextlib
import logging
from typing import Any

import psycopg
from pgqueuer import PgQueuer
from pgqueuer.db import PsycopgDriver
from pgqueuer.models import Schedule

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.registry import service_registry
from appkit_commons.scheduler.scheduler_types import ScheduledService, Scheduler

logger = logging.getLogger(__name__)


class PGQueuerScheduler(Scheduler):
    """Central application scheduler service using PGQueuer."""

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._pgq: PgQueuer | None = None
        self._is_running = False
        self._services: dict[str, ScheduledService] = {}
        self._conn: psycopg.AsyncConnection | None = None
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._is_running

    async def _setup_pgqueuer(self) -> None:
        """Configure PGQueuer with database connection."""
        try:
            registry = service_registry()
            config = registry.get(DatabaseConfig)

            # Fix connection string for psycopg if it contains driver info
            url_str = str(config.url).replace("+psycopg", "").replace("+asyncpg", "")

            # Connect using psycopg with keepalive settings to prevent dropouts
            # Azure DB for PostgreSQL defaults to 4 minutes idle timeout, so we
            # set keepalives to ensure the connection stays active.
            self._conn = await psycopg.AsyncConnection.connect(
                url_str,
                autocommit=True,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )

            # Driver
            driver = PsycopgDriver(self._conn)
            self._pgq = PgQueuer(driver)

            logger.info("Scheduler configured with PGQueuer")
        except Exception as e:
            logger.exception(
                "Failed to configure PGQueuer: %s.",
                e,
            )

    def add_service(self, service: ScheduledService) -> None:
        """Add a service to the scheduler.

        Schedules the job defined by the service instance.

        Args:
            service: The initialized service instance to schedule.
        """
        self._services[service.job_id] = service
        # If running, register immediately
        if self._is_running and self._pgq:
            self._register_service_on_pgq(service)

    def _register_service_on_pgq(self, service: ScheduledService) -> None:
        """Register the service with the PGQueuer instance."""
        if not self._pgq:
            return

        cron = service.trigger.to_cron()

        # Define the wrapper function that calls execute
        # Note: PGQueuer passes 'schedule: Schedule' to the function
        async def wrapper(_schedule: Schedule) -> None:
            logger.info("Executing scheduled service: %s", service.name)
            try:
                await service.execute()
            except Exception as e:
                logger.error("Error executing service %s: %s", service.name, e)

        # Register using the .schedule decorator logic programmatically
        # This effectively does: @pgq.schedule(...)
        self._pgq.schedule(service.job_id, cron)(wrapper)
        logger.debug("Registered service '%s' with cron '%s'", service.job_id, cron)

    async def _cleanup_connection(self) -> None:
        """Close database connection and clear PGQueuer instance."""
        if self._conn:
            with contextlib.suppress(Exception):
                await self._conn.close()
        self._conn = None
        self._pgq = None

    async def _run_loop(self) -> None:
        """Main loop for the scheduler with auto-restart on connection loss."""
        while self._is_running:
            try:
                # 1. Setup connection and PGQueuer if needed
                if not self._pgq:
                    await self._setup_pgqueuer()
                    if not self._pgq:
                        # Failed to setup, retry later
                        await asyncio.sleep(10)
                        continue

                    # 2. Register services on NEW pgq instance
                    for service in self._services.values():
                        self._register_service_on_pgq(service)

                # 3. Run safely
                logger.info(
                    "Starting PGQueuer run loop (services=%d)...", len(self._services)
                )
                if self._pgq:
                    await self._pgq.run()

            except asyncio.CancelledError:
                logger.debug("PGQueuer loop cancelled.")
                break
            except Exception as e:
                logger.error("PGQueuer scheduler crashed: %s. Restarting in 5s...", e)
                # Cleanup to force reconnection
                await self._cleanup_connection()
                await asyncio.sleep(5)

    async def start(self) -> None:
        """Start the scheduler background task."""
        if not self._is_running:
            self._is_running = True
            # Start the resilient loop
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Scheduler started")
        else:
            logger.debug("Application scheduler is already running")

    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self._is_running:
            self._is_running = False
            if self._task:
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task

            await self._cleanup_connection()
            logger.info("Application scheduler stopped")

    # Compatibility method if needed, but we aim to remove direct usage
    def add_job(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        """Deprecated: add_job is not supported in PGQueuer implementation."""
        logger.warning("add_job is deprecated and not supported with PGQueuer.")

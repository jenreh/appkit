"""Comprehensive tests for PGQueuer scheduler implementation."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.scheduler.pgqueuer import PGQueuerScheduler
from appkit_commons.scheduler.scheduler_types import (
    IntervalTrigger,
    ScheduledService,
)


class MockScheduledService(ScheduledService):
    """Mock service for testing."""

    job_id = "test_service"
    name = "Test Service"
    execute_count = 0

    @property
    def trigger(self):
        return IntervalTrigger(minutes=5)

    async def execute(self):
        MockScheduledService.execute_count += 1


class TestPGQueuerSchedulerInit:
    """Test suite for PGQueuerScheduler initialization."""

    def test_pgqueuer_scheduler_init(self) -> None:
        """PGQueuerScheduler initializes with default state."""
        # Act
        scheduler = PGQueuerScheduler()

        # Assert
        assert scheduler._pgq is None
        assert scheduler._is_running is False
        assert scheduler._services == {}
        assert scheduler._conn is None
        assert scheduler._task is None

    def test_pgqueuer_scheduler_is_not_running_initially(self) -> None:
        """PGQueuerScheduler is_running is False initially."""
        # Act
        scheduler = PGQueuerScheduler()

        # Assert
        assert scheduler.is_running is False


class TestPGQueuerSchedulerIsRunning:
    """Test suite for is_running property."""

    def test_is_running_returns_running_state(self) -> None:
        """is_running returns current running state."""
        # Arrange
        scheduler = PGQueuerScheduler()

        # Act & Assert
        assert scheduler.is_running is False
        scheduler._is_running = True
        assert scheduler.is_running is True


class TestPGQueuerSchedulerAddService:
    """Test suite for add_service method."""

    def test_add_service_stores_service(self) -> None:
        """add_service stores service in services dict."""
        # Arrange
        scheduler = PGQueuerScheduler()
        service = MockScheduledService()

        # Act
        scheduler.add_service(service)

        # Assert
        assert "test_service" in scheduler._services
        assert scheduler._services["test_service"] == service

    def test_add_service_multiple_services(self) -> None:
        """add_service can add multiple services."""
        # Arrange
        scheduler = PGQueuerScheduler()
        service1 = MockScheduledService()

        class Service2(ScheduledService):
            job_id = "service2"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=10)

            async def execute(self):
                pass

        service2 = Service2()

        # Act
        scheduler.add_service(service1)
        scheduler.add_service(service2)

        # Assert
        assert len(scheduler._services) == 2
        assert "test_service" in scheduler._services
        assert "service2" in scheduler._services


class TestPGQueuerSchedulerSetupPGQueuer:
    """Test suite for _setup_pgqueuer method."""

    @pytest.mark.asyncio
    async def test_setup_pgqueuer_success(self) -> None:
        """_setup_pgqueuer successfully initializes PGQueuer."""
        # Arrange
        scheduler = PGQueuerScheduler()
        mock_conn = AsyncMock()
        mock_driver = MagicMock()
        mock_pgq = MagicMock()

        # Act
        with (
            patch(
                "appkit_commons.scheduler.pgqueuer.service_registry"
            ) as mock_registry,
            patch(
                "appkit_commons.scheduler.pgqueuer.psycopg.AsyncConnection.connect",
                return_value=mock_conn,
            ),
            patch(
                "appkit_commons.scheduler.pgqueuer.PsycopgDriver",
                return_value=mock_driver,
            ),
            patch(
                "appkit_commons.scheduler.pgqueuer.PgQueuer",
                return_value=mock_pgq,
            ),
        ):
            mock_config = MagicMock()
            mock_config.url = "postgresql://localhost/testdb"
            mock_registry_instance = MagicMock()
            mock_registry_instance.get.return_value = mock_config
            mock_registry.return_value = mock_registry_instance

            await scheduler._setup_pgqueuer()

        # Assert
        assert scheduler._conn is not None
        assert scheduler._pgq is not None

    @pytest.mark.asyncio
    async def test_setup_pgqueuer_connection_failure_logs_error(self, caplog) -> None:
        """_setup_pgqueuer logs error on connection failure."""
        # Arrange
        scheduler = PGQueuerScheduler()

        # Act
        with (
            caplog.at_level(logging.ERROR),
            patch(
                "appkit_commons.scheduler.pgqueuer.service_registry"
            ) as mock_registry,
        ):
            mock_registry.side_effect = Exception("Connection failed")
            await scheduler._setup_pgqueuer()

        # Assert
        assert "Failed to configure PGQueuer" in caplog.text

    @pytest.mark.asyncio
    async def test_setup_pgqueuer_connects_with_keepalive_params(self) -> None:
        """_setup_pgqueuer connects with keepalive settings."""
        # Arrange
        scheduler = PGQueuerScheduler()
        mock_conn = AsyncMock()

        # Act
        with (
            patch(
                "appkit_commons.scheduler.pgqueuer.service_registry"
            ) as mock_registry,
            patch(
                "appkit_commons.scheduler.pgqueuer.psycopg.AsyncConnection.connect",
                return_value=mock_conn,
            ) as mock_connect,
            patch(
                "appkit_commons.scheduler.pgqueuer.PsycopgDriver",
            ),
            patch(
                "appkit_commons.scheduler.pgqueuer.PgQueuer",
            ),
        ):
            mock_config = MagicMock()
            mock_config.url = "postgresql://localhost/testdb"
            mock_registry_instance = MagicMock()
            mock_registry_instance.get.return_value = mock_config
            mock_registry.return_value = mock_registry_instance

            await scheduler._setup_pgqueuer()  # noqa: SLF001

        # Assert - verify keepalive parameters were used
        assert mock_connect.called
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs.get("keepalives") == 1
        assert call_kwargs.get("keepalives_idle") == 20
        assert call_kwargs.get("keepalives_interval") == 5
        assert call_kwargs.get("keepalives_count") == 3


class TestPGQueuerSchedulerRegisterService:
    """Test suite for _register_service_on_pgq method."""

    def test_register_service_on_pgq_no_pgq_instance(self) -> None:
        """_register_service_on_pgq returns early if no PGQueuer instance."""
        # Arrange
        scheduler = PGQueuerScheduler()
        scheduler._pgq = None
        service = MockScheduledService()

        # Act
        result = scheduler._register_service_on_pgq(service)

        # Assert
        assert result is None

    def test_register_service_on_pgq_calls_schedule(self) -> None:
        """_register_service_on_pgq calls schedule on PGQueuer."""
        # Arrange
        scheduler = PGQueuerScheduler()
        scheduler._pgq = MagicMock()
        scheduler._pgq.schedule = MagicMock(return_value=lambda f: f)
        service = MockScheduledService()

        # Act
        scheduler._register_service_on_pgq(service)

        # Assert
        scheduler._pgq.schedule.assert_called_once()


class TestPGQueuerSchedulerCleanup:
    """Test suite for _cleanup_connection method."""

    @pytest.mark.asyncio
    async def test_cleanup_connection_closes_conn(self) -> None:
        """_cleanup_connection closes the database connection."""
        # Arrange
        scheduler = PGQueuerScheduler()
        mock_conn = AsyncMock()
        scheduler._conn = mock_conn
        scheduler._pgq = MagicMock()

        # Act
        await scheduler._cleanup_connection()

        # Assert
        mock_conn.close.assert_called_once()
        assert scheduler._conn is None
        assert scheduler._pgq is None

    @pytest.mark.asyncio
    async def test_cleanup_connection_handles_close_error(self) -> None:
        """_cleanup_connection handles errors when closing."""
        # Arrange
        scheduler = PGQueuerScheduler()
        mock_conn = AsyncMock()
        mock_conn.close.side_effect = Exception("Close error")
        scheduler._conn = mock_conn
        scheduler._pgq = MagicMock()

        # Act & Assert - should not raise
        await scheduler._cleanup_connection()
        assert scheduler._conn is None


class TestPGQueuerSchedulerStartShutdown:
    """Test suite for start and shutdown methods."""

    @pytest.mark.asyncio
    async def test_start_sets_running_state(self) -> None:
        """start() sets _is_running to True."""
        # Arrange
        scheduler = PGQueuerScheduler()

        # Act
        await scheduler.start()

        # Assert
        assert scheduler._is_running is True
        assert scheduler._task is not None

        # Cleanup
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, caplog) -> None:
        """start() logs debug message if already running."""
        # Arrange
        scheduler = PGQueuerScheduler()
        scheduler._is_running = True

        # Act
        with caplog.at_level(logging.DEBUG):
            await scheduler.start()

        # Assert
        assert "already running" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_shutdown_sets_running_state_false(self) -> None:
        """shutdown() sets _is_running to False."""
        # Arrange
        scheduler = PGQueuerScheduler()
        await scheduler.start()

        # Act
        await scheduler.shutdown()

        # Assert
        assert scheduler._is_running is False

    @pytest.mark.asyncio
    async def test_shutdown_cancels_task(self) -> None:
        """shutdown() cancels the running task."""
        # Arrange
        scheduler = PGQueuerScheduler()
        await scheduler.start()
        task = scheduler._task

        # Act
        await scheduler.shutdown()

        # Assert
        assert task is not None
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_shutdown_when_not_running(self, caplog) -> None:
        """shutdown() does nothing if not running."""
        # Arrange
        scheduler = PGQueuerScheduler()

        # Act
        with caplog.at_level(logging.INFO):
            await scheduler.shutdown()

        # Assert - should not raise


class TestPGQueuerSchedulerAddJob:
    """Test suite for add_job (deprecated) method."""

    def test_add_job_logs_warning(self, caplog) -> None:
        """add_job() logs deprecation warning."""
        # Arrange
        scheduler = PGQueuerScheduler()

        # Act
        with caplog.at_level(logging.WARNING):
            scheduler.add_job("test", lambda: None)

        # Assert
        assert "deprecated" in caplog.text.lower()


class TestPGQueuerSchedulerRunLoop:
    """Test suite for _run_loop method."""

    @pytest.mark.asyncio
    async def test_run_loop_cancelled(self) -> None:
        """_run_loop handles cancellation gracefully."""
        # Arrange
        scheduler = PGQueuerScheduler()
        scheduler._is_running = True

        # Create a task and immediately cancel it
        async def run_and_cancel():
            task = asyncio.create_task(scheduler._run_loop())
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Act & Assert - should handle cancellation
        await run_and_cancel()

    @pytest.mark.asyncio
    async def test_run_loop_exits_when_not_running(self) -> None:
        """_run_loop exits when _is_running is False."""
        # Arrange
        scheduler = PGQueuerScheduler()
        scheduler._is_running = False

        # Act
        await scheduler._run_loop()

        # Assert - should complete without errors


class TestPGQueuerSchedulerIntegration:
    """Integration tests for PGQueuerScheduler."""

    def test_scheduler_with_multiple_services(self) -> None:
        """Scheduler can manage multiple services."""
        # Arrange
        scheduler = PGQueuerScheduler()

        class Service1(ScheduledService):
            job_id = "service1"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=5)

            async def execute(self):
                pass

        class Service2(ScheduledService):
            job_id = "service2"

            @property
            def trigger(self):
                return IntervalTrigger(minutes=10)

            async def execute(self):
                pass

        # Act
        scheduler.add_service(Service1())
        scheduler.add_service(Service2())

        # Assert
        assert len(scheduler._services) == 2

    def test_scheduler_service_retrieval(self) -> None:
        """Scheduler can retrieve registered services."""
        # Arrange
        scheduler = PGQueuerScheduler()
        service = MockScheduledService()

        # Act
        scheduler.add_service(service)

        # Assert
        assert scheduler._services["test_service"] is service

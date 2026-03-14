"""Tests for BpmnCleanupService."""

from unittest.mock import AsyncMock, patch

import pytest

from appkit_commons.scheduler import CronTrigger
from appkit_mcp_bpmn.backend.services.bpmn_cleanup_service import BpmnCleanupService
from appkit_mcp_bpmn.configuration import BPMNConfig

pytest_plugins = ["appkit_commons.testing"]


@pytest.fixture
def config(tmp_path) -> BPMNConfig:
    return BPMNConfig(
        storage_dir=str(tmp_path / "bpmn"),
        storage_mode="filesystem",
        cleanup_days_threshold=30,
    )


@pytest.fixture
def service(config: BPMNConfig) -> BpmnCleanupService:
    return BpmnCleanupService(config=config)


def test_job_id(service: BpmnCleanupService) -> None:
    assert service.job_id == "bpmn_cleanup"


def test_trigger_is_cron(service: BpmnCleanupService) -> None:
    trigger = service.trigger
    assert isinstance(trigger, CronTrigger)
    assert trigger.hour == 3
    assert trigger.minute == 34


def test_trigger_cron_expression(service: BpmnCleanupService) -> None:
    assert service.trigger.to_cron() == "34 3 * * *"


@pytest.mark.asyncio
async def test_execute_calls_delete(service: BpmnCleanupService) -> None:
    """execute delegates to storage.delete_older_than_days."""
    mock_storage = AsyncMock()
    mock_storage.delete_older_than_days.return_value = 5

    with patch(
        "appkit_mcp_bpmn.backend.services.bpmn_cleanup_service.create_storage_backend",
        return_value=mock_storage,
    ):
        await service.execute()

    mock_storage.delete_older_than_days.assert_awaited_once_with(30)


@pytest.mark.asyncio
async def test_execute_logs_nothing_when_zero(
    service: BpmnCleanupService, caplog
) -> None:
    """execute logs debug (not info) when 0 diagrams deleted."""
    mock_storage = AsyncMock()
    mock_storage.delete_older_than_days.return_value = 0

    with patch(
        "appkit_mcp_bpmn.backend.services.bpmn_cleanup_service.create_storage_backend",
        return_value=mock_storage,
    ):
        import logging

        with caplog.at_level(logging.INFO):
            await service.execute()

    # No INFO log about deletions — only debug
    info_deletions = [
        r
        for r in caplog.records
        if r.levelno >= logging.INFO and "Deleted" in r.message
    ]
    assert not info_deletions


@pytest.mark.asyncio
async def test_execute_handles_exception(service: BpmnCleanupService) -> None:
    """execute does not propagate exceptions — logs error instead."""
    mock_storage = AsyncMock()
    mock_storage.delete_older_than_days.side_effect = RuntimeError("DB error")

    with patch(
        "appkit_mcp_bpmn.backend.services.bpmn_cleanup_service.create_storage_backend",
        return_value=mock_storage,
    ):
        # Should not raise
        await service.execute()

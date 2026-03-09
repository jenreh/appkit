"""Scheduled cleanup service for deleting old BPMN diagrams.

Provides scheduled cleanup of BPMN diagrams older than a configured
threshold. The scheduler runs once daily at 3:34 AM UTC.
"""

import logging

from appkit_commons.registry import service_registry
from appkit_commons.scheduler import CronTrigger, ScheduledService, Trigger
from appkit_mcp_bpmn.backend.storage.factory import create_storage_backend
from appkit_mcp_bpmn.configuration import BPMNConfig

logger = logging.getLogger(__name__)


class BpmnCleanupService(ScheduledService):
    """Service to clean up old BPMN diagrams from filesystem and/or database."""

    job_id = "bpmn_cleanup"
    name = "Clean up old BPMN diagrams"

    def __init__(self, config: BPMNConfig | None = None) -> None:
        self.config = config or service_registry().get(BPMNConfig)

    @property
    def trigger(self) -> Trigger:
        """Run daily at 3:34 AM UTC."""
        return CronTrigger(hour=3, minute=34)

    async def execute(self) -> None:
        """Run the BPMN diagram cleanup job."""
        try:
            days = self.config.cleanup_days_threshold
            mode = self.config.storage_mode
            logger.info(
                "Running BPMN cleanup job (mode=%s, threshold=%d days)", mode, days
            )

            storage = create_storage_backend(mode, self.config.storage_dir)
            count = await storage.delete_older_than_days(days)

            if count > 0:
                logger.info("Deleted %d BPMN diagrams older than %d days", count, days)
            else:
                logger.debug("No BPMN diagrams older than %d days found", days)

        except Exception as e:
            logger.error("BPMN cleanup job failed: %s", e)

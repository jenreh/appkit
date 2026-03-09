"""Dual-mode BPMN storage backend (saves to filesystem AND database)."""

import logging

from appkit_mcp_bpmn.backend.storage.base import DiagramInfo, StorageBackend
from appkit_mcp_bpmn.backend.storage.database import DatabaseStorageBackend
from appkit_mcp_bpmn.backend.storage.filesystem import FilesystemStorageBackend

logger = logging.getLogger(__name__)


class DualStorageBackend(StorageBackend):
    """Saves and loads diagrams using both filesystem and database backends.

    ``save`` writes to both; ``load`` tries the database first and falls
    back to the filesystem.  ``delete_older_than_days`` runs cleanup on
    both backends and returns the sum.
    """

    def __init__(
        self, fs: FilesystemStorageBackend, db: DatabaseStorageBackend
    ) -> None:
        self._fs = fs
        self._db = db

    async def save(
        self,
        xml: str,
        prompt: str,
        user_id: int,
        diagram_id: str,
        diagram_type: str = "process",
    ) -> DiagramInfo:
        # Filesystem save is synchronous under the hood; run both for atomicity.
        # The DiagramInfo from the filesystem backend is authoritative for URLs.
        info = await self._fs.save(xml, prompt, user_id, diagram_id, diagram_type)
        try:
            await self._db.save(xml, prompt, user_id, diagram_id, diagram_type)
        except Exception:
            logger.exception(
                "DB save failed for diagram %s; filesystem copy still available",
                diagram_id,
            )
        return info

    async def load(self, diagram_id: str, user_id: int) -> str | None:
        xml = await self._db.load(diagram_id, user_id)
        if xml is not None:
            return xml
        logger.debug(
            "Diagram %s not in DB for user %s, trying filesystem", diagram_id, user_id
        )
        return await self._fs.load(diagram_id, user_id)

    async def delete_older_than_days(self, days: int) -> int:
        db_count = await self._db.delete_older_than_days(days)
        fs_count = await self._fs.delete_older_than_days(days)
        total = db_count + fs_count
        logger.debug(
            "Cleanup: %d DB records + %d FS files deleted (threshold: %d days)",
            db_count,
            fs_count,
            days,
        )
        return total

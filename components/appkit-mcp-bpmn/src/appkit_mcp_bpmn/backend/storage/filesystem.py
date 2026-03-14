"""Filesystem-based BPMN diagram storage backend."""

import asyncio
import logging
import time
from pathlib import Path

from appkit_mcp_bpmn.backend.storage.base import DiagramInfo, StorageBackend
from appkit_mcp_bpmn.services.bpmn_storage import (
    _get_storage_dir,
    diagram_exists,
    load_diagram,
    save_diagram,
)

logger = logging.getLogger(__name__)

_DAYS_TO_SECONDS = 86_400


class FilesystemStorageBackend(StorageBackend):
    """Stores BPMN diagrams as ``.bpmn`` files on the local filesystem.

    The ``user_id`` and ``prompt`` parameters are accepted by the interface
    but are not used for filesystem storage — there is a single flat
    directory shared across all users (matching the legacy behaviour).
    """

    def __init__(self, storage_dir: str) -> None:
        self._storage_dir = storage_dir

    async def save(
        self,
        xml: str,
        prompt: str,  # noqa: ARG002
        user_id: int,  # noqa: ARG002
        diagram_id: str,
        diagram_type: str = "process",  # noqa: ARG002
    ) -> DiagramInfo:
        info = save_diagram(xml, self._storage_dir, diagram_id=diagram_id)
        return DiagramInfo(
            id=info["id"],
            download_url=info["download_url"],
            view_url=info["view_url"],
        )

    async def load(self, diagram_id: str, user_id: int) -> str | None:  # noqa: ARG002
        return load_diagram(diagram_id, self._storage_dir)

    async def update(
        self,
        diagram_id: str,
        user_id: int,  # noqa: ARG002
        xml: str,
    ) -> bool:
        if not diagram_exists(diagram_id, self._storage_dir):
            return False
        save_diagram(xml, self._storage_dir, diagram_id=diagram_id)
        return True

    async def rename(
        self,
        diagram_id: str,
        user_id: int,  # noqa: ARG002
        name: str,  # noqa: ARG002
    ) -> bool:
        # Filesystem doesn't store names; return True only if diagram exists.
        return diagram_exists(diagram_id, self._storage_dir)

    async def delete_older_than_days(self, days: int) -> int:
        """Delete ``.bpmn`` files whose mtime is older than *days*."""
        return await asyncio.to_thread(self._sync_delete_older_than_days, days)

    def _sync_delete_older_than_days(self, days: int) -> int:
        """Synchronous implementation of filesystem cleanup."""
        cutoff = time.time() - days * _DAYS_TO_SECONDS
        directory = _get_storage_dir(self._storage_dir)
        count = 0
        for bpmn_file in Path(directory).glob("*.bpmn"):
            if bpmn_file.stat().st_mtime < cutoff:
                bpmn_file.unlink(missing_ok=True)
                count += 1
                logger.debug("Deleted old BPMN file: %s", bpmn_file.name)
        logger.debug("Deleted %d old BPMN files (older than %d days)", count, days)
        return count

"""Database-backed BPMN diagram storage backend."""

import logging

from appkit_commons.database.session import get_asyncdb_session
from appkit_mcp_bpmn.backend.repository import bpmn_diagram_repo
from appkit_mcp_bpmn.backend.storage.base import DiagramInfo, StorageBackend

logger = logging.getLogger(__name__)

_DOWNLOAD_URL_TEMPLATE = "/api/bpmn/diagrams/{id}/xml"
_VIEW_URL_TEMPLATE = "/api/bpmn/diagrams/{id}/view"


class DatabaseStorageBackend(StorageBackend):
    """Stores BPMN diagrams as XML blobs in the PostgreSQL database.

    Diagrams are user-scoped: ``load`` only returns a record when the
    ``user_id`` matches the one used during ``save``.
    """

    async def save(
        self,
        xml: str,
        prompt: str,
        user_id: int,
        diagram_id: str,
        diagram_type: str = "process",
    ) -> DiagramInfo:
        logger.info(
            "DatabaseStorageBackend.save called: diagram_id=%s user_id=%s",
            diagram_id,
            user_id,
        )
        async with get_asyncdb_session() as session:
            await bpmn_diagram_repo.save_diagram(
                session,
                diagram_id=diagram_id,
                user_id=user_id,
                xml=xml,
                prompt=prompt,
                diagram_type=diagram_type,
            )
        logger.info("DatabaseStorageBackend.save committed: %s", diagram_id)
        return DiagramInfo(
            id=diagram_id,
            download_url=_DOWNLOAD_URL_TEMPLATE.format(id=diagram_id),
            view_url=_VIEW_URL_TEMPLATE.format(id=diagram_id),
        )

    async def load(self, diagram_id: str, user_id: int) -> str | None:
        async with get_asyncdb_session() as session:
            return await bpmn_diagram_repo.load_xml(session, diagram_id, user_id)

    async def delete_older_than_days(self, days: int) -> int:
        async with get_asyncdb_session() as session:
            return await bpmn_diagram_repo.soft_delete_older_than_days(session, days)

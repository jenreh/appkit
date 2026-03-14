"""Repository for BPMN diagram database operations."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from appkit_commons.database.base_repository import BaseRepository
from appkit_mcp_bpmn.backend.models import BpmnDiagram

logger = logging.getLogger(__name__)


class BpmnDiagramRepository(BaseRepository[BpmnDiagram, AsyncSession]):
    """Repository class for BPMN diagram database operations."""

    @property
    def model_class(self) -> type[BpmnDiagram]:
        return BpmnDiagram

    async def find_by_diagram_id(
        self, session: AsyncSession, diagram_id: str, user_id: int
    ) -> BpmnDiagram | None:
        """Retrieve a diagram by its UUID for a specific user.

        Defers loading of xml_content to avoid fetching large blobs upfront.
        """
        stmt = (
            select(BpmnDiagram)
            .options(defer(BpmnDiagram.xml_content))
            .where(
                BpmnDiagram.diagram_id == diagram_id,
                BpmnDiagram.user_id == user_id,
                ~BpmnDiagram.is_deleted,
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def load_xml(
        self, session: AsyncSession, diagram_id: str, user_id: int
    ) -> str | None:
        """Load the raw XML blob for a diagram (user-scoped).

        Returns:
            Decoded XML string or None if not found / already deleted.
        """
        stmt = select(BpmnDiagram).where(
            BpmnDiagram.diagram_id == diagram_id,
            BpmnDiagram.user_id == user_id,
            ~BpmnDiagram.is_deleted,
        )
        result = await session.execute(stmt)
        diagram = result.scalars().first()
        if diagram:
            return diagram.xml_content.decode("utf-8")
        return None

    async def save_diagram(
        self,
        session: AsyncSession,
        *,
        diagram_id: str,
        user_id: int,
        xml: str,
        prompt: str,
        name: str = "",
        diagram_type: str = "process",
    ) -> BpmnDiagram:
        """Persist a new BPMN diagram record.

        Returns:
            The newly created and flushed BpmnDiagram entity.
        """
        resolved_name = (
            name.strip()
            if name and name.strip()
            else (
                prompt.strip()[:128]
                if prompt and prompt.strip()
                else f"Diagram {diagram_id[:8]}"
            )
        )
        diagram = BpmnDiagram(
            diagram_id=diagram_id,
            user_id=user_id,
            name=resolved_name,
            xml_content=xml.encode("utf-8"),
            prompt=prompt,
            diagram_type=diagram_type,
            is_deleted=False,
        )
        session.add(diagram)
        await session.flush()
        logger.debug(
            "Saved BPMN diagram: id=%s user=%s type=%s",
            diagram_id,
            user_id,
            diagram_type,
        )
        return diagram

    async def update_xml(
        self, session: AsyncSession, diagram_id: str, user_id: int, xml: str
    ) -> bool:
        """Update the XML content of an existing diagram (user-scoped).

        Returns:
            True if the record was found and updated, False otherwise.
        """
        stmt = select(BpmnDiagram).where(
            BpmnDiagram.diagram_id == diagram_id,
            BpmnDiagram.user_id == user_id,
            ~BpmnDiagram.is_deleted,
        )
        result = await session.execute(stmt)
        diagram = result.scalars().first()
        if diagram:
            diagram.xml_content = xml.encode("utf-8")
            await session.flush()
            logger.debug("Updated BPMN diagram XML: %s", diagram_id)
            return True
        logger.warning("BPMN diagram %s not found for user %s", diagram_id, user_id)
        return False

    async def update_name(
        self, session: AsyncSession, diagram_id: str, user_id: int, name: str
    ) -> bool:
        """Update the name of an existing diagram (user-scoped).

        Returns:
            True if the record was found and updated, False otherwise.
        """
        stmt = select(BpmnDiagram).where(
            BpmnDiagram.diagram_id == diagram_id,
            BpmnDiagram.user_id == user_id,
            ~BpmnDiagram.is_deleted,
        )
        result = await session.execute(stmt)
        diagram = result.scalars().first()
        if diagram:
            diagram.name = name
            await session.flush()
            logger.debug("Updated BPMN diagram name: %s -> %s", diagram_id, name)
            return True
        logger.warning("BPMN diagram %s not found for user %s", diagram_id, user_id)
        return False

    async def soft_delete_by_diagram_id(
        self, session: AsyncSession, diagram_id: str, user_id: int
    ) -> bool:
        """Mark a single diagram as deleted (user-scoped).

        Returns:
            True if the record was found and updated, False otherwise.
        """
        stmt = select(BpmnDiagram).where(
            BpmnDiagram.diagram_id == diagram_id,
            BpmnDiagram.user_id == user_id,
        )
        result = await session.execute(stmt)
        diagram = result.scalars().first()
        if diagram:
            diagram.is_deleted = True
            diagram.xml_content = b""
            await session.flush()
            logger.debug("Soft-deleted BPMN diagram: %s", diagram_id)
            return True
        logger.warning("BPMN diagram %s not found for user %s", diagram_id, user_id)
        return False

    async def soft_delete_older_than_days(
        self, session: AsyncSession, days: int
    ) -> int:
        """Soft-delete all diagrams older than ``days`` days (all users).

        Sets is_deleted=True and clears xml_content to save space.

        Returns:
            Count of records updated.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(BpmnDiagram).where(
            BpmnDiagram.created < cutoff,
            ~BpmnDiagram.is_deleted,
        )
        result = await session.execute(stmt)
        diagrams = list(result.scalars().all())
        for diagram in diagrams:
            diagram.is_deleted = True
            diagram.xml_content = b""
        await session.flush()
        count = len(diagrams)
        logger.debug("Soft-deleted %d BPMN diagrams older than %d days", count, days)
        return count

    async def list_deleted_diagram_ids(
        self, session: AsyncSession, older_than_days: int
    ) -> list[str]:
        """Return diagram IDs that were soft-deleted more than ``older_than_days`` ago.

        Used by cleanup to find corresponding filesystem files to remove.
        """
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        stmt = select(BpmnDiagram.diagram_id).where(
            BpmnDiagram.is_deleted,
            BpmnDiagram.updated < cutoff,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


bpmn_diagram_repo = BpmnDiagramRepository()

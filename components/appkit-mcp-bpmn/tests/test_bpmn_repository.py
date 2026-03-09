"""Tests for BpmnDiagramRepository."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_mcp_bpmn.backend.models import BpmnDiagram
from appkit_mcp_bpmn.backend.repository import BpmnDiagramRepository

pytest_plugins = ["appkit_commons.testing"]

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
  <bpmn:process id="P1">
    <bpmn:startEvent id="S" /><bpmn:endEvent id="E" />
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.fixture
def repo() -> BpmnDiagramRepository:
    return BpmnDiagramRepository()


@pytest_asyncio.fixture
async def saved_diagram(
    repo: BpmnDiagramRepository, async_session: AsyncSession
) -> BpmnDiagram:
    """Persist a single diagram and return the entity."""
    return await repo.save_diagram(
        async_session,
        diagram_id="aaaa-bbbb-1111",
        user_id=42,
        xml=SAMPLE_XML,
        prompt="Test workflow",
        diagram_type="process",
    )


@pytest.mark.asyncio
async def test_save_and_load_xml(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
    saved_diagram: BpmnDiagram,
) -> None:
    """XML round-trips through save → load correctly."""
    xml = await repo.load_xml(async_session, "aaaa-bbbb-1111", user_id=42)
    assert xml == SAMPLE_XML


@pytest.mark.asyncio
async def test_load_wrong_user_returns_none(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
    saved_diagram: BpmnDiagram,
) -> None:
    """load_xml returns None when user_id does not match."""
    xml = await repo.load_xml(async_session, "aaaa-bbbb-1111", user_id=99)
    assert xml is None


@pytest.mark.asyncio
async def test_find_by_diagram_id(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
    saved_diagram: BpmnDiagram,
) -> None:
    """find_by_diagram_id returns the record without the xml_content blob."""
    record = await repo.find_by_diagram_id(async_session, "aaaa-bbbb-1111", user_id=42)
    assert record is not None
    assert record.diagram_id == "aaaa-bbbb-1111"
    assert record.prompt == "Test workflow"


@pytest.mark.asyncio
async def test_soft_delete_by_diagram_id(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
    saved_diagram: BpmnDiagram,
) -> None:
    """soft_delete_by_diagram_id sets is_deleted and clears xml_content."""
    deleted = await repo.soft_delete_by_diagram_id(
        async_session, "aaaa-bbbb-1111", user_id=42
    )
    assert deleted is True

    # Record still exists
    record = await repo.find_by_diagram_id(async_session, "aaaa-bbbb-1111", user_id=42)
    assert record is None  # excluded by ~is_deleted filter

    # load_xml now returns None
    xml = await repo.load_xml(async_session, "aaaa-bbbb-1111", user_id=42)
    assert xml is None


@pytest.mark.asyncio
async def test_soft_delete_wrong_user_returns_false(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
    saved_diagram: BpmnDiagram,
) -> None:
    """soft_delete_by_diagram_id returns False for wrong user."""
    deleted = await repo.soft_delete_by_diagram_id(
        async_session, "aaaa-bbbb-1111", user_id=999
    )
    assert deleted is False


@pytest.mark.asyncio
async def test_soft_delete_older_than_days(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
) -> None:
    """soft_delete_older_than_days deletes records older than threshold."""
    old_time = datetime.now(UTC) - timedelta(days=100)

    # Save an old record
    diagram = await repo.save_diagram(
        async_session,
        diagram_id="old-diagram-id",
        user_id=1,
        xml=SAMPLE_XML,
        prompt="Old workflow",
    )
    # Manually backdate created
    diagram.created = old_time
    await async_session.flush()

    # Save a recent record (should NOT be deleted)
    await repo.save_diagram(
        async_session,
        diagram_id="new-diagram-id",
        user_id=1,
        xml=SAMPLE_XML,
        prompt="New workflow",
    )

    count = await repo.soft_delete_older_than_days(async_session, days=90)
    assert count == 1

    # Old record is deleted, new one survives
    old = await repo.load_xml(async_session, "old-diagram-id", user_id=1)
    new = await repo.load_xml(async_session, "new-diagram-id", user_id=1)
    assert old is None
    assert new == SAMPLE_XML


@pytest.mark.asyncio
async def test_list_deleted_diagram_ids(
    repo: BpmnDiagramRepository,
    async_session: AsyncSession,
) -> None:
    """list_deleted_diagram_ids returns IDs of old deleted records."""
    old_time = datetime.now(UTC) - timedelta(days=200)

    diagram = await repo.save_diagram(
        async_session,
        diagram_id="deleted-old-id",
        user_id=5,
        xml=SAMPLE_XML,
        prompt="Stale",
    )
    diagram.is_deleted = True
    diagram.updated = old_time
    await async_session.flush()

    ids = await repo.list_deleted_diagram_ids(async_session, older_than_days=90)
    assert "deleted-old-id" in ids

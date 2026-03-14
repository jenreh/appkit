from unittest.mock import AsyncMock, patch

import pytest

from appkit_mcp_bpmn.backend.storage.base import DiagramInfo
from appkit_mcp_bpmn.backend.storage.database import DatabaseStorageBackend

pytest_plugins = ["appkit_commons.testing"]

SAMPLE_XML = "<bpmn></bpmn>"
DIAGRAM_ID = "test-uuid-1234"
USER_ID = 7


@pytest.fixture
def db_backend() -> DatabaseStorageBackend:
    return DatabaseStorageBackend()


@pytest.mark.asyncio
@patch("appkit_mcp_bpmn.backend.storage.database.bpmn_diagram_repo")
@patch("appkit_mcp_bpmn.backend.storage.database.get_asyncdb_session")
async def test_database_save(
    mock_session, mock_repo, db_backend: DatabaseStorageBackend
) -> None:
    mock_session_ctx = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_session_ctx

    mock_repo.save_diagram = AsyncMock()

    info = await db_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)

    assert isinstance(info, DiagramInfo)
    assert info.id == DIAGRAM_ID
    assert DIAGRAM_ID in info.download_url
    assert DIAGRAM_ID in info.view_url

    mock_repo.save_diagram.assert_awaited_once_with(
        mock_session_ctx,
        diagram_id=DIAGRAM_ID,
        user_id=USER_ID,
        xml=SAMPLE_XML,
        prompt="prompt",
        diagram_type="process",
    )


@pytest.mark.asyncio
@patch("appkit_mcp_bpmn.backend.storage.database.bpmn_diagram_repo")
@patch("appkit_mcp_bpmn.backend.storage.database.get_asyncdb_session")
async def test_database_load(
    mock_session, mock_repo, db_backend: DatabaseStorageBackend
) -> None:
    mock_session_ctx = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_session_ctx

    mock_repo.load_xml = AsyncMock(return_value=SAMPLE_XML)

    xml = await db_backend.load(DIAGRAM_ID, USER_ID)

    assert xml == SAMPLE_XML
    mock_repo.load_xml.assert_awaited_once_with(mock_session_ctx, DIAGRAM_ID, USER_ID)


@pytest.mark.asyncio
@patch("appkit_mcp_bpmn.backend.storage.database.bpmn_diagram_repo")
@patch("appkit_mcp_bpmn.backend.storage.database.get_asyncdb_session")
async def test_database_delete_older_than_days(
    mock_session, mock_repo, db_backend: DatabaseStorageBackend
) -> None:
    mock_session_ctx = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_session_ctx

    mock_repo.soft_delete_older_than_days = AsyncMock(return_value=5)

    count = await db_backend.delete_older_than_days(days=90)

    assert count == 5
    mock_repo.soft_delete_older_than_days.assert_awaited_once_with(mock_session_ctx, 90)

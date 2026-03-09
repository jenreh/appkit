"""Tests for BPMN storage backends and factory."""

import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from appkit_mcp_bpmn.backend.storage.base import DiagramInfo, StorageBackend
from appkit_mcp_bpmn.backend.storage.dual import DualStorageBackend
from appkit_mcp_bpmn.backend.storage.factory import create_storage_backend
from appkit_mcp_bpmn.backend.storage.filesystem import FilesystemStorageBackend

pytest_plugins = ["appkit_commons.testing"]

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
  <bpmn:process id="P1">
    <bpmn:startEvent id="S" /><bpmn:endEvent id="E" />
  </bpmn:process>
</bpmn:definitions>
"""
DIAGRAM_ID = "test-uuid-1234"
USER_ID = 7


# ---------------------------------------------------------------------------
# FilesystemStorageBackend
# ---------------------------------------------------------------------------


@pytest.fixture
def fs_backend(tmp_path: Path) -> FilesystemStorageBackend:
    return FilesystemStorageBackend(str(tmp_path / "bpmn"))


@pytest.mark.asyncio
async def test_filesystem_save_returns_info(
    fs_backend: FilesystemStorageBackend,
) -> None:
    info = await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)
    assert isinstance(info, DiagramInfo)
    assert info.id == DIAGRAM_ID
    assert DIAGRAM_ID in info.download_url
    assert DIAGRAM_ID in info.view_url


@pytest.mark.asyncio
async def test_filesystem_save_creates_file(
    fs_backend: FilesystemStorageBackend, tmp_path: Path
) -> None:
    await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)
    bpmn_file = tmp_path / "bpmn" / f"{DIAGRAM_ID}.bpmn"
    assert bpmn_file.is_file()
    assert bpmn_file.read_text(encoding="utf-8") == SAMPLE_XML


@pytest.mark.asyncio
async def test_filesystem_load_returns_xml(
    fs_backend: FilesystemStorageBackend,
) -> None:
    await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)
    xml = await fs_backend.load(DIAGRAM_ID, USER_ID)
    assert xml == SAMPLE_XML


@pytest.mark.asyncio
async def test_filesystem_load_returns_none_for_missing(
    fs_backend: FilesystemStorageBackend,
) -> None:
    xml = await fs_backend.load("nonexistent-id", USER_ID)
    assert xml is None


@pytest.mark.asyncio
async def test_filesystem_load_ignores_user_id(
    fs_backend: FilesystemStorageBackend,
) -> None:
    """Filesystem backend is not user-scoped; any user_id loads the file."""
    await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)
    xml = await fs_backend.load(DIAGRAM_ID, user_id=999)
    assert xml == SAMPLE_XML


@pytest.mark.asyncio
async def test_filesystem_delete_older_than_days(
    fs_backend: FilesystemStorageBackend, tmp_path: Path
) -> None:
    """delete_older_than_days removes .bpmn files older than threshold."""
    await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)

    bpmn_file = tmp_path / "bpmn" / f"{DIAGRAM_ID}.bpmn"
    assert bpmn_file.is_file()

    # Backdate mtime to 100 days ago
    old_mtime = time.time() - 100 * 86_400
    import os

    os.utime(bpmn_file, (old_mtime, old_mtime))

    count = await fs_backend.delete_older_than_days(days=90)
    assert count == 1
    assert not bpmn_file.is_file()


@pytest.mark.asyncio
async def test_filesystem_delete_skips_recent_files(
    fs_backend: FilesystemStorageBackend, tmp_path: Path
) -> None:
    """delete_older_than_days does not delete recently created files."""
    await fs_backend.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)

    count = await fs_backend.delete_older_than_days(days=90)
    assert count == 0
    bpmn_file = tmp_path / "bpmn" / f"{DIAGRAM_ID}.bpmn"
    assert bpmn_file.is_file()


# ---------------------------------------------------------------------------
# DualStorageBackend
# ---------------------------------------------------------------------------


def _make_mock_backend(xml: str | None = SAMPLE_XML) -> AsyncMock:
    """Create a mock StorageBackend."""
    mock = AsyncMock(spec=StorageBackend)
    mock.save.return_value = DiagramInfo(
        id=DIAGRAM_ID,
        download_url=f"/api/bpmn/diagrams/{DIAGRAM_ID}/xml",
        view_url=f"/api/bpmn/diagrams/{DIAGRAM_ID}/view",
    )
    mock.load.return_value = xml
    mock.delete_older_than_days.return_value = 2
    return mock


@pytest.mark.asyncio
async def test_dual_save_calls_both_backends() -> None:
    fs_mock = _make_mock_backend()
    db_mock = _make_mock_backend()
    dual = DualStorageBackend(fs=fs_mock, db=db_mock)

    info = await dual.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)

    fs_mock.save.assert_awaited_once()
    db_mock.save.assert_awaited_once()
    assert info.id == DIAGRAM_ID


@pytest.mark.asyncio
async def test_dual_save_continues_if_db_fails() -> None:
    """DualStorageBackend still returns FS info when DB raises."""
    fs_mock = _make_mock_backend()
    db_mock = _make_mock_backend()
    db_mock.save.side_effect = RuntimeError("DB unavailable")

    dual = DualStorageBackend(fs=fs_mock, db=db_mock)
    info = await dual.save(SAMPLE_XML, "prompt", USER_ID, DIAGRAM_ID)

    assert info.id == DIAGRAM_ID  # FS info returned despite DB error


@pytest.mark.asyncio
async def test_dual_load_prefers_db() -> None:
    fs_mock = _make_mock_backend(xml=None)
    db_mock = _make_mock_backend(xml=SAMPLE_XML)
    dual = DualStorageBackend(fs=fs_mock, db=db_mock)

    xml = await dual.load(DIAGRAM_ID, USER_ID)
    assert xml == SAMPLE_XML
    db_mock.load.assert_awaited_once()
    fs_mock.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_dual_load_falls_back_to_fs() -> None:
    fs_mock = _make_mock_backend(xml=SAMPLE_XML)
    db_mock = _make_mock_backend(xml=None)
    dual = DualStorageBackend(fs=fs_mock, db=db_mock)

    xml = await dual.load(DIAGRAM_ID, USER_ID)
    assert xml == SAMPLE_XML
    db_mock.load.assert_awaited_once()
    fs_mock.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_dual_delete_sums_both_counts() -> None:
    fs_mock = _make_mock_backend()
    db_mock = _make_mock_backend()
    fs_mock.delete_older_than_days.return_value = 3
    db_mock.delete_older_than_days.return_value = 5
    dual = DualStorageBackend(fs=fs_mock, db=db_mock)

    total = await dual.delete_older_than_days(days=90)
    assert total == 8


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_filesystem(tmp_path: Path) -> None:
    backend = create_storage_backend("filesystem", str(tmp_path))
    assert isinstance(backend, FilesystemStorageBackend)


def test_factory_database(tmp_path: Path) -> None:
    from appkit_mcp_bpmn.backend.storage.database import DatabaseStorageBackend

    backend = create_storage_backend("database", str(tmp_path))
    assert isinstance(backend, DatabaseStorageBackend)


def test_factory_both(tmp_path: Path) -> None:
    backend = create_storage_backend("both", str(tmp_path))
    assert isinstance(backend, DualStorageBackend)


def test_factory_invalid_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown storage mode"):
        create_storage_backend("invalid", str(tmp_path))  # type: ignore[arg-type]

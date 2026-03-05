"""Tests for BPMN diagram storage service."""

import uuid
from pathlib import Path

import pytest

from appkit_mcp_bpmn.services.bpmn_storage import (
    diagram_exists,
    get_diagram_path,
    load_diagram,
    save_diagram,
)


@pytest.fixture
def tmp_storage(tmp_path: Path) -> str:
    """Return a temporary storage directory path."""
    storage = tmp_path / "bpmn_files"
    storage.mkdir()
    return str(storage)


SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="Start" />
    <bpmn:endEvent id="End" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_save_diagram_creates_file(tmp_storage: str) -> None:
    """save_diagram writes a .bpmn file and returns metadata."""
    result = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)

    assert "id" in result
    assert "download_url" in result
    assert "view_url" in result

    file_path = Path(tmp_storage) / f"{result['id']}.bpmn"
    assert file_path.is_file()
    assert file_path.read_text(encoding="utf-8") == SAMPLE_XML


def test_save_diagram_unique_ids(tmp_storage: str) -> None:
    """Each save produces a unique diagram ID."""
    r1 = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)
    r2 = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)

    assert r1["id"] != r2["id"]
    # Both should be valid UUIDs
    uuid.UUID(r1["id"])
    uuid.UUID(r2["id"])


def test_save_diagram_creates_directory(tmp_path: Path) -> None:
    """save_diagram creates the storage directory if it does not exist."""
    storage = str(tmp_path / "new_dir" / "bpmn")
    result = save_diagram(SAMPLE_XML, storage_dir=storage)

    assert Path(storage).is_dir()
    assert (Path(storage) / f"{result['id']}.bpmn").is_file()


def test_get_diagram_path(tmp_storage: str) -> None:
    """get_diagram_path returns the expected path."""
    diagram_id = "test-uuid-1234"
    path = get_diagram_path(diagram_id, storage_dir=tmp_storage)

    assert path == Path(tmp_storage) / "test-uuid-1234.bpmn"


def test_diagram_exists_true(tmp_storage: str) -> None:
    """diagram_exists returns True for saved diagrams."""
    result = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)
    assert diagram_exists(result["id"], storage_dir=tmp_storage) is True


def test_diagram_exists_false(tmp_storage: str) -> None:
    """diagram_exists returns False for non-existent diagrams."""
    assert diagram_exists("nonexistent-id", storage_dir=tmp_storage) is False


def test_load_diagram_success(tmp_storage: str) -> None:
    """load_diagram returns XML content for existing diagrams."""
    result = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)
    loaded = load_diagram(result["id"], storage_dir=tmp_storage)

    assert loaded == SAMPLE_XML


def test_load_diagram_not_found(tmp_storage: str) -> None:
    """load_diagram returns None for missing diagrams."""
    assert load_diagram("does-not-exist", storage_dir=tmp_storage) is None


def test_save_diagram_urls_contain_id(tmp_storage: str) -> None:
    """URLs in the result contain the diagram ID."""
    result = save_diagram(SAMPLE_XML, storage_dir=tmp_storage)
    diagram_id = result["id"]

    assert diagram_id in result["download_url"]
    assert diagram_id in result["view_url"]

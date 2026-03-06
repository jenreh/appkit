"""Filesystem storage for BPMN diagrams."""

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_storage_dir(storage_dir: str) -> Path:
    """Return the storage directory, creating it if necessary."""
    path = Path(storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_diagram(
    xml: str,
    storage_dir: str,
) -> dict[str, str]:
    """Save BPMN XML to the filesystem with a unique ID.

    Args:
        xml: Validated BPMN 2.0 XML string.
        storage_dir: Base directory for diagram storage.

    Returns:
        Dict with ``id``, ``download_url``, and ``view_url``.

    Raises:
        OSError: If the file cannot be written.
    """
    diagram_id = str(uuid.uuid4())
    directory = _get_storage_dir(storage_dir)
    file_path = directory / f"{diagram_id}.bpmn"

    file_path.write_text(xml, encoding="utf-8")
    logger.info("Saved BPMN diagram: %s", file_path)

    return {
        "id": diagram_id,
        "download_url": f"/api/bpmn/diagrams/{diagram_id}/xml",
        "view_url": f"/api/bpmn/diagrams/{diagram_id}/view",
    }


def get_diagram_path(
    diagram_id: str,
    storage_dir: str,
) -> Path:
    """Return the filesystem path for a diagram.

    Args:
        diagram_id: UUID of the diagram.
        storage_dir: Base directory for diagram storage.

    Returns:
        Path to the ``.bpmn`` file.
    """
    return _get_storage_dir(storage_dir) / f"{diagram_id}.bpmn"


def diagram_exists(
    diagram_id: str,
    storage_dir: str,
) -> bool:
    """Check whether a diagram file exists on disk.

    Args:
        diagram_id: UUID of the diagram.
        storage_dir: Base directory for diagram storage.

    Returns:
        True if the file exists.
    """
    return get_diagram_path(diagram_id, storage_dir).is_file()


def load_diagram(
    diagram_id: str,
    storage_dir: str,
) -> str | None:
    """Load BPMN XML from disk.

    Args:
        diagram_id: UUID of the diagram.
        storage_dir: Base directory for diagram storage.

    Returns:
        XML string or None if not found.
    """
    path = get_diagram_path(diagram_id, storage_dir)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")

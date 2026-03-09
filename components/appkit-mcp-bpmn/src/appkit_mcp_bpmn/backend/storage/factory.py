"""Factory for creating BPMN storage backends from configuration."""

from typing import Literal

from appkit_mcp_bpmn.backend.storage.base import StorageBackend
from appkit_mcp_bpmn.backend.storage.database import DatabaseStorageBackend
from appkit_mcp_bpmn.backend.storage.dual import DualStorageBackend
from appkit_mcp_bpmn.backend.storage.filesystem import FilesystemStorageBackend

StorageMode = Literal["filesystem", "database", "both"]


def create_storage_backend(
    mode: StorageMode,
    storage_dir: str,
) -> StorageBackend:
    """Return a :class:`StorageBackend` matching ``mode``.

    Args:
        mode: One of ``"filesystem"``, ``"database"``, or ``"both"``.
        storage_dir: Base filesystem directory (used by FS and dual backends).

    Returns:
        A concrete :class:`StorageBackend` instance.

    Raises:
        ValueError: If ``mode`` is not a recognised value.
    """
    if mode == "filesystem":
        return FilesystemStorageBackend(storage_dir)
    if mode == "database":
        return DatabaseStorageBackend()
    if mode == "both":
        return DualStorageBackend(
            fs=FilesystemStorageBackend(storage_dir),
            db=DatabaseStorageBackend(),
        )
    raise ValueError(
        f"Unknown storage mode '{mode}'. Must be one of: filesystem, database, both."
    )

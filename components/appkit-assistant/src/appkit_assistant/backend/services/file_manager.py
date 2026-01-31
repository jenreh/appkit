"""File management utilities for assistant uploads.

This module provides utilities for managing uploaded files in user-specific
directories. Files are stored temporarily and cleaned up after processing.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory for uploaded files (relative to project root)
UPLOAD_BASE_DIR = Path("uploaded_files")


def get_user_upload_directory(user_id: str) -> Path:
    """Get the upload directory for a specific user.

    Creates the directory if it doesn't exist.

    Args:
        user_id: The user's unique identifier.

    Returns:
        Path to the user's upload directory.
    """
    user_dir = UPLOAD_BASE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("User upload dir: %s", user_dir)
    return user_dir


def _make_unique_filename(target_path: Path) -> Path:
    """Generate a unique filename if target already exists.

    Appends _1, _2, etc. before the extension until a unique name is found.

    Args:
        target_path: The desired file path.

    Returns:
        A unique file path that doesn't exist yet.
    """
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 1

    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def move_to_user_directory(temp_path: str, user_id: str) -> str:
    """Move a file from temporary location to user's upload directory.

    Args:
        temp_path: Path to the temporary file (from browser upload).
        user_id: The user's unique identifier.

    Returns:
        Absolute path to the file in the user's directory.

    Raises:
        FileNotFoundError: If the source file doesn't exist.
    """
    source = Path(temp_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {temp_path}")

    user_dir = get_user_upload_directory(user_id)
    target = user_dir / source.name
    target = _make_unique_filename(target)

    shutil.move(str(source), str(target))
    logger.info("Moved file to user directory: %s → %s", temp_path, target)

    return str(target.absolute())


def cleanup_uploaded_files(file_paths: list[str]) -> None:
    """Delete uploaded files from disk.

    Args:
        file_paths: List of absolute file paths to delete.
    """
    deleted_count = 0
    for file_path in file_paths:
        try:
            Path(file_path).unlink(missing_ok=True)
            deleted_count += 1
        except OSError as e:
            logger.warning("Failed to delete file %s: %s", file_path, e)

    logger.debug("Cleaned up %d uploaded files", deleted_count)


def get_file_size(file_path: str) -> int:
    """Get the size of a file in bytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in bytes, or 0 if file doesn't exist.
    """
    try:
        return Path(file_path).stat().st_size
    except OSError:
        return 0

"""File validation service for AI processors.

Provides file type, size, and extension validation utilities
shared across all processors that handle file uploads.
"""

import logging
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)


class FileValidationService:
    """Service for validating files before upload to AI APIs."""

    # Max file size (5MB)
    MAX_FILE_SIZE: Final[int] = 5 * 1024 * 1024

    # Allowed file extensions
    ALLOWED_EXTENSIONS: Final[set[str]] = {
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "xlsx",
        "csv",
        "docx",
        "pptx",
        "md",
    }

    # Image extensions (for determining content type)
    IMAGE_EXTENSIONS: Final[set[str]] = {"png", "jpg", "jpeg", "gif", "webp"}

    # MIME type mapping
    MEDIA_TYPES: Final[dict[str, str]] = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        "pptx": (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        "md": "text/markdown",
        "txt": "text/plain",
    }

    def get_file_extension(self, file_path: str) -> str:
        """Extract file extension from path.

        Args:
            file_path: Path to the file

        Returns:
            Lowercase file extension without the dot, or empty string
        """
        return file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    def is_image_file(self, file_path: str) -> bool:
        """Check if file is an image based on extension.

        Args:
            file_path: Path to the file

        Returns:
            True if file has an image extension
        """
        ext = self.get_file_extension(file_path)
        return ext in self.IMAGE_EXTENSIONS

    def get_media_type(self, file_path: str) -> str:
        """Get MIME type for a file based on extension.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string, defaults to application/octet-stream
        """
        ext = self.get_file_extension(file_path)
        return self.MEDIA_TYPES.get(ext, "application/octet-stream")

    def validate_file(self, file_path: str) -> tuple[bool, str]:
        """Validate file for upload.

        Checks:
        - File exists
        - Extension is allowed
        - File size is within limits

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return False, f"File not found: {file_path}"

        # Check extension
        ext = self.get_file_extension(file_path)
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type: {ext}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            return False, f"File too large: {size_mb:.1f}MB (max 5MB)"

        return True, ""


# Singleton instance for convenience
_file_validation_service: FileValidationService | None = None


def get_file_validation_service() -> FileValidationService:
    """Get or create the file validation service singleton.

    Returns:
        The FileValidationService instance
    """
    global _file_validation_service
    if _file_validation_service is None:
        _file_validation_service = FileValidationService()
    return _file_validation_service

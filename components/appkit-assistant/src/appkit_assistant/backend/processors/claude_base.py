"""
Claude base processor for generating AI responses using Anthropic's Claude API.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Final

from anthropic import AsyncAnthropic

from appkit_assistant.backend.models import (
    AIModel,
    Chunk,
    MCPServer,
    Message,
)
from appkit_assistant.backend.processor import Processor

logger = logging.getLogger(__name__)

CLAUDE_HAIKU_4_5: Final = AIModel(
    id="claude-haiku-4.5",
    text="Claude 4.5 Haiku",
    icon="anthropic",
    model="claude-haiku-4-5",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    temperature=1.0,
)

CLAUDE_SONNET_4_5: Final = AIModel(
    id="claude-sonnet-4.5",
    text="Claude 4.5 Sonnet",
    icon="anthropic",
    model="claude-sonnet-4-5",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    temperature=1.0,
)


class BaseClaudeProcessor(Processor, ABC):
    """Base class for Claude processors with common initialization and utilities."""

    # Extended thinking budget (fixed at 10k tokens)
    THINKING_BUDGET_TOKENS: Final[int] = 10000

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

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize the base Claude processor.

        Args:
            models: Dictionary of supported AI models
            api_key: API key for Anthropic Claude API (or Azure API key)
            base_url: Base URL for Azure-hosted Claude (optional)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.models = models
        self.client: AsyncAnthropic | None = None

        if self.api_key:
            if self.base_url:
                # Azure-hosted Claude
                self.client = AsyncAnthropic(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            else:
                # Direct Anthropic API
                self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            logger.warning("No Claude API key found. Processor will not work.")

    @abstractmethod
    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages and generate AI response chunks."""

    def get_supported_models(self) -> dict[str, AIModel]:
        """Return supported models if API key is available."""
        return self.models if self.api_key else {}

    def _get_file_extension(self, file_path: str) -> str:
        """Extract file extension from path."""
        return file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image based on extension."""
        ext = self._get_file_extension(file_path)
        return ext in self.IMAGE_EXTENSIONS

    def _get_media_type(self, file_path: str) -> str:
        """Get MIME type for a file based on extension."""
        ext = self._get_file_extension(file_path)
        media_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "docx": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml"
                ".document"
            ),
            "pptx": (
                "application/vnd.openxmlformats-officedocument.presentationml"
                ".presentation"
            ),
            "md": "text/markdown",
            "txt": "text/plain",
        }
        return media_types.get(ext, "application/octet-stream")

    def _validate_file(self, file_path: str) -> tuple[bool, str]:
        """Validate file for upload.

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
        ext = self._get_file_extension(file_path)
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type: {ext}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            return False, f"File too large: {size_mb:.1f}MB (max 5MB)"

        return True, ""

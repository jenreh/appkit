"""Utility functions for image tool operations."""

import base64
import logging
from pathlib import Path
from urllib.parse import urlparse

import anyio
import httpx

from appkit_mcp_image.backend.models import TMP_PATH

logger = logging.getLogger(__name__)


async def url_to_bytes(url_or_path: str) -> bytes:
    """Load image from URL, file path, or data URL as bytes.

    Args:
        url_or_path: URL, file path, or base64 data URL

    Returns:
        Image data as bytes

    Raises:
        httpx.HTTPError: If download fails
        OSError: If file reading fails
    """
    # Handle data URLs
    if url_or_path.startswith("data:image"):
        base64_part = url_or_path.split(",", 1)[1]
        return base64.b64decode(base64_part)

    # Handle HTTP URLs
    if url_or_path.startswith(("http://", "https://")):
        parsed_url = urlparse(url_or_path)

        # Try local upload directory first
        if parsed_url.path.startswith("/_upload/"):
            local_path = Path(TMP_PATH) / Path(parsed_url.path).name
            if local_path.exists():
                logger.debug("Reading image from local path: %s", local_path)
                async with await anyio.open_file(local_path, "rb") as f:
                    return await f.read()

        # Fall back to remote download
        logger.debug("Downloading image from URL: %s", url_or_path)
        async with httpx.AsyncClient() as client:
            response = await client.get(url_or_path)
            response.raise_for_status()
            return response.content

    # Handle local file paths
    async with await anyio.open_file(url_or_path, "rb") as f:
        return await f.read()


async def url_to_base64(url_or_path: str) -> str:
    """Convert URL, file path, or data URL to base64 string.

    Args:
        url_or_path: URL, file path, or base64 data URL

    Returns:
        Base64 encoded string

    Raises:
        httpx.HTTPError: If download fails
        OSError: If file reading fails
    """
    content = await url_to_bytes(url_or_path)
    return base64.b64encode(content).decode()

"""Image loading strategies using Strategy and Factory patterns."""

import base64
import logging
from abc import ABC, abstractmethod

import anyio
import httpx

logger = logging.getLogger(__name__)


# Strategy Pattern: Image Loading
class ImageLoader(ABC):
    """Strategy for loading images from different sources."""

    @abstractmethod
    async def load(self, source: str) -> bytes:
        """Load image bytes from source."""


class URLImageLoader(ImageLoader):
    """Loads images from HTTP(S) URLs."""

    async def load(self, url: str) -> bytes:
        """Download image from URL."""
        logger.info("Downloading image from URL: %s", url)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                logger.info(
                    "Successfully downloaded image: %d bytes", len(response.content)
                )
                return response.content
        except Exception:
            logger.exception("Failed to download image from URL: %s", url)
            raise


class FileImageLoader(ImageLoader):
    """Loads images from local file paths."""

    async def load(self, path: str) -> bytes:
        """Read image from local file."""
        logger.info("Reading image from local file: %s", path)
        try:
            async with await anyio.open_file(path, "rb") as f:
                image_bytes = await f.read()
                logger.info("Successfully read image: %d bytes", len(image_bytes))
                return image_bytes
        except Exception:
            logger.exception("Failed to read image from file: %s", path)
            raise


class Base64ImageLoader(ImageLoader):
    """Loads images from base64 data URLs."""

    async def load(self, data_url: str) -> bytes:
        """Decode image from base64 data URL."""
        logger.debug("Decoding base64 data URL")
        try:
            base64_data = data_url.split(",", 1)[1]
            image_bytes = base64.b64decode(base64_data)
            logger.info("Successfully decoded base64 image: %d bytes", len(image_bytes))
            return image_bytes
        except Exception:
            logger.exception("Failed to decode base64 data URL")
            raise


class ImageLoaderFactory:
    """Factory pattern for creating appropriate image loader."""

    _loaders = {
        "data:image": Base64ImageLoader(),
        "http://": URLImageLoader(),
        "https://": URLImageLoader(),
    }

    @classmethod
    def create(cls, source: str) -> ImageLoader:
        """Get appropriate loader for image source."""
        for prefix, loader in cls._loaders.items():
            if source.startswith(prefix):
                return loader
        return FileImageLoader()

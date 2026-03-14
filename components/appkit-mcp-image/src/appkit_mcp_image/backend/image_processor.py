"""Image processing utilities for loading and decoding images."""

import base64
import logging

from appkit_mcp_image.backend.image_loaders import ImageLoaderFactory

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image loading and decoding for the MCP edit tool."""

    def __init__(self) -> None:
        self.loader_factory = ImageLoaderFactory()

    async def load_image(self, path: str) -> bytes:
        """Load image using appropriate strategy."""
        loader = self.loader_factory.create(path)
        return await loader.load(path)

    async def prepare_images_for_editing(
        self, image_paths: list[str], output_format: str
    ) -> list[tuple[bytes, str]]:
        """Load multiple images and return (bytes, mime_type) tuples."""
        logger.info("Loading %d image(s) for editing", len(image_paths))
        image_files: list[tuple[bytes, str]] = []

        for idx, img_path in enumerate(image_paths, 1):
            try:
                logger.debug("Loading image %d: %s", idx, img_path)
                image_bytes = await self.load_image(img_path)
                mimetype = f"image/{output_format}"
                image_files.append((image_bytes, mimetype))
                logger.info("Loaded image %d: %d bytes", idx, len(image_bytes))
            except Exception:
                logger.exception("Failed to load image %d", idx)
                raise

        return image_files

    def decode_base64_image(self, b64_data: str, image_idx: int) -> bytes:
        """Decode base64 image data from API response."""
        try:
            image_bytes = base64.b64decode(b64_data)
            logger.debug(
                "Decoded base64 image %d: %d bytes", image_idx, len(image_bytes)
            )
            return image_bytes
        except Exception:
            logger.exception("Failed to decode image %d", image_idx)
            raise

"""Image processing service for handling image operations and storage."""

import base64
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from appkit_mcp_image.backend.image_loaders import ImageLoaderFactory

if TYPE_CHECKING:
    from appkit_mcp_image.backend.models import ImageGenerator

logger = logging.getLogger(__name__)

# API Configuration
TMP_IMG_FILE: Final[str] = "mcp-image"


class ImageProcessor:
    """Handles image processing and storage operations."""

    def __init__(self, generator: "ImageGenerator"):
        self.generator = generator
        self.loader_factory = ImageLoaderFactory()

    async def load_image(self, path: str) -> bytes:
        """Load image using appropriate strategy."""
        loader = self.loader_factory.create(path)
        return await loader.load(path)

    async def prepare_images_for_editing(
        self, image_paths: list[str], output_format: str
    ) -> list[tuple[str, bytes, str]]:
        """Load multiple images and prepare tuples for API call."""
        logger.info("Loading %d image(s) for editing", len(image_paths))
        image_files = []

        for idx, img_path in enumerate(image_paths, 1):
            try:
                logger.debug("Loading image %d: %s", idx, img_path)
                image_bytes = await self.load_image(img_path)
                filename = (
                    Path(img_path).name if img_path.startswith("/") else "image.png"
                )
                mimetype = f"image/{output_format}"
                image_files.append((filename, image_bytes, mimetype))
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

    async def save_and_return_images(
        self, api_images: list, output_format: str
    ) -> list[str]:
        """Process API response images and save to storage."""
        images = []

        for idx, img in enumerate(api_images, 1):
            if not img.b64_json:
                logger.warning("Image %d has no base64 data, skipping", idx)
                continue

            try:
                image_bytes = self.decode_base64_image(img.b64_json, idx)
                image_url = await self.generator.save_image(
                    image_bytes=image_bytes,
                    tmp_file_prefix=TMP_IMG_FILE,
                    output_format=output_format,
                )
                logger.info("Image %d saved: %s", idx, image_url)
                images.append(image_url)
            except Exception:
                logger.exception("Failed to process image %d", idx)
                raise

        return images

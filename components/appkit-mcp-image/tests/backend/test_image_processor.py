"""Tests for image processor."""

import base64
from unittest.mock import AsyncMock, patch

import pytest

from appkit_mcp_image.backend.image_processor import ImageProcessor


class TestImageProcessor:
    """Test ImageProcessor class."""

    @pytest.fixture
    def image_processor(self) -> ImageProcessor:
        """Create an ImageProcessor instance."""
        return ImageProcessor()

    @pytest.mark.asyncio
    async def test_load_image(self, image_processor: ImageProcessor) -> None:
        """Test loading an image."""
        with patch.object(image_processor.loader_factory, "create") as mock_create:
            mock_loader = AsyncMock()
            mock_loader.load.return_value = b"image_data"
            mock_create.return_value = mock_loader

            result = await image_processor.load_image("/path/to/image.png")

            assert result == b"image_data"
            mock_loader.load.assert_called_once_with("/path/to/image.png")

    @pytest.mark.asyncio
    async def test_load_image_from_url(self, image_processor: ImageProcessor) -> None:
        """Test loading an image from URL."""
        with patch.object(image_processor.loader_factory, "create") as mock_create:
            mock_loader = AsyncMock()
            mock_loader.load.return_value = b"remote_image_data"
            mock_create.return_value = mock_loader

            result = await image_processor.load_image("https://example.com/image.png")

            assert result == b"remote_image_data"

    @pytest.mark.asyncio
    async def test_prepare_images_for_editing_single_image(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test preparing single image for editing."""
        with patch.object(image_processor, "load_image") as mock_load:
            mock_load.return_value = b"image_data_123"

            result = await image_processor.prepare_images_for_editing(
                image_paths=["/path/to/image.png"],
                output_format="png",
            )

            assert len(result) == 1
            image_bytes, mimetype = result[0]
            assert image_bytes == b"image_data_123"
            assert mimetype == "image/png"

    @pytest.mark.asyncio
    async def test_prepare_images_for_editing_multiple_images(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test preparing multiple images for editing."""
        with patch.object(image_processor, "load_image") as mock_load:
            mock_load.side_effect = [b"image1", b"image2", b"image3"]

            result = await image_processor.prepare_images_for_editing(
                image_paths=[
                    "/path/to/img1.png",
                    "https://example.com/img2.png",
                    "/path/to/img3.jpg",
                ],
                output_format="jpeg",
            )

            assert len(result) == 3
            assert result[0][0] == b"image1"
            assert result[1][0] == b"image2"
            assert result[2][0] == b"image3"

    @pytest.mark.asyncio
    async def test_prepare_images_for_editing_load_error(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test error when loading image fails."""
        with patch.object(image_processor, "load_image") as mock_load:
            mock_load.side_effect = FileNotFoundError("Image not found")

            with pytest.raises(FileNotFoundError):
                await image_processor.prepare_images_for_editing(
                    image_paths=["/missing/image.png"],
                    output_format="png",
                )

    @pytest.mark.asyncio
    async def test_prepare_images_for_editing_output_format_variations(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test preparing images with different output formats."""
        with patch.object(image_processor, "load_image") as mock_load:
            mock_load.return_value = b"image_data"

            for output_format in ["png", "jpeg", "webp"]:
                result = await image_processor.prepare_images_for_editing(
                    image_paths=["/path/to/image.png"],
                    output_format=output_format,
                )

                _, mimetype = result[0]
                assert mimetype == f"image/{output_format}"

    def test_decode_base64_image(self, image_processor: ImageProcessor) -> None:
        """Test decoding base64 image data."""
        original_data = b"Hello World Image Data"
        b64_data = base64.b64encode(original_data).decode()

        result = image_processor.decode_base64_image(b64_data, 1)

        assert result == original_data

    def test_decode_base64_image_invalid_data(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test error when decoding invalid base64 data."""
        with pytest.raises(ValueError):  # noqa: BLE001
            image_processor.decode_base64_image("not_valid_base64!!!!", 1)

"""Tests for image processor."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from server.backend.image_processor import ImageProcessor


class TestImageProcessor:
    """Test ImageProcessor class."""

    @pytest.fixture
    def mock_generator(self) -> MagicMock:
        """Create a mock generator."""
        return MagicMock()

    @pytest.fixture
    def image_processor(self, mock_generator: MagicMock) -> ImageProcessor:
        """Create an ImageProcessor instance with mock generator."""
        return ImageProcessor(mock_generator)

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
            filename, image_bytes, mimetype = result[0]
            assert image_bytes == b"image_data_123"
            assert mimetype == "image/png"
            assert "image" in filename.lower()

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
            assert result[0][1] == b"image1"
            assert result[1][1] == b"image2"
            assert result[2][1] == b"image3"

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

                _, _, mimetype = result[0]
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

    def test_decode_base64_image_empty_data(
        self, image_processor: ImageProcessor
    ) -> None:
        """Test decoding empty base64 data."""
        b64_data = base64.b64encode(b"").decode()
        result = image_processor.decode_base64_image(b64_data, 1)

        assert result == b""

    @pytest.mark.asyncio
    async def test_save_and_return_images_single_image(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test saving and returning a single image."""
        mock_img = MagicMock()
        mock_img.b64_json = base64.b64encode(b"image_data").decode()

        mock_generator._save_image_to_tmp_and_get_url = AsyncMock(  # noqa: SLF001
            return_value="http://localhost:8000/image1.png"
        )

        result = await image_processor.save_and_return_images(
            api_images=[mock_img],
            output_format="png",
        )

        assert len(result) == 1
        assert result[0] == "http://localhost:8000/image1.png"

    @pytest.mark.asyncio
    async def test_save_and_return_images_multiple_images(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test saving and returning multiple images."""
        mock_img1 = MagicMock()
        mock_img1.b64_json = base64.b64encode(b"image1_data").decode()

        mock_img2 = MagicMock()
        mock_img2.b64_json = base64.b64encode(b"image2_data").decode()

        mock_generator._save_image_to_tmp_and_get_url = AsyncMock(  # noqa: SLF001
            side_effect=[
                "http://localhost:8000/image1.png",
                "http://localhost:8000/image2.png",
            ]
        )

        result = await image_processor.save_and_return_images(
            api_images=[mock_img1, mock_img2],
            output_format="jpeg",
        )

        assert len(result) == 2
        assert result[0] == "http://localhost:8000/image1.png"
        assert result[1] == "http://localhost:8000/image2.png"

    @pytest.mark.asyncio
    async def test_save_and_return_images_skip_empty_b64_json(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test skipping images with no base64 data."""
        mock_img_valid = MagicMock()
        mock_img_valid.b64_json = base64.b64encode(b"image_data").decode()

        mock_img_empty = MagicMock()
        mock_img_empty.b64_json = None

        mock_generator._save_image_to_tmp_and_get_url = AsyncMock(  # noqa: SLF001
            return_value="http://localhost:8000/image1.png"
        )

        result = await image_processor.save_and_return_images(
            api_images=[mock_img_empty, mock_img_valid],
            output_format="png",
        )

        # Should only return 1 image (the valid one)
        assert len(result) == 1
        assert result[0] == "http://localhost:8000/image1.png"

    @pytest.mark.asyncio
    async def test_save_and_return_images_save_error(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test error when saving image fails."""
        mock_img = MagicMock()
        mock_img.b64_json = base64.b64encode(b"image_data").decode()

        mock_generator._save_image_to_tmp_and_get_url = AsyncMock(  # noqa: SLF001
            side_effect=RuntimeError("Storage unavailable")
        )

        with pytest.raises(RuntimeError):
            await image_processor.save_and_return_images(
                api_images=[mock_img],
                output_format="png",
            )

    @pytest.mark.asyncio
    async def test_save_and_return_images_decode_error(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test error when decoding base64 fails."""
        mock_img = MagicMock()
        mock_img.b64_json = "invalid_base64_data!!!!"

        with pytest.raises(ValueError):
            await image_processor.save_and_return_images(
                api_images=[mock_img],
                output_format="png",
            )

    @pytest.mark.asyncio
    async def test_save_and_return_images_various_formats(
        self, image_processor: ImageProcessor, mock_generator: MagicMock
    ) -> None:
        """Test saving images with different output formats."""
        for output_format in ["png", "jpeg", "webp"]:
            mock_img = MagicMock()
            mock_img.b64_json = base64.b64encode(b"image_data").decode()

            mock_generator._save_image_to_tmp_and_get_url = AsyncMock(  # noqa: SLF001
                return_value=f"http://localhost:8000/image.{output_format}"
            )

            result = await image_processor.save_and_return_images(
                api_images=[mock_img],
                output_format=output_format,
            )

            assert len(result) == 1
            # Verify the correct format was passed
            call_kwargs = (
                mock_generator._save_image_to_tmp_and_get_url.call_args.kwargs  # noqa: SLF001
            )
            assert call_kwargs["output_format"] == output_format

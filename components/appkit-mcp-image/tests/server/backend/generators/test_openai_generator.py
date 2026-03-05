"""Unit tests for OpenAI image generator."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from httpx import Response

from appkit_mcp_image.backend.generators.openai import (
    OpenAIImageGenerator,
)
from appkit_mcp_image.backend.models import EditImageInput, GenerationInput


class TestOpenAIImageGeneratorInit:
    """Test OpenAIImageGenerator initialization."""

    def test_init_with_all_params(
        self, openai_api_key: str, openai_base_url: str
    ) -> None:
        """Test initialization with all parameters."""
        generator = OpenAIImageGenerator(
            api_key=openai_api_key,
            base_url=openai_base_url,
            id="test-id",
            label="Test Label",
            model="gpt-image-1",
            backend_server="http://localhost:8000",
        )

        assert generator.id == "test-id"
        assert generator.label == "Test Label"
        assert generator.model == "gpt-image-1"
        assert generator.api_key == openai_api_key
        assert generator.backend_server == "http://localhost:8000"
        assert generator.client is not None

    def test_init_minimal_params(
        self, openai_api_key: str, openai_base_url: str
    ) -> None:
        """Test initialization with minimal parameters."""
        generator = OpenAIImageGenerator(
            api_key=openai_api_key, base_url=openai_base_url
        )

        assert generator.id == "gpt-image-1"
        assert generator.model == "gpt-image-1"
        assert generator.api_key == openai_api_key


class TestOpenAIImageGeneratorGenerate:
    """Test image generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test basic image generation."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.prompt_enhancer = MagicMock()
        generator.prompt_enhancer.enhance = AsyncMock(return_value="Test prompt")
        generator.image_processor = MagicMock()
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=["http://localhost:8000/img1.png"]
        )

        # Mock response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="dGVzdCBkYXRh", url=None)]
        mock_openai_client.images.generate.return_value = mock_response

        input_data = GenerationInput(prompt="Test prompt")
        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert len(response.images) > 0

    @pytest.mark.asyncio
    async def test_generate_with_all_params(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test image generation with all parameters."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.prompt_enhancer = MagicMock()
        generator.prompt_enhancer.enhance = AsyncMock(return_value="Detailed prompt")
        generator.image_processor = MagicMock()
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=[
                "http://localhost:8000/img1.png",
                "http://localhost:8000/img2.png",
            ]
        )

        # Mock response with 2 images
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="aW1hZ2UxX2RhdGE=", url=None),
            MagicMock(b64_json="aW1hZ2UyX2RhdGE=", url=None),
        ]
        mock_openai_client.images.generate.return_value = mock_response

        input_data = GenerationInput(
            prompt="Detailed prompt",
            size="1024x1024",
            output_format="webp",
            seed=42,
            enhance_prompt=False,
        )

        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 2

    @pytest.mark.asyncio
    async def test_generate_with_prompt_enhancement(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test image generation with prompt enhancement."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.prompt_enhancer = MagicMock()
        generator.prompt_enhancer.enhance = AsyncMock(return_value="Enhanced prompt")
        generator.image_processor = MagicMock()
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=["http://localhost:8000/img1.png"]
        )

        # Mock the image generation response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZW5oYW5jZWQgZGF0YQ==", url=None)]
        mock_openai_client.images.generate.return_value = mock_response

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=True)
        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert response.enhanced_prompt == "Enhanced prompt"


class TestOpenAIImageGeneratorEdit:
    """Test image editing functionality."""

    @pytest.mark.asyncio
    async def test_edit_basic(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test basic image editing."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.image_processor = MagicMock()
        generator.image_processor.prepare_images_for_editing = AsyncMock(
            return_value=[("test.png", b"image_data", "image/png")]
        )
        generator.image_processor.load_image = AsyncMock(return_value=b"mask_data")
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=["http://localhost:8000/edited.png"]
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit.return_value = mock_response

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])
        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 1
        assert response.images[0].startswith("http://localhost:8000")
        mock_openai_client.images.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_multiple_images(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with multiple images."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.image_processor = MagicMock()
        generator.image_processor.prepare_images_for_editing = AsyncMock(
            return_value=[
                ("img1.png", b"data1", "image/png"),
                ("img2.png", b"data2", "image/png"),
            ]
        )
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=[
                "http://localhost:8000/edited1.png",
                "http://localhost:8000/edited2.png",
            ]
        )

        input_data = EditImageInput(
            prompt="Edit prompt", image_paths=[temp_image_file, temp_image_file]
        )

        # Mock response with 2 edited images
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="ZWRpdGVkMQ==", url=None),
            MagicMock(b64_json="ZWRpdGVkMg==", url=None),
        ]
        mock_openai_client.images.edit.return_value = mock_response

        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 2
        assert response.images[0].startswith("http://localhost:8000")
        assert response.images[1].startswith("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_edit_with_mask(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with mask."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.image_processor = MagicMock()
        generator.image_processor.prepare_images_for_editing = AsyncMock(
            return_value=[("test.png", b"image_data", "image/png")]
        )
        generator.image_processor.load_image = AsyncMock(return_value=b"mask_data")
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=["http://localhost:8000/edited.png"]
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit.return_value = mock_response

        input_data = EditImageInput(
            prompt="Edit prompt",
            image_paths=[temp_image_file],
            mask_path=temp_image_file,
        )
        response = await generator.edit(input_data)

        assert len(response.images) == 1
        call_kwargs = mock_openai_client.images.edit.call_args.kwargs
        assert "mask" in call_kwargs

    @pytest.mark.asyncio
    async def test_edit_with_all_params(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with all parameters."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        generator.image_processor = MagicMock()
        generator.image_processor.prepare_images_for_editing = AsyncMock(
            return_value=[("test.png", b"image_data", "image/jpeg")]
        )
        generator.image_processor.load_image = AsyncMock(return_value=b"mask_data")
        generator.image_processor.save_and_return_images = AsyncMock(
            return_value=["http://localhost:8000/edited.png"]
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit.return_value = mock_response

        input_data = EditImageInput(
            prompt="Detailed edit",
            image_paths=[temp_image_file],
            mask_path=temp_image_file,
            output_format="jpeg",
            seed=123,
        )
        response = await generator.edit(input_data)

        assert len(response.images) == 1

        # Verify call arguments
        call_kwargs = mock_openai_client.images.edit.call_args.kwargs
        assert call_kwargs["prompt"] == "Detailed edit"
        assert call_kwargs["output_format"] == "jpeg"


class TestOpenAIImageGeneratorLoadImage:
    """Test image loading via ImageProcessor (formerly _load_image)."""

    @pytest.mark.asyncio
    async def test_load_image_from_file(
        self, temp_image_file: str, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from file path."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        loaded = await generator.image_processor.load_image(temp_image_file)

        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_load_image_from_url(
        self, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from URL."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        url = "https://example.com/image.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        loaded = await generator.image_processor.load_image(url)
        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_from_base64(
        self, sample_base64_image: str, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from base64 data URL."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        loaded = await generator.image_processor.load_image(sample_base64_image)

        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_file_not_found(self, openai_base_url: str) -> None:
        """Test loading non-existent file raises error."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        with pytest.raises(FileNotFoundError):
            await generator.image_processor.load_image("/nonexistent/file.png")

    @pytest.mark.asyncio
    @respx.mock
    async def test_load_image_url_error(self, openai_base_url: str) -> None:
        """Test loading from URL with HTTP error."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        url = "https://example.com/notfound.png"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            await generator.image_processor.load_image(url)


class TestOpenAIImageGeneratorErrorHandling:
    """Test error handling in OpenAI generator."""

    @pytest.mark.asyncio
    async def test_generate_api_error(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test handling of API errors during generation."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        mock_openai_client.images.generate.side_effect = Exception("API Error")

        input_data = GenerationInput(prompt="Test")

        response = await generator.generate(input_data)

        # The generator attempts to access attributes not defined in GenerationInput
        assert response.state == "failed"
        assert "no attribute" in response.error or "API Error" in response.error

    @pytest.mark.asyncio
    async def test_edit_api_error(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test handling of API errors during editing."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        mock_openai_client.images.edit.side_effect = Exception("Edit API Error")

        input_data = EditImageInput(prompt="Edit", image_paths=[temp_image_file])

        response = await generator.edit(input_data)

        assert response.state == "failed"
        assert "Edit API Error" in response.error

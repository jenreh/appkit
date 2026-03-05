"""Unit tests for OpenAI image generator."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

from appkit_mcp_image.backend.generators.openai import (
    OpenAIImageGenerator,
    OpenAIPromptEnhancer,
)
from appkit_mcp_image.backend.models import EditImageInput, GenerationInput

_OPENAI_CLIENT = "appkit_mcp_image.backend.generators.openai.AsyncAzureOpenAI"


class TestOpenAIImageGeneratorInit:
    """Test OpenAIImageGenerator initialization."""

    @patch(_OPENAI_CLIENT)
    def test_init_with_all_params(
        self,
        mock_client_cls: MagicMock,
        openai_api_key: str,
        openai_base_url: str,
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

    @patch(_OPENAI_CLIENT)
    def test_init_minimal_params(
        self,
        mock_client_cls: MagicMock,
        openai_api_key: str,
        openai_base_url: str,
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
    @patch(_OPENAI_CLIENT)
    async def test_generate_basic(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        openai_base_url: str,
    ) -> None:
        """Test basic image generation."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        # Mock response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="dGVzdCBkYXRh", url=None)]
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)

        # Mock save_image and clean_tmp_path (uses service_registry)
        generator.save_image = AsyncMock(
            return_value="http://localhost:8000/_upload/images/test.png"
        )
        generator.clean_tmp_path = MagicMock()

        input_data = GenerationInput(prompt="Test prompt", enhance_prompt=False)
        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert len(response.images) > 0

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_generate_with_all_params(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        openai_base_url: str,
    ) -> None:
        """Test image generation with all parameters."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        # Mock response with 2 images
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="aW1hZ2UxX2RhdGE=", url=None),
            MagicMock(b64_json="aW1hZ2UyX2RhdGE=", url=None),
        ]
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)

        # Mock save_image and clean_tmp_path (uses service_registry)
        generator.save_image = AsyncMock(
            side_effect=[
                "http://localhost:8000/_upload/images/img1.webp",
                "http://localhost:8000/_upload/images/img2.webp",
            ]
        )
        generator.clean_tmp_path = MagicMock()

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
    @patch(_OPENAI_CLIENT)
    async def test_generate_with_prompt_enhancement(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        openai_base_url: str,
    ) -> None:
        """Test image generation with prompt enhancement."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.prompt_enhancer = OpenAIPromptEnhancer(
            mock_openai_client, "gpt-5-mini"
        )

        # Mock the completion for prompt enhancement
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Enhanced prompt"))
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        # Mock the image generation response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZW5oYW5jZWQgZGF0YQ==", url=None)]
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)

        # Mock save_image and clean_tmp_path (uses service_registry)
        generator.save_image = AsyncMock(
            return_value="http://localhost:8000/_upload/images/test.png"
        )
        generator.clean_tmp_path = MagicMock()

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=True)
        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert response.enhanced_prompt == "Enhanced prompt"


class TestOpenAIImageGeneratorEdit:
    """Test image editing functionality."""

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_edit_basic(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        temp_image_file: str,
        openai_base_url: str,
    ) -> None:
        """Test basic image editing."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)

        generator.save_image = AsyncMock(
            return_value="http://localhost:8000/_upload/images/edited.png"
        )
        generator.clean_tmp_path = MagicMock()

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])
        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 1

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_edit_multiple_images(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        temp_image_file: str,
        openai_base_url: str,
    ) -> None:
        """Test editing with multiple images."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="ZWRpdGVkMQ==", url=None),
            MagicMock(b64_json="ZWRpdGVkMg==", url=None),
        ]
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)

        generator.save_image = AsyncMock(
            side_effect=[
                "http://localhost:8000/_upload/images/edited1.png",
                "http://localhost:8000/_upload/images/edited2.png",
            ]
        )
        generator.clean_tmp_path = MagicMock()

        input_data = EditImageInput(
            prompt="Edit prompt", image_paths=[temp_image_file, temp_image_file]
        )

        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 2

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_edit_with_mask(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        temp_image_file: str,
        openai_base_url: str,
    ) -> None:
        """Test editing with mask."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)

        generator.save_image = AsyncMock(
            return_value="http://localhost:8000/_upload/images/edited.png"
        )
        generator.clean_tmp_path = MagicMock()

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
    @patch(_OPENAI_CLIENT)
    async def test_edit_with_all_params(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        temp_image_file: str,
        openai_base_url: str,
    ) -> None:
        """Test editing with all parameters."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="ZWRpdGVk", url=None)]
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)

        generator.save_image = AsyncMock(
            return_value="http://localhost:8000/_upload/images/edited.jpeg"
        )
        generator.clean_tmp_path = MagicMock()

        input_data = EditImageInput(
            prompt="Detailed edit",
            image_paths=[temp_image_file],
            mask_path=temp_image_file,
            output_format="jpeg",
        )
        response = await generator.edit(input_data)

        assert len(response.images) == 1

        call_kwargs = mock_openai_client.images.edit.call_args.kwargs
        assert call_kwargs["prompt"] == "Detailed edit"
        assert call_kwargs["output_format"] == "jpeg"


class TestOpenAIImageGeneratorLoadImage:
    """Test image loading via image_processor."""

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_load_image_from_file(
        self,
        mock_client_cls: MagicMock,
        temp_image_file: str,
        sample_image_bytes: bytes,
        openai_base_url: str,
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
    @patch(_OPENAI_CLIENT)
    async def test_load_image_from_url(
        self,
        mock_client_cls: MagicMock,
        sample_image_bytes: bytes,
        openai_base_url: str,
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
    @patch(_OPENAI_CLIENT)
    async def test_load_image_from_base64(
        self,
        mock_client_cls: MagicMock,
        sample_base64_image: str,
        sample_image_bytes: bytes,
        openai_base_url: str,
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
    @patch(_OPENAI_CLIENT)
    async def test_load_image_file_not_found(
        self, mock_client_cls: MagicMock, openai_base_url: str
    ) -> None:
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
    @patch(_OPENAI_CLIENT)
    async def test_load_image_url_error(
        self, mock_client_cls: MagicMock, openai_base_url: str
    ) -> None:
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
    @patch(_OPENAI_CLIENT)
    async def test_generate_api_error(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        openai_base_url: str,
    ) -> None:
        """Test handling of API errors during generation."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_openai_client.images.generate = AsyncMock(
            side_effect=Exception("API Error")
        )

        input_data = GenerationInput(prompt="Test", enhance_prompt=False)

        response = await generator.generate(input_data)

        assert response.state == "failed"
        assert "API Error" in response.error

    @pytest.mark.asyncio
    @patch(_OPENAI_CLIENT)
    async def test_edit_api_error(
        self,
        mock_client_cls: MagicMock,
        mock_openai_client: MagicMock,
        temp_image_file: str,
        openai_base_url: str,
    ) -> None:
        """Test handling of API errors during editing."""
        mock_client_cls.return_value = mock_openai_client
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        mock_openai_client.images.edit = AsyncMock(
            side_effect=Exception("Edit API Error")
        )

        input_data = EditImageInput(prompt="Edit", image_paths=[temp_image_file])

        response = await generator.edit(input_data)

        assert response.state == "failed"
        assert "Edit API Error" in response.error

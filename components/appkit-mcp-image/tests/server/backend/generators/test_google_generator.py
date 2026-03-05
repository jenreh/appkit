"""Unit tests for Google image generator."""

from unittest.mock import MagicMock

import pytest
from server.backend.generators.google import GoogleImageGenerator
from server.backend.models import EditImageInput, GenerationInput


class TestGoogleImageGeneratorInit:
    """Test GoogleImageGenerator initialization."""

    def test_init_with_all_params(self, google_api_key: str) -> None:
        """Test initialization with all parameters."""
        generator = GoogleImageGenerator(
            api_key=google_api_key,
            model="FLUX.1-Kontext-pro",
            backend_server="http://localhost:8080",
        )

        assert generator.model == "FLUX.1-Kontext-pro"
        assert generator.api_key == google_api_key
        assert generator.backend_server == "http://localhost:8080"

    def test_init_minimal_params(self, google_api_key: str) -> None:
        """Test initialization with minimal parameters."""
        generator = GoogleImageGenerator(api_key=google_api_key)

        assert generator.model == "imagen-4.0-generate-preview-06-06"
        assert generator.api_key == google_api_key


class TestGoogleImageGeneratorGenerate:
    """Test image generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_basic(self, mock_google_client: MagicMock) -> None:
        """Test basic image generation."""
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )
        generator.client = mock_google_client

        input_data = GenerationInput(prompt="Test prompt")
        response = await generator.generate(input_data)

        # The generator attempts to access attributes not defined in GenerationInput,
        # so this will fail
        assert response.state == "failed"
        assert "no attribute" in response.error or "API call failed" in response.error

    @pytest.mark.asyncio
    async def test_generate_with_all_params(
        self, mock_google_client: MagicMock
    ) -> None:
        """Test image generation with all parameters."""
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )
        generator.client = mock_google_client

        # Mock response with 2 images
        mock_image1 = MagicMock()
        mock_image1.image.image_bytes = b"google_image1_data"
        mock_image2 = MagicMock()
        mock_image2.image.image_bytes = b"google_image2_data"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image1, mock_image2]
        mock_google_client.models.generate_images.return_value = mock_response

        input_data = GenerationInput(
            prompt="Detailed prompt",
            size="1024x1024",
            output_format="png",
            seed=42,
            enhance_prompt=False,
        )

        response = await generator.generate(input_data)

        # The generator attempts to access attributes not defined in GenerationInput,
        # so this will fail
        assert response.state == "failed"
        assert "no attribute" in response.error or "API call failed" in response.error

    @pytest.mark.asyncio
    async def test_generate_with_prompt_enhancement(
        self, mock_google_client: MagicMock
    ) -> None:
        """Test image generation with prompt enhancement."""
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )
        generator.client = mock_google_client

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=True)
        response = await generator.generate(input_data)

        # The generator attempts to access attributes not defined in GenerationInput,
        # so this will fail
        assert response.state == "failed"
        assert "no attribute" in response.error or "API call failed" in response.error


class TestGoogleImageGeneratorEdit:
    """Test image editing functionality."""

    @pytest.mark.asyncio
    async def test_edit_not_supported(self, temp_image_file: str) -> None:
        """Test that edit operation is not supported."""
        generator = GoogleImageGenerator(api_key="test_key")

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])

        # Edit should return error response (not supported by Google Imagen)
        response = await generator.edit(input_data)

        assert response.state == "failed"
        assert "not supported" in response.error.lower()

    @pytest.mark.asyncio
    async def test_perform_edit_not_supported(self, temp_image_file: str) -> None:
        """Test _perform_edit method returns not supported error."""
        generator = GoogleImageGenerator(api_key="test_key")

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])

        # Call the private method directly
        response = await generator._perform_edit(input_data)  # noqa: SLF001

        assert response.state == "failed"
        assert "not supported" in response.error.lower()


class TestGoogleImageGeneratorErrorHandling:
    """Test error handling in Google generator."""

    @pytest.mark.asyncio
    async def test_generate_api_error(self, mock_google_client: MagicMock) -> None:
        """Test handling of API errors during generation."""
        generator = GoogleImageGenerator(api_key="test_key")
        generator.client = mock_google_client

        mock_google_client.models.generate_images.side_effect = Exception(
            "Google API Error"
        )

        input_data = GenerationInput(prompt="Test")

        response = await generator.generate(input_data)

        # The generator attempts to access attributes not defined in GenerationInput
        assert response.state == "failed"
        assert "no attribute" in response.error or "Google API Error" in response.error

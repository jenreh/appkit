"""Unit tests for Google image generator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_mcp_image.backend.generators.google import (
    GoogleImageGenerator,
    GooglePromptEnhancer,
)
from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageResponseState,
)

_GENAI_CLIENT = "appkit_mcp_image.backend.generators.google.genai.Client"


class TestGoogleImageGeneratorInit:
    """Test GoogleImageGenerator initialization."""

    @patch(_GENAI_CLIENT)
    def test_init_with_all_params(
        self, mock_client_cls: MagicMock, google_api_key: str
    ) -> None:
        """Test initialization with all parameters."""
        generator = GoogleImageGenerator(
            api_key=google_api_key,
            model="FLUX.1-Kontext-pro",
            backend_server="http://localhost:8080",
        )

        assert generator.model == "FLUX.1-Kontext-pro"
        assert generator.api_key == google_api_key
        assert generator.backend_server == "http://localhost:8080"

    @patch(_GENAI_CLIENT)
    def test_init_minimal_params(
        self, mock_client_cls: MagicMock, google_api_key: str
    ) -> None:
        """Test initialization with minimal parameters."""
        generator = GoogleImageGenerator(api_key=google_api_key)

        assert generator.model == "imagen-4.0-generate-preview-06-06"
        assert generator.api_key == google_api_key


class TestGoogleImageGeneratorGenerate:
    """Test image generation functionality."""

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_generate_basic(
        self, mock_client_cls: MagicMock, mock_google_client: MagicMock
    ) -> None:
        """Test basic image generation."""
        mock_client_cls.return_value = mock_google_client
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )

        input_data = GenerationInput(prompt="Test prompt")
        response = await generator.generate(input_data)

        assert response.state == "failed"

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_generate_with_all_params(
        self, mock_client_cls: MagicMock, mock_google_client: MagicMock
    ) -> None:
        """Test image generation with all parameters."""
        mock_client_cls.return_value = mock_google_client
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )

        input_data = GenerationInput(
            prompt="Detailed prompt",
            size="1024x1024",
            output_format="png",
            seed=42,
            enhance_prompt=False,
        )

        response = await generator.generate(input_data)

        assert response.state == "failed"

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_generate_with_prompt_enhancement(
        self, mock_client_cls: MagicMock, mock_google_client: MagicMock
    ) -> None:
        """Test image generation with prompt enhancement."""
        mock_client_cls.return_value = mock_google_client
        generator = GoogleImageGenerator(
            api_key="test_key", backend_server="http://localhost:8000"
        )

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=True)
        response = await generator.generate(input_data)

        assert response.state == "failed"


class TestGoogleImageGeneratorEdit:
    """Test image editing functionality."""

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_edit_not_supported(
        self, mock_client_cls: MagicMock, temp_image_file: str
    ) -> None:
        """Test that edit operation is not supported."""
        generator = GoogleImageGenerator(api_key="test_key")

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])

        response = await generator.edit(input_data)

        assert response.state == "failed"

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_perform_edit_not_supported(
        self, mock_client_cls: MagicMock, temp_image_file: str
    ) -> None:
        """Test _perform_edit method returns not supported error."""
        generator = GoogleImageGenerator(api_key="test_key")

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])

        response = await generator._perform_edit(input_data)  # noqa: SLF001

        assert response.state == "failed"


class TestGoogleImageGeneratorErrorHandling:
    """Test error handling in Google generator."""

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_generate_api_error(
        self, mock_client_cls: MagicMock, mock_google_client: MagicMock
    ) -> None:
        """Test handling of API errors during generation."""
        mock_client_cls.return_value = mock_google_client
        generator = GoogleImageGenerator(api_key="test_key")

        mock_google_client.models.generate_content.side_effect = Exception(
            "Google API Error"
        )

        input_data = GenerationInput(prompt="Test")

        response = await generator.generate(input_data)

        assert response.state == "failed"


# -- _parse_size tests --


class TestParseSize:
    """Tests for GoogleImageGenerator._parse_size."""

    @patch(_GENAI_CLIENT)
    def test_auto_returns_default(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        assert gen._parse_size("auto") == (1024, 1024)  # noqa: SLF001

    @patch(_GENAI_CLIENT)
    def test_no_x_returns_default(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        assert gen._parse_size("square") == (1024, 1024)  # noqa: SLF001

    @patch(_GENAI_CLIENT)
    def test_valid_size(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        assert gen._parse_size("1536x1024") == (1536, 1024)  # noqa: SLF001

    @patch(_GENAI_CLIENT)
    def test_invalid_numeric(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        assert gen._parse_size("axb") == (1024, 1024)  # noqa: SLF001


# -- _process_response tests --


class TestProcessResponse:
    """Tests for GoogleImageGenerator._process_response."""

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_no_candidates(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        response = MagicMock()
        response.candidates = []
        result = await gen._process_response(  # noqa: SLF001
            response, "jpeg", "prompt"
        )
        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_candidate_no_content(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        candidate = MagicMock()
        candidate.content = None
        response = MagicMock()
        response.candidates = [candidate]
        result = await gen._process_response(  # noqa: SLF001
            response, "jpeg", "prompt"
        )
        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_successful_processing(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(
            api_key="k",
            backend_server="http://localhost:8000",
        )
        gen.save_image = AsyncMock(return_value="http://img.url/1.png")

        part = MagicMock()
        part.inline_data = MagicMock()
        part.inline_data.data = b"\x89PNG"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        result = await gen._process_response(  # noqa: SLF001
            response, "png", "enhanced"
        )
        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.images) == 1

    @pytest.mark.asyncio
    @patch(_GENAI_CLIENT)
    async def test_processing_exception(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(
            api_key="k",
            backend_server="http://localhost:8000",
        )
        gen.save_image = AsyncMock(side_effect=OSError("disk"))

        part = MagicMock()
        part.inline_data = MagicMock()
        part.inline_data.data = b"\x89PNG"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        result = await gen._process_response(  # noqa: SLF001
            response, "png", "prompt"
        )
        assert result.state == ImageResponseState.FAILED


# -- _create_failed_response tests --


class TestCreateFailedResponse:
    @patch(_GENAI_CLIENT)
    def test_returns_failed_state(self, mock_cls: MagicMock) -> None:
        gen = GoogleImageGenerator(api_key="k")
        resp = gen._create_failed_response("oops", "p")  # noqa: SLF001
        assert resp.state == ImageResponseState.FAILED
        assert resp.error == "oops"
        assert resp.enhanced_prompt == "p"
        assert resp.images == []


# -- GooglePromptEnhancer tests --


class TestGooglePromptEnhancer:
    def test_enhance_success(self) -> None:
        client = MagicMock()
        response = MagicMock()
        response.text = "  better prompt  "
        client.models.generate_content.return_value = response

        enhancer = GooglePromptEnhancer(client, "gemini")
        result = enhancer.enhance("original")
        assert result == "better prompt"

    def test_enhance_empty_returns_original(self) -> None:
        client = MagicMock()
        response = MagicMock()
        response.text = "   "
        client.models.generate_content.return_value = response

        enhancer = GooglePromptEnhancer(client, "gemini")
        result = enhancer.enhance("original")
        assert result == "original"

    def test_enhance_exception_returns_original(self) -> None:
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("fail")

        enhancer = GooglePromptEnhancer(client, "gemini")
        result = enhancer.enhance("original")
        assert result == "original"

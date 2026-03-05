# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for GoogleImageGenerator.

Covers init, aspect ratio calculation, prompt enhancement,
image generation, and image editing flows.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from appkit_imagecreator.backend.generators.google import (
    GoogleImageGenerator,
)
from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageModel,
    ImageResponseState,
)

_PATCH = "appkit_imagecreator.backend.generators.google"


def _model(model_id: str = "imagen-4") -> ImageModel:
    return ImageModel(id=model_id, model=model_id, label="Imagen 4")


def _gen(
    api_key: str = "google-key",
    models: ImageModel | None = None,
) -> GoogleImageGenerator:
    with patch(f"{_PATCH}.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        return GoogleImageGenerator(
            model=models or _model(),
            api_key=api_key,
        )


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_basic(self) -> None:
        gen = _gen()
        assert gen.model.model == "imagen-4"
        assert gen.client is not None

    def test_no_api_key(self) -> None:
        with patch(f"{_PATCH}.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            gen = GoogleImageGenerator(model=_model(), api_key=None)
        assert gen.client is not None  # Client still created


# ============================================================================
# _aspect_ratio
# ============================================================================


class TestAspectRatio:
    @pytest.mark.parametrize(
        ("width", "height", "expected"),
        [
            (1024, 1024, "1:1"),
            (1920, 1080, "16:9"),
            (1080, 1920, "9:16"),
            (800, 600, "4:3"),
            (600, 800, "3:4"),
        ],
    )
    def test_ratios(self, width: int | None, height: int | None, expected: str) -> None:
        gen = _gen()
        assert gen._aspect_ratio(width, height) == expected

    def test_wide_ratio(self) -> None:
        gen = _gen()
        # 2048 x 512 = ratio 4.0, closest should be "4:1" or similar
        result = gen._aspect_ratio(2048, 512)
        assert ":" in result  # Should return a valid ratio string

    def test_tall_ratio(self) -> None:
        gen = _gen()
        result = gen._aspect_ratio(512, 2048)
        assert ":" in result


# ============================================================================
# _enhance_prompt
# ============================================================================


class TestEnhancePrompt:
    def test_success(self) -> None:
        gen = _gen()
        mock_response = MagicMock()
        mock_response.text = "Enhanced beautiful sunset"
        gen.client.models.generate_content = MagicMock(return_value=mock_response)
        result = gen._enhance_prompt(
            GenerationInput(prompt="sunset", enhance_prompt=True)
        )
        assert result == "Enhanced beautiful sunset"

    def test_no_enhancement(self) -> None:
        gen = _gen()
        result = gen._enhance_prompt(
            GenerationInput(prompt="original", enhance_prompt=False)
        )
        assert result == "original"

    def test_error_fallback(self) -> None:
        gen = _gen()
        gen.client.models.generate_content = MagicMock(side_effect=RuntimeError("fail"))
        inp = GenerationInput(prompt="original", enhance_prompt=True)
        result = gen._enhance_prompt(inp)
        assert result == "original"


# ============================================================================
# _perform_generation
# ============================================================================


class TestPerformGeneration:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        gen = _gen()
        mock_image = MagicMock()
        mock_image.image.image_bytes = b"fake-image-data"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        gen.client.models.generate_images = MagicMock(return_value=mock_response)
        inp = GenerationInput(
            prompt="sunset", enhance_prompt=False, width=1024, height=768
        )
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.generated_images) == 1

    @pytest.mark.asyncio
    async def test_no_images(self) -> None:
        gen = _gen()
        mock_response = MagicMock()
        mock_response.generated_images = None
        gen.client.models.generate_images = MagicMock(return_value=mock_response)
        inp = GenerationInput(prompt="test", enhance_prompt=False)
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    async def test_with_enhancement(self) -> None:
        gen = _gen()
        mock_image = MagicMock()
        mock_image.image.image_bytes = b"data"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        gen.client.models.generate_images = MagicMock(return_value=mock_response)
        enhance_response = MagicMock()
        enhance_response.text = "Better sunset"
        gen.client.models.generate_content = MagicMock(return_value=enhance_response)
        inp = GenerationInput(prompt="sunset", enhance_prompt=True)
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.SUCCEEDED
        assert result.enhanced_prompt == "Better sunset"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        gen = _gen()
        gen.client.models.generate_images = MagicMock(
            side_effect=RuntimeError("API error")
        )
        inp = GenerationInput(prompt="test", enhance_prompt=False)
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.FAILED
        assert "API error" in result.error


# ============================================================================
# _perform_edit
# ============================================================================


class TestPerformEdit:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        gen = _gen()
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"edited-image"
        mock_part.inline_data.mime_type = "image/png"
        mock_part.text = None
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
        gen.client.models.generate_content = MagicMock(return_value=mock_response)

        inp = GenerationInput(prompt="edit this", enhance_prompt=False)
        refs = [(b"src-image", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.generated_images) == 1

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        gen = _gen()
        gen.client.models.generate_content = MagicMock(
            side_effect=RuntimeError("edit fail")
        )
        inp = GenerationInput(prompt="edit", enhance_prompt=False)
        refs = [(b"src", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.FAILED
        assert "edit fail" in result.error

    @pytest.mark.asyncio
    async def test_text_response_no_images(self) -> None:
        gen = _gen()
        mock_part = MagicMock()
        mock_part.inline_data = None
        mock_part.text = "I cannot edit that"
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
        gen.client.models.generate_content = MagicMock(return_value=mock_response)
        inp = GenerationInput(prompt="edit", enhance_prompt=False)
        refs = [(b"src", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    async def test_no_candidates(self) -> None:
        gen = _gen()
        mock_response = MagicMock()
        mock_response.candidates = []
        gen.client.models.generate_content = MagicMock(return_value=mock_response)
        inp = GenerationInput(prompt="edit", enhance_prompt=False)
        refs = [(b"src", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.FAILED

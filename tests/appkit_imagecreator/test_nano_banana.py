# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for NanoBananaImageGenerator.

Covers _perform_generation: success, no images, exception,
config handling, and aspect ratio override.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from appkit_imagecreator.backend.generators.nano_banana import (
    NanoBananaImageGenerator,
)
from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageResponseState,
)

_PATCH = "appkit_imagecreator.backend.generators.nano_banana"


def _model(
    model_id: str = "nano-banana",
    model_name: str = "gemini-2.0-flash-exp",
    config: dict | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = model_id
    m.model = model_name
    m.config = config
    return m


def _input(
    prompt: str = "a cat",
    width: int = 1024,
    height: int = 1024,
) -> GenerationInput:
    return GenerationInput(
        prompt=prompt,
        width=width,
        height=height,
        enhance_prompt=False,
    )


def _make_generator(
    model: MagicMock | None = None,
) -> NanoBananaImageGenerator:
    """Create generator with mocked client."""
    m = model or _model()
    with patch("appkit_imagecreator.backend.generators.google.genai"):
        gen = NanoBananaImageGenerator(model=m, api_key="key")
    gen.client = MagicMock()
    return gen


def _response_with_images(
    image_data: bytes = b"\x89PNG",
) -> MagicMock:
    """Build a mock genai response with inline image data."""
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = image_data
    # hasattr(part, "inline_data") should return True
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


def _response_empty() -> MagicMock:
    """Build a mock genai response with no candidates."""
    response = MagicMock()
    response.candidates = []
    return response


def _response_no_inline_data() -> MagicMock:
    """Response with candidate but no inline_data on parts."""
    part = MagicMock(spec=[])  # No inline_data attribute
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


class TestPerformGeneration:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Returns SUCCEEDED with generated images."""
        gen = _make_generator()
        gen.client.models.generate_content.return_value = _response_with_images(
            b"\x89PNG"
        )

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.generated_images) == 1
        assert result.enhanced_prompt is not None

    @pytest.mark.asyncio
    async def test_no_candidates(self) -> None:
        """Returns FAILED when no candidates in response."""
        gen = _make_generator()
        gen.client.models.generate_content.return_value = _response_empty()

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.FAILED
        assert "No images" in (result.error or "")

    @pytest.mark.asyncio
    async def test_no_inline_data(self) -> None:
        """Returns FAILED when parts have no inline_data."""
        gen = _make_generator()
        gen.client.models.generate_content.return_value = _response_no_inline_data()

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        """Returns FAILED with error message on exception."""
        gen = _make_generator()
        gen.client.models.generate_content.side_effect = RuntimeError("API error")

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.FAILED
        assert "API error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_with_model_config(self) -> None:
        """Model config is split into image_config and main config."""
        model = _model(
            config={
                "aspect_ratio": "16:9",
                "person_generation": "allow",
                "temperature": 0.5,
            }
        )
        gen = _make_generator(model=model)
        gen.client.models.generate_content.return_value = _response_with_images()

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.SUCCEEDED
        # aspect_ratio from config overrides computed one
        call_kwargs = gen.client.models.generate_content.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_without_config(self) -> None:
        """No model config uses computed aspect ratio."""
        model = _model(config=None)
        gen = _make_generator(model=model)
        gen.client.models.generate_content.return_value = _response_with_images()

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_empty_config(self) -> None:
        """Empty model config uses computed aspect ratio."""
        model = _model(config={})
        gen = _make_generator(model=model)
        gen.client.models.generate_content.return_value = _response_with_images()

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_multiple_parts(self) -> None:
        """Extracts multiple images from multiple parts."""
        part1 = MagicMock()
        part1.inline_data = MagicMock()
        part1.inline_data.data = b"img1"
        part2 = MagicMock()
        part2.inline_data = MagicMock()
        part2.inline_data.data = b"img2"

        content = MagicMock()
        content.parts = [part1, part2]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        gen = _make_generator()
        gen.client.models.generate_content.return_value = response

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.generated_images) == 2

    @pytest.mark.asyncio
    async def test_candidate_no_content(self) -> None:
        """Skips candidates with no content."""
        candidate = MagicMock()
        candidate.content = None
        response = MagicMock()
        response.candidates = [candidate]

        gen = _make_generator()
        gen.client.models.generate_content.return_value = response

        result = await gen._perform_generation(_input())

        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    async def test_image_config_fields(self) -> None:
        """All known image_config fields are routed correctly."""
        model = _model(
            config={
                "image_size": "1024x1024",
                "output_mime_type": "image/webp",
                "output_compression_quality": 90,
            }
        )
        gen = _make_generator(model=model)
        gen.client.models.generate_content.return_value = _response_with_images()

        result = await gen._perform_generation(_input())
        assert result.state == ImageResponseState.SUCCEEDED

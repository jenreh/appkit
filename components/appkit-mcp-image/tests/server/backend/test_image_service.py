"""Tests for image service helpers."""

from unittest.mock import AsyncMock

import pytest
from server.backend.image_service import edit_image_impl, generate_image_impl
from server.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGeneratorResponse,
    ImageResponseState,
)


class TestGenerateImageImpl:
    """Test generate_image_impl function."""

    @pytest.mark.asyncio
    async def test_generate_image_impl_returns_enhanced_prompt(self) -> None:
        """generate_image_impl should expose enhanced prompt in its result."""
        generator = AsyncMock()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=["data:image/png;base64,aW1hZ2Ux"],
            enhanced_prompt="Refined prompt",
        )

        input_data = GenerationInput(prompt="Original prompt", size="auto")

        image_url, enhanced_prompt = await generate_image_impl(
            input_data=input_data,
            generator=generator,
        )

        assert enhanced_prompt == "Refined prompt"
        assert image_url == "data:image/png;base64,aW1hZ2Ux"

    @pytest.mark.asyncio
    async def test_generate_image_impl_success(self) -> None:
        """Test successful image generation."""
        generator = AsyncMock()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=["http://localhost:8000/image.png"],
            enhanced_prompt="Enhanced: Test prompt",
        )

        input_data = GenerationInput(prompt="Test prompt")

        image_url, enhanced_prompt = await generate_image_impl(
            input_data=input_data,
            generator=generator,
        )

        assert image_url == "http://localhost:8000/image.png"
        assert enhanced_prompt == "Enhanced: Test prompt"
        generator.generate.assert_called_once_with(input_data)

    @pytest.mark.asyncio
    async def test_generate_image_impl_failure(self) -> None:
        """Test error handling when generation fails."""
        generator = AsyncMock()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            images=[],
            error="API connection failed",
        )

        input_data = GenerationInput(prompt="Test prompt")

        with pytest.raises(ValueError) as exc_info:
            await generate_image_impl(
                input_data=input_data,
                generator=generator,
            )

        assert "Image generation failed" in str(exc_info.value)
        assert "API connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_image_impl_without_enhanced_prompt(self) -> None:
        """Test generation when enhanced_prompt is None."""
        generator = AsyncMock()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=["http://localhost:8000/image2.png"],
            enhanced_prompt=None,
        )

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=False)

        image_url, enhanced_prompt = await generate_image_impl(
            input_data=input_data,
            generator=generator,
        )

        assert image_url == "http://localhost:8000/image2.png"
        assert enhanced_prompt is None

    @pytest.mark.asyncio
    async def test_generate_image_impl_multiple_images(self) -> None:
        """Test generation returns first image when multiple are generated."""
        generator = AsyncMock()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=[
                "http://localhost:8000/image1.png",
                "http://localhost:8000/image2.png",
            ],
            enhanced_prompt="Enhanced prompt",
        )

        input_data = GenerationInput(prompt="Test", size="1024x1024")

        image_url, enhanced_prompt = await generate_image_impl(
            input_data=input_data,
            generator=generator,
        )

        # Should return first image only
        assert image_url == "http://localhost:8000/image1.png"
        assert enhanced_prompt == "Enhanced prompt"


class TestEditImageImpl:
    """Test edit_image_impl function."""

    @pytest.mark.asyncio
    async def test_edit_image_impl_success(self) -> None:
        """Test successful image editing."""
        generator = AsyncMock()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=["http://localhost:8000/edited.png"],
        )

        input_data = EditImageInput(
            prompt="Make it brighter",
            image_paths=["http://example.com/original.png"],
        )

        image_url = await edit_image_impl(
            input_data=input_data,
            generator=generator,
        )

        assert image_url == "http://localhost:8000/edited.png"
        generator.edit.assert_called_once_with(input_data)

    @pytest.mark.asyncio
    async def test_edit_image_impl_with_mask(self) -> None:
        """Test image editing with mask."""
        generator = AsyncMock()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=["http://localhost:8000/inpainted.png"],
        )

        input_data = EditImageInput(
            prompt="Fill with clouds",
            image_paths=["http://example.com/image.png"],
            mask_path="http://example.com/mask.png",
        )

        image_url = await edit_image_impl(
            input_data=input_data,
            generator=generator,
        )

        assert image_url == "http://localhost:8000/inpainted.png"

    @pytest.mark.asyncio
    async def test_edit_image_impl_failure(self) -> None:
        """Test error handling when editing fails."""
        generator = AsyncMock()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            images=[],
            error="Image format not supported",
        )

        input_data = EditImageInput(
            prompt="Edit",
            image_paths=["http://example.com/image.png"],
        )

        with pytest.raises(ValueError) as exc_info:
            await edit_image_impl(
                input_data=input_data,
                generator=generator,
            )

        assert "Image editing failed" in str(exc_info.value)
        assert "Image format not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_edit_image_impl_multiple_images(self) -> None:
        """Test editing multiple images returns first result."""
        generator = AsyncMock()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=[
                "http://localhost:8000/edited1.png",
                "http://localhost:8000/edited2.png",
            ],
        )

        input_data = EditImageInput(
            prompt="Enhance",
            image_paths=[
                "http://example.com/img1.png",
                "http://example.com/img2.png",
            ],
        )

        image_url = await edit_image_impl(
            input_data=input_data,
            generator=generator,
        )

        # Should return first edited image
        assert image_url == "http://localhost:8000/edited1.png"

    @pytest.mark.asyncio
    async def test_edit_image_impl_empty_result(self) -> None:
        """Test error when edit returns empty image list."""
        generator = AsyncMock()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            images=[],
            error="No images returned",
        )

        input_data = EditImageInput(
            prompt="Edit",
            image_paths=["test.png"],
        )

        with pytest.raises(ValueError):
            await edit_image_impl(
                input_data=input_data,
                generator=generator,
            )

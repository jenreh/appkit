"""Unit tests for data models in app.backend.models."""

import os

import pytest
from pydantic import ValidationError

from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageInputBase,
)


class TestImageInputBase:
    """Test ImageInputBase model."""

    @pytest.mark.parametrize(
        "size",
        [
            "1024x1024",
            "1536x1024",
            "1024x1536",
            "auto",
        ],
    )
    def test_valid_sizes(self, size: str) -> None:
        """Test all valid size values."""
        input_data = ImageInputBase(prompt="Test", size=size)
        assert input_data.size == size

    @pytest.mark.parametrize("output_format", ["png", "jpeg", "webp"])
    def test_valid_output_formats(self, output_format: str) -> None:
        """Test all valid output formats."""
        input_data = ImageInputBase(prompt="Test", output_format=output_format)
        assert input_data.output_format == output_format

    @pytest.mark.parametrize("background", ["transparent", "opaque", "auto"])
    def test_valid_background_values(self, background: str) -> None:
        """Test valid background values."""
        input_data = ImageInputBase(prompt="Test", background=background)
        assert input_data.background == background


class TestGenerationInput:
    """Test GenerationInput model."""

    def test_inherits_from_base(self) -> None:
        """Test that GenerationInput inherits from ImageInputBase."""
        assert issubclass(GenerationInput, ImageInputBase)

    def test_defaults(self) -> None:
        """Test default values for GenerationInput."""
        input_data = GenerationInput(prompt="Test prompt")

        # Base class defaults
        assert input_data.size == "1536x1024"
        assert input_data.output_format == "jpeg"
        assert input_data.background == "opaque"

        # GenerationInput specific defaults
        assert input_data.prompt == "Test prompt"
        assert input_data.enhance_prompt is True

    def test_prompt_required(self) -> None:
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            GenerationInput()

    def test_legacy_parameters(self) -> None:
        """Test legacy parameter support."""
        input_data = GenerationInput(
            prompt="Test",
            seed=12345,
            enhance_prompt=False,
        )

        assert input_data.seed == 12345
        assert input_data.enhance_prompt is False

    def test_all_parameters_together(self) -> None:
        """Test GenerationInput with all parameters."""
        input_data = GenerationInput(
            prompt="A beautiful landscape",
            size="1536x1024",
            output_format="webp",
            background="opaque",
            seed=42,
            enhance_prompt=True,
        )

        assert input_data.prompt == "A beautiful landscape"
        assert input_data.size == "1536x1024"
        assert input_data.output_format == "webp"
        assert input_data.background == "opaque"
        assert input_data.seed == 42
        assert input_data.enhance_prompt is True


class TestEditImageInput:
    """Test EditImageInput model."""

    def test_inherits_from_base(self) -> None:
        """Test that EditImageInput inherits from ImageInputBase."""
        assert issubclass(EditImageInput, ImageInputBase)

    def test_defaults(self) -> None:
        """Test default values for EditImageInput."""
        input_data = EditImageInput(prompt="Edit prompt", image_paths=["test.png"])

        # Base class defaults
        assert input_data.size == "1536x1024"
        assert input_data.output_format == "jpeg"
        assert input_data.background == "opaque"

        # EditImageInput specific defaults
        assert input_data.prompt == "Edit prompt"
        assert input_data.image_paths == ["test.png"]
        assert input_data.mask_path is None

    def test_prompt_required(self) -> None:
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            EditImageInput(image_paths=["test.png"])

    def test_image_paths_required(self) -> None:
        """Test that image_paths is required."""
        with pytest.raises(ValidationError):
            EditImageInput(prompt="Test")

    def test_single_image_path(self) -> None:
        """Test with single image path."""
        input_data = EditImageInput(prompt="Edit", image_paths=["image.png"])
        assert len(input_data.image_paths) == 1
        assert input_data.image_paths[0] == "image.png"

    def test_multiple_image_paths(self) -> None:
        """Test with multiple image paths (up to 16)."""
        paths = [f"image{i}.png" for i in range(10)]
        input_data = EditImageInput(prompt="Edit", image_paths=paths)
        assert len(input_data.image_paths) == 10
        assert input_data.image_paths == paths

    def test_mask_path(self) -> None:
        """Test mask_path parameter."""
        input_data = EditImageInput(
            prompt="Edit", image_paths=["image.png"], mask_path="mask.png"
        )
        assert input_data.mask_path == "mask.png"

    def test_all_parameters_together(self) -> None:
        """Test EditImageInput with all parameters."""
        input_data = EditImageInput(
            prompt="Edit this image",
            size="1024x1536",
            output_format="jpeg",
            background="opaque",
            image_paths=["image1.png", "image2.png"],
            mask_path="mask.png",
        )

        assert input_data.prompt == "Edit this image"
        assert input_data.size == "1024x1536"
        assert input_data.output_format == "jpeg"
        assert input_data.background == "opaque"
        assert input_data.image_paths == ["image1.png", "image2.png"]
        assert input_data.mask_path == "mask.png"


class TestImageGenerator:
    """Test ImageGenerator base class."""

    def test_init(self) -> None:
        """Test ImageGenerator initialization."""
        generator = ImageGenerator(
            id="test-gen",
            label="Test Generator",
            model="test-model",
            optimizer_model="opt-model",
            api_key="test-key",
            backend_server="http://localhost:8000",
        )

        assert generator.id == "test-gen"
        assert generator.label == "Test Generator"
        assert generator.model == "test-model"
        assert generator.api_key == "test-key"
        assert generator.backend_server == "http://localhost:8000"

    def test_init_without_backend_server(self) -> None:
        """Test ImageGenerator initialization without backend_server."""
        generator = ImageGenerator(
            id="test-gen",
            label="Test Generator",
            model="test-model",
            optimizer_model="opt-model",
            api_key="test-key",
        )

        assert generator.backend_server is None

    def test_format_prompt_without_negative_prompt(self) -> None:
        """Test _format_prompt without negative prompt."""
        generator = ImageGenerator(
            id="test", label="Test", model="test", optimizer_model="opt", api_key="key"
        )

        prompt = "A beautiful sunset"
        result = generator._format_prompt(prompt)  # noqa: SLF001

        assert result == "A beautiful sunset"

    def test_format_prompt_with_negative_prompt(self) -> None:
        """Test _format_prompt with negative prompt."""
        generator = ImageGenerator(
            id="test", label="Test", model="test", optimizer_model="opt", api_key="key"
        )

        prompt = "A beautiful sunset"
        negative = "blurry, low quality"
        result = generator._format_prompt(prompt, negative)  # noqa: SLF001

        assert "## Image Prompt:" in result
        assert prompt in result
        assert "## Negative Prompt" in result
        assert negative in result

    def test_aspect_ratio_square(self) -> None:
        """Test _aspect_ratio for square dimensions."""
        generator = ImageGenerator(
            id="test", label="Test", model="test", optimizer_model="opt", api_key="key"
        )

        assert generator._aspect_ratio(1024, 1024) == "1:1"  # noqa: SLF001
        assert generator._aspect_ratio(512, 512) == "1:1"  # noqa: SLF001
        assert generator._aspect_ratio(2048, 2048) == "1:1"  # noqa: SLF001

    def test_aspect_ratio_landscape(self) -> None:
        """Test _aspect_ratio for landscape dimensions (width > height)."""
        generator = ImageGenerator(
            id="test", label="Test", model="test", optimizer_model="opt", api_key="key"
        )

        assert generator._aspect_ratio(1536, 1024) == "4:3"  # noqa: SLF001
        assert generator._aspect_ratio(2048, 1024) == "4:3"  # noqa: SLF001
        assert generator._aspect_ratio(1024, 512) == "4:3"  # noqa: SLF001

    def test_aspect_ratio_portrait(self) -> None:
        """Test _aspect_ratio for portrait dimensions (width < height)."""
        generator = ImageGenerator(
            id="test", label="Test", model="test", optimizer_model="opt", api_key="key"
        )

        assert generator._aspect_ratio(1024, 1536) == "3:4"  # noqa: SLF001
        assert generator._aspect_ratio(512, 1024) == "3:4"  # noqa: SLF001
        assert generator._aspect_ratio(1024, 2048) == "3:4"  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_save_image_without_backend_server(self) -> None:
        """Test save_image raises when backend_server unset."""
        generator = ImageGenerator(
            id="test",
            label="Test",
            model="test",
            optimizer_model="opt",
            api_key="key",
            # backend_server not provided
        )

        with pytest.raises(ValueError) as exc_info:
            await generator.save_image(
                image_bytes=b"test_image",
                tmp_file_prefix="test",
                output_format="png",
            )

        assert "backend_server" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_save_image_with_backend_server(self, tmp_path) -> None:
        """Test save_image saves image and returns URL."""
        generator = ImageGenerator(
            id="test",
            label="Test",
            model="test",
            optimizer_model="opt",
            api_key="key",
            backend_server="http://localhost:8000",
        )

        # Mock TMP_PATH
        old_tmp_path = os.environ.get("TMP_PATH")
        os.environ["TMP_PATH"] = str(tmp_path)

        try:
            url = await generator.save_image(
                image_bytes=b"test_image_data",
                tmp_file_prefix="test",
                output_format="png",
            )

            assert "http://localhost:8000" in url
            assert "/_upload/" in url
            assert ".png" in url
        finally:
            # Restore original TMP_PATH
            if old_tmp_path:
                os.environ["TMP_PATH"] = old_tmp_path
            else:
                os.environ.pop("TMP_PATH", None)

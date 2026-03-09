"""Unit tests for data models in app.backend.models."""

import pytest
from pydantic import ValidationError

from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageInputBase,
    ImageResult,
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


class TestImageResult:
    """Test ImageResult model."""

    def test_success_result(self) -> None:
        """Test ImageResult with success."""
        result = ImageResult(
            success=True,
            image_url="http://localhost/api/images/1",
            prompt="a cat",
            model="test-model",
        )
        assert result.success is True
        assert result.image_url == "http://localhost/api/images/1"

    def test_error_result(self) -> None:
        """Test ImageResult with error."""
        result = ImageResult(
            success=False,
            error="generation failed",
        )
        assert result.success is False
        assert result.error == "generation failed"
        assert result.image_url is None

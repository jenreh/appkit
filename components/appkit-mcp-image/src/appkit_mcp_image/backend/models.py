"""MCP-specific input and output models for image generation tools.

These models define the tool interface (what the LLM sends/receives).
Image generation logic and database models are reused from appkit-imagecreator.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ImageInputBase(BaseModel):
    """Base class for image generation and editing inputs."""

    prompt: str = Field(..., description="Text description (max 32000 chars)")

    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = Field(
        default="1536x1024", description="Image dimensions"
    )

    # Output format
    output_format: Literal["png", "jpeg", "webp"] = Field(
        default="jpeg", description="Output image format"
    )

    # Background transparency
    background: Literal["transparent", "opaque", "auto"] = Field(
        default="opaque", description="Background transparency setting"
    )


class GenerationInput(ImageInputBase):
    """Input model for image generation via MCP tool."""

    seed: int = Field(
        default=0, description="Random seed for reproducibility (0 = random)"
    )
    enhance_prompt: bool = Field(default=True, description="Auto-enhance prompt")


class EditImageInput(ImageInputBase):
    """Input model for image editing via MCP tool."""

    image_paths: list[str] = Field(
        ...,
        description="List of image URLs, file paths, or base64 data URLs (max 16)",
    )
    mask_path: str | None = Field(
        default=None,
        description=(
            "Optional mask image for inpainting (transparent areas = edit zones)"
        ),
    )


class ImageResult(BaseModel):
    """Structured result returned by image tools to the MCP-App UI."""

    success: bool
    image_url: str | None = None
    prompt: str | None = None
    enhanced_prompt: str | None = None
    model: str | None = None
    size: str | None = None
    error: str | None = None

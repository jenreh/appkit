import logging
from abc import ABC
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import reflex as rx
from pydantic import BaseModel, computed_field
from sqlalchemy import JSON, Column, DateTime, LargeBinary
from sqlmodel import Field

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


def get_image_api_base_url() -> str:
    """Get the base URL for the image API based on configuration.

    Returns the backend URL with port for development (separate ports),
    or just the deploy URL for production (single port).
    """
    reflex_config = service_registry().get(ReflexConfig)
    if reflex_config.single_port:
        return reflex_config.deploy_url
    return f"{reflex_config.deploy_url}:{reflex_config.backend_port}"


class ImageModel(BaseModel):
    id: str
    model: str
    label: str
    config: dict[str, Any] | None = None


class GeneratedImage(rx.Model, table=True):
    """Model for storing generated images in the database.

    Stores image metadata including prompt, style, model configuration,
    and the binary image data as a BLOB.
    """

    __tablename__ = "imagecreator_generated_images"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    prompt: str = Field(max_length=4000, nullable=False)
    enhanced_prompt: str | None = Field(default=None, max_length=8000, nullable=True)
    style: str | None = Field(default=None, max_length=100, nullable=True)
    model: str = Field(max_length=100, nullable=False)
    image_data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    content_type: str = Field(max_length=50, nullable=False, default="image/png")
    width: int = Field(nullable=False)
    height: int = Field(nullable=False)
    quality: str | None = Field(default=None, max_length=20, nullable=True)
    config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    is_uploaded: bool = Field(default=False, nullable=False, index=True)
    is_deleted: bool = Field(default=False, nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class GeneratedImageModel(BaseModel):
    """Pydantic model for GeneratedImage data transfer (without binary data)."""

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    prompt: str
    enhanced_prompt: str | None = None
    style: str | None = None
    model: str
    content_type: str = "image/png"
    width: int
    height: int
    quality: str | None = None
    config: dict[str, Any] | None = None
    is_uploaded: bool = False
    is_deleted: bool = False
    created_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str:
        """Generate the API URL to download the image."""
        base_url = get_image_api_base_url()
        return f"{base_url}/api/images/{self.id}"


class ImageResponseState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationInput(BaseModel):
    """Input parameters for image generation or editing.

    Attributes:
        prompt: Text description of the desired image
        negative_prompt: What to avoid in the image
        width: Output image width
        height: Output image height
        steps: Number of diffusion steps (model-specific)
        n: Number of images to generate
        seed: Random seed for reproducibility
        enhance_prompt: Whether to AI-enhance the prompt
        reference_image_ids: IDs of images to use as references (image-to-image)
    """

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 4
    n: int = 1
    seed: int = 0
    enhance_prompt: bool = True
    reference_image_ids: list[int] = []


class GeneratedImageData(BaseModel):
    """Single generated image with raw data or external URL.

    Used to pass image data from generators to the state layer.
    Either image_bytes or external_url should be set, not both.
    """

    image_bytes: bytes | None = None
    external_url: str | None = None
    content_type: str = "image/png"


class ImageGeneratorResponse(BaseModel):
    """Response from image generation.

    Attributes:
        state: Success or failure state
        generated_images: List of generated images with bytes or URLs (preferred)
        images: DEPRECATED - List of image URLs for backwards compatibility
        error: Error message if generation failed
        enhanced_prompt: The AI-enhanced prompt used for generation
    """

    state: ImageResponseState
    generated_images: list[GeneratedImageData] = []
    error: str = ""
    enhanced_prompt: str = ""


class ImageGenerator(ABC):
    """Base class for image generation.

    Subclasses implement _perform_generation() to call their respective APIs
    and return GeneratedImageData with raw bytes or external URLs.
    """

    model: ImageModel
    api_key: str
    supports_edit: bool

    def __init__(
        self,
        model: ImageModel,
        api_key: str,
        supports_edit: bool = True,
    ):
        self.model = model
        self.api_key = api_key
        self.supports_edit = supports_edit

    def _format_prompt(self, prompt: str, negative_prompt: str | None = None) -> str:
        """Formats the prompt including an optional negative prompt."""
        if negative_prompt:
            return (
                f"## Image Prompt:\n{prompt}\n\n"
                f"## Negative Prompt (Avoid this in the image):\n{negative_prompt}"
            ).strip()
        return prompt.strip()

    def _create_generated_image_data(
        self,
        image_bytes: bytes,
        content_type: str = "image/png",
    ) -> GeneratedImageData:
        """Create GeneratedImageData from raw image bytes.

        Args:
            image_bytes: Raw binary image data
            content_type: MIME type of the image (e.g., 'image/png', 'image/jpeg')

        Returns:
            GeneratedImageData with the image bytes set
        """
        return GeneratedImageData(
            image_bytes=image_bytes,
            content_type=content_type,
        )

    def _aspect_ratio(self, width: int, height: int) -> str:
        """Calculate the closest supported aspect ratio based on width and height."""
        ratios = {
            "2:1": 2 / 1,
            "1:1": 1.0,
            "1:2": 1 / 2,
        }

        current_ratio = width / height
        ratio = min(ratios, key=lambda k: abs(ratios[k] - current_ratio))
        logger.debug(
            "Calculated aspect ratio %s for dimensions %dx%d", ratio, width, height
        )
        return ratio

    async def generate(self, input_data: GenerationInput) -> ImageGeneratorResponse:
        """
        Generates images based on the input data.
        Handles common error logging and response for failures.
        """
        try:
            return await self._perform_generation(input_data)
        except Exception as e:
            logger.exception("Error during image generation with %s", self.model.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, generated_images=[], error=str(e)
            )

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """
        Subclasses must implement this method to perform the actual image generation.
        """
        raise NotImplementedError(
            "Subclasses must implement the _perform_generation method."
        )

    async def edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit images using reference images.

        Args:
            input_data: Generation parameters including prompt and edit mode
            reference_images: List of (image_bytes, content_type) tuples

        Returns:
            ImageGeneratorResponse with edited images
        """
        if not self.supports_edit:
            logger.error(
                "Image editing is not supported by %s",
                self.model.id,
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error="Bildbearbeitung wird von diesem Modell nicht unterstützt.",
            )

        try:
            return await self._perform_edit(input_data, reference_images)
        except Exception as e:
            logger.exception("Error during image editing with %s", self.model.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, generated_images=[], error=str(e)
            )

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Perform image editing with reference images.

        Subclasses must implement this method for image-to-image generation.

        Args:
            input_data: Generation parameters
            reference_images: List of (image_bytes, content_type) tuples

        Returns:
            ImageGeneratorResponse with edited images

        Raises:
            NotImplementedError: If editing is not supported by this generator
        """
        raise NotImplementedError("Subclasses must implement the _perform_edit method.")

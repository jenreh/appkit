import logging
import uuid
from abc import ABC
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

import anyio
from pydantic import BaseModel, Field

from appkit_commons.registry import service_registry
from appkit_mcp_image.configuration import MCPImageGeneratorConfig

logger = logging.getLogger(__name__)
TMP_PATH: Final[str] = "uploaded_files/images"


class ImageResponseState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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
    """Input model for image generation (gpt-image-1)."""

    seed: int = Field(
        default=0, description="Random seed for reproducibility (0 = random)"
    )
    enhance_prompt: bool = Field(default=True, description="Auto-enhance prompt")


class EditImageInput(ImageInputBase):
    """Input model for image editing (gpt-image-1)."""

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


class ImageGeneratorResponse(BaseModel):
    state: ImageResponseState
    images: list[str]
    enhanced_prompt: str | None = None
    error: str = ""


class ImageGenerator(ABC):
    """Base class for image generation."""

    id: str
    model: str
    optimizer_model: str
    label: str
    api_key: str
    base_url: str | None = None
    backend_server: str | None = None

    def __init__(
        self,
        id: str,  # noqa: A002
        label: str,
        model: str,
        optimizer_model: str,
        api_key: str,
        base_url: str | None = None,
        backend_server: str | None = None,
    ):
        self.id = id
        self.model = model
        self.optimizer_model = optimizer_model
        self.base_url = base_url
        self.backend_server = backend_server
        self.label = label
        self.api_key = api_key

    def _format_prompt(self, prompt: str, negative_prompt: str | None = None) -> str:
        """Formats the prompt including an optional negative prompt."""
        if negative_prompt:
            return (
                f"## Image Prompt:\n{prompt}\n\n"
                f"## Negative Prompt (Avoid this in the image):\n{negative_prompt}"
            ).strip()
        return prompt.strip()

    async def save_image(
        self,
        image_bytes: bytes,
        tmp_file_prefix: str,
        output_format: str,
    ) -> str:
        """
        Saves image bytes to a uniquely named file in the temporary directory
        and returns the full URL to access it.
        """
        if not self.backend_server:
            logger.error(
                "backend_server is not configured for generator %s. "
                "Cannot save image to local temp and construct URL.",
                self.id,
            )
            raise ValueError(
                f"backend_server ist für Generator {self.id} nicht konfiguriert, "
                "um die Bild-URL zu erstellen."
            )

        tmp_dir = anyio.Path(TMP_PATH)
        await tmp_dir.mkdir(parents=True, exist_ok=True)

        random_id = uuid.uuid4().hex
        filename = f"{tmp_file_prefix}-{random_id}.{output_format}"
        file_path = tmp_dir / filename

        async with await anyio.open_file(file_path, "wb") as f:
            logger.debug("Writing image to %s", file_path)
            await f.write(image_bytes)

        return f"{self.backend_server}/_upload/images/{filename}"

    def _aspect_ratio(self, width: int, height: int) -> str:
        """Calculate the aspect ratio based on width and height."""
        if width == height:
            return "1:1"

        if width > height:
            return "4:3"

        return "3:4"

    async def generate(self, input_data: GenerationInput) -> ImageGeneratorResponse:
        """
        Generates images based on the input data.
        Handles common error logging and response for failures.
        """
        try:
            return await self._perform_generation(input_data)
        except Exception as e:
            logger.exception("Error during image generation with %s", self.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, images=[], error=str(e)
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

    async def edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """
        Edits images based on the input data.
        Handles common error logging and response for failures.
        """
        try:
            return await self._perform_edit(input_data)
        except Exception as e:
            logger.exception("Error during image editing with %s", self.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, images=[], error=str(e)
            )

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """
        Subclasses must implement this method to perform the actual image editing.
        Raises NotImplementedError if editing is not supported.
        """
        raise NotImplementedError("Subclasses must implement the _perform_edit method.")

    def clean_tmp_path(self, prefix: str) -> Path:
        """Keep only the last max_images_to_keep images with the given prefix.

        Deletes oldest images when the count exceeds the limit.
        """
        tmp_path = Path(TMP_PATH)

        if not tmp_path.exists():
            logger.info("Temporary path %s does not exist. Creating it.", tmp_path)
            tmp_path.mkdir(parents=True, exist_ok=True)
        elif not tmp_path.is_dir():
            logger.error("Temporary path %s is not a directory.", tmp_path)
            raise NotADirectoryError(f"Temporary path {tmp_path} is not a directory.")

        # Get all files matching the prefix, sorted by modification time
        files_with_prefix = sorted(
            (
                f
                for f in tmp_path.iterdir()
                if f.is_file() and f.name.startswith(prefix)
            ),
            key=lambda f: f.stat().st_mtime,  # Oldest first
        )

        # Keep only the last max_images_to_keep images
        config = service_registry().get(MCPImageGeneratorConfig)
        max_images_to_keep = config.max_images_to_keep
        if len(files_with_prefix) > max_images_to_keep:
            files_to_delete = files_with_prefix[:-max_images_to_keep]
            for file in files_to_delete:
                logger.debug(
                    "Removing old image: %s (keeping last %d images)",
                    file,
                    max_images_to_keep,
                )
                file.unlink()

        return tmp_path

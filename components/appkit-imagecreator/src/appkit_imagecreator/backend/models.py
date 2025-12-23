import logging
import uuid  # Added import
from abc import ABC
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

import anyio  # Added import
import reflex as rx
from pydantic import BaseModel, computed_field
from sqlalchemy import JSON, Column, DateTime, LargeBinary
from sqlmodel import Field

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry
from appkit_imagecreator.configuration import ImageGeneratorConfig

logger = logging.getLogger(__name__)
TMP_PATH: Final[str] = service_registry().get(ImageGeneratorConfig).tmp_dir


def get_image_api_base_url() -> str:
    """Get the base URL for the image API based on configuration.

    Returns the backend URL with port for development (separate ports),
    or just the deploy URL for production (single port).
    """
    reflex_config = service_registry().get(ReflexConfig)
    if reflex_config.single_port:
        return reflex_config.deploy_url
    return f"{reflex_config.deploy_url}:{reflex_config.backend_port}"


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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class GeneratedImageModel(BaseModel):
    """Pydantic model for GeneratedImage data transfer (without binary data)."""

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
    prompt: str
    width: int = 1024
    height: int = 1024
    negative_prompt: str = ""
    steps: int = 4
    n: int = 1
    seed: int = 0
    enhance_prompt: bool = True


class ImageGeneratorResponse(BaseModel):
    state: ImageResponseState
    images: list[str]
    error: str = ""
    enhanced_prompt: str = ""  # The actual AI-enhanced prompt used for generation


class ImageGenerator(ABC):
    """Base class for image generation."""

    id: str
    model: str
    label: str
    api_key: str
    backend_server: str | None = None

    def __init__(
        self,
        id: str,  # noqa: A002
        label: str,
        model: str,
        api_key: str,
        backend_server: str | None = None,
    ):
        self.id = id
        self.model = model
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

    async def _save_image_to_tmp_and_get_url(
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

        tmp_dir = Path(TMP_PATH)
        tmp_dir.mkdir(parents=True, exist_ok=True)  # Ensure base temp directory exists

        random_id = uuid.uuid4().hex
        filename = f"{tmp_file_prefix}-{random_id}.{output_format}"
        file_path = tmp_dir / filename

        async with await anyio.open_file(file_path, "wb") as f:
            logger.debug("Writing image to %s", file_path)
            await f.write(image_bytes)

        return f"{self.backend_server}/_upload/{filename}"

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

    def clean_tmp_path(self, prefix: str) -> Path:
        """remove all images beginning with prefix from TMP_PATH"""
        tmp_path = Path(TMP_PATH)

        if not tmp_path.exists():
            logger.info("Temporary path %s does not exist. Creating it.", tmp_path)
            tmp_path.mkdir(parents=True, exist_ok=True)
        elif not tmp_path.is_dir():
            logger.error("Temporary path %s is not a directory.", tmp_path)
            raise NotADirectoryError(f"Temporary path {tmp_path} is not a directory.")

        for file in tmp_path.iterdir():
            if file.is_file() and file.name.startswith(prefix):
                logger.debug("Removing temporary file: %s", file)
                file.unlink()

        return tmp_path

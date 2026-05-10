import logging
from abc import ABC
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, computed_field
from sqlalchemy import (
    JSON,
    DateTime,
    LargeBinary,
    String,
    Unicode,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.database.entities import Base, get_cipher_key
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


def get_image_api_base_url() -> str:
    """Get the base URL for the image API based on configuration."""
    try:
        reflex_config = service_registry().get(ReflexConfig)
        if reflex_config.single_port:
            return reflex_config.deploy_url
        return f"{reflex_config.api_url}"
    except KeyError:
        logger.error("ReflexConfig not found in registry, using default localhost")
        return "http://localhost:3000"


class ImageModel(BaseModel):
    """Pydantic model for runtime image model representation."""

    id: str
    model: str
    label: str
    config: dict[str, Any] | None = None
    required_role: str | None = None


class ImageGeneratorModel(Base):
    """Database model for image generator configuration."""

    __tablename__ = "imagecreator_generator_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    processor_type: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(
        StringEncryptedType(Unicode, get_cipher_key, FernetEngine),
        nullable=False,
        default="",
    )
    base_url: Mapped[str | None] = mapped_column(String, default=None)
    extra_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    required_role: Mapped[str | None] = mapped_column(String, default=None)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    _NON_API_KEYS: ClassVar[frozenset[str]] = frozenset({"on_azure"})

    def to_image_model(self) -> "ImageModel":
        """Convert DB entity to runtime ImageModel."""
        raw = self.extra_config or {}
        api_config = {k: v for k, v in raw.items() if k not in self._NON_API_KEYS}
        return ImageModel(
            id=self.model_id,
            model=self.model,
            label=self.label,
            config=api_config or None,
            required_role=self.required_role,
        )


class GeneratedImage(Base):
    """Model for storing generated images in the database."""

    __tablename__ = "imagecreator_generated_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    prompt: Mapped[str] = mapped_column(String(4000), nullable=False)
    enhanced_prompt: Mapped[str | None] = mapped_column(String(8000), default=None)
    style: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="image/png"
    )
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    quality: Mapped[str | None] = mapped_column(String(20), default=None)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    is_uploaded: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
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
    """Input parameters for image generation or editing."""

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
    """Single generated image with raw data or external URL."""

    image_bytes: bytes | None = None
    external_url: str | None = None
    content_type: str = "image/png"


class ImageGeneratorResponse(BaseModel):
    """Response from image generation."""

    state: ImageResponseState
    generated_images: list[GeneratedImageData] = []
    error: str = ""
    enhanced_prompt: str = ""


class ImageGenerator(ABC):
    """Base class for image generation."""

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
        return GeneratedImageData(
            image_bytes=image_bytes,
            content_type=content_type,
        )

    def _aspect_ratio(self, width: int, height: int) -> str:
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
        raise NotImplementedError(
            "Subclasses must implement the _perform_generation method."
        )

    async def edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
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
        raise NotImplementedError("Subclasses must implement the _perform_edit method.")


class ImageGeneratorConfigModel(BaseModel):
    """Pydantic model for ImageGeneratorModel used in UI State."""

    model_config = {"from_attributes": True}

    id: int = 0
    model_id: str = ""
    model: str = ""
    label: str = ""
    processor_type: str = ""
    api_key: str = ""
    base_url: str | None = None
    extra_config: dict[str, Any] | None = None
    required_role: str | None = None
    active: bool = True
    created_at: datetime | None = None
